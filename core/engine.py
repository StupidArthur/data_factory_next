"""
统一执行引擎骨架

后续将作为：
- 实时运行（在线 mock）
- 快速批量生成（离线数据）
- 从文件播放（replay）
的统一调度入口。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Iterable

from .clock import Clock, ClockConfig
from .variable import VariableStore
from .expression import ExpressionNode, ExpressionConfig, AlgorithmNode
from .factory import InstanceFactory
from .parser import ProgramConfig
from utils.logger import get_logger


logger = get_logger()


@dataclass
class EngineConfig:
    """
    执行引擎配置（初版，仅表达式节点）。

    后续可以扩展：
    - 物理模型节点
    - 控制算法节点
    - 播放节点（从 CSV/数据库读）
    """

    clock: ClockConfig
    expressions: List[ExpressionConfig]
    max_lag_steps: int = 0


class UnifiedEngine:
    """
    统一执行引擎（初版实现：只包含表达式节点）。

    特点：
    - 内部使用 `Clock` 管理模拟时间与 sleep。
    - 使用 `VariableStore` 管理变量当前值与历史。
    - 通过 `ExpressionNode` 列表按顺序执行计算。
    """

    def __init__(self, config: EngineConfig, instances: Dict[str, Any] | None = None) -> None:
        self.config = config
        self.clock = Clock(config.clock)
        self.vars = VariableStore(max_lag_steps=config.max_lag_steps)
        self._instances: Dict[str, Any] = instances or {}
        self._nodes: List[Any] = []
        # 只有在提供了 instances 时才创建表达式节点
        if instances is not None:
            self._expr_nodes: List[ExpressionNode] = [
                ExpressionNode(c, instances) for c in config.expressions
            ]
        else:
            self._expr_nodes: List[ExpressionNode] = []

        logger.info(
            "UnifiedEngine initialized: %d expression nodes, max_lag_steps=%d",
            len(self._expr_nodes),
            self.config.max_lag_steps,
        )
    
    @classmethod
    def from_program_config(cls, config: ProgramConfig) -> "UnifiedEngine":
        """
        从ProgramConfig创建引擎。
        
        Args:
            config: 程序配置
            
        Returns:
            统一执行引擎实例
        """
        # 创建实例工厂
        factory = InstanceFactory(cycle_time=config.clock.cycle_time)
        
        # 创建所有实例和节点
        instances: Dict[str, Any] = {}
        nodes: List[Any] = []
        expressions: List[ExpressionConfig] = []
        
        for item in config.program:
            if item.type.upper() == "VARIABLE":
                # Variable类型：创建表达式节点
                expr_config = ExpressionConfig(name=item.name, expression=item.expression)
                expressions.append(expr_config)
            else:
                # 算法/模型类型：创建实例和算法节点
                instance = factory.create_instance(item)
                instances[item.name] = instance
                
                # 获取存储属性列表
                stored_attrs = getattr(instance.__class__, "stored_attributes", [])
                
                # 创建算法节点
                node = AlgorithmNode(
                    instance=instance,
                    expression=item.expression,
                    stored_attributes=stored_attrs,
                    instance_name=item.name,
                    instances=instances,
                )
                nodes.append(node)
        
        # 创建表达式节点（需要传入instances）
        expr_nodes: List[ExpressionNode] = []
        for expr_config in expressions:
            node = ExpressionNode(expr_config, instances)
            expr_nodes.append(node)
        
        # 创建引擎配置
        engine_config = EngineConfig(
            clock=config.clock,
            expressions=expressions,
            max_lag_steps=config.record_length,
        )
        
        # 创建引擎（传入 instances）
        engine = cls(engine_config, instances=instances)
        engine._nodes = nodes + expr_nodes
        
        # 初始化所有实例的属性到VariableStore
        for instance_name, instance in instances.items():
            stored_attrs = getattr(instance.__class__, "stored_attributes", [])
            for attr_name in stored_attrs:
                if hasattr(instance, attr_name):
                    value = getattr(instance, attr_name)
                    engine.vars.set(f"{instance_name}.{attr_name}", value)
        
        return engine

    # 基本执行 API ------------------------------------------------------
    def step_once(self) -> Dict[str, Any]:
        """
        执行一个周期。

        执行顺序：
        1. 使用当前 `sim_time` 计算本周期的目标时间标签 `t`
        2. 执行所有表达式节点（算法计算）
        3. 调用 `clock.step()`，在内部根据模式决定是否 sleep，并更新周期计数

        Returns:
            当前周期完成后所有变量的快照，包含：
            - 所有变量的当前值
            - cycle_count: 周期计数
            - need_sample: 是否需要采样
            - time_str: 当前时间字符串
            - sim_time: 当前模拟时间（浮点数，秒）
        """
        # 1. 计算本周期的目标时间标签（下一个采样点）
        t = self.clock.sim_time + self.config.clock.cycle_time

        # 2. 按顺序执行所有节点
        # 先执行算法节点，再执行表达式节点
        for node in self._nodes:
            if isinstance(node, AlgorithmNode):
                node.step(self.vars)
            elif isinstance(node, ExpressionNode):
                node.step(self.vars)

        # 3. 步进时钟（内部根据模式决定是否 sleep，并记录执行时间）
        cycle_count, need_sample, time_str, exec_ratio = self.clock.step()

        # 4. 返回快照
        snapshot = self.vars.snapshot()
        snapshot["cycle_count"] = cycle_count
        snapshot["need_sample"] = need_sample
        snapshot["time_str"] = time_str
        snapshot["sim_time"] = t
        snapshot["exec_ratio"] = exec_ratio
        return snapshot

    def run_for_steps(self, steps: int) -> List[Dict[str, Any]]:
        """
        连续执行指定步数。

        注意：
        - step() 内部会根据 ClockConfig.mode 决定是否等待
        - REALTIME 模式：每个周期都会 sleep
        - GENERATOR 模式：不 sleep，快速执行

        Args:
            steps: 周期数。

        Returns:
            周期快照列表。
        """
        results: List[Dict[str, Any]] = []
        self.clock.start()
        try:
            for _ in range(steps):
                snapshot = self.step_once()
                results.append(snapshot)
        finally:
            self.clock.stop()
        return results

    def run_forever(self) -> Iterable[Dict[str, Any]]:
        """
        无限循环执行（生成器形式）。

        注意：
        - 调用方负责中断循环（例如外层 while, try/except KeyboardInterrupt）。
        - step() 内部会根据 ClockConfig.mode 决定是否 sleep。
        """
        self.clock.start()
        try:
            while True:
                snapshot = self.step_once()
                yield snapshot
        finally:
            self.clock.stop()


