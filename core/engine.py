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
from datetime import datetime
from typing import List, Dict, Any, Iterable

from .clock import Clock, ClockConfig, ClockMode
from .variable import VariableStore
from .expression import ExpressionNode, ExpressionConfig, AlgorithmNode
from .factory import InstanceFactory
from .parser import ProgramConfig
from utils.logger import get_logger

# 可选导入数据管理模块
try:
    from data_manager import RealtimeDataManager, RealtimeConfig, HistoryStorage, HistoryConfig
    DATA_MANAGER_AVAILABLE = True
except ImportError:
    DATA_MANAGER_AVAILABLE = False
    RealtimeDataManager = None
    RealtimeConfig = None
    HistoryStorage = None
    HistoryConfig = None


logger = get_logger()


@dataclass
class EngineConfig:
    """
    执行引擎配置（初版，仅表达式节点）。

    后续可以扩展：
    - 物理模型节点
    - 控制算法节点
    - 播放节点（从 CSV/数据库读）
    
    注意：
        - 历史数据长度由 VariableStore 按变量配置，不再使用全局 max_lag_steps
    """

    clock: ClockConfig
    expressions: List[ExpressionConfig]


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
        self.vars = VariableStore()
        self._instances: Dict[str, Any] = instances or {}
        self._nodes: List[Any] = []
        # 只有在提供了 instances 时才创建表达式节点
        if instances is not None:
            self._expr_nodes: List[ExpressionNode] = [
                ExpressionNode(c, instances) for c in config.expressions
            ]
        else:
            self._expr_nodes: List[ExpressionNode] = []

        # 数据管理模块（可选）
        self._realtime_manager: Any = None
        self._history_storage: Any = None

        logger.info(
            "UnifiedEngine initialized: %d expression nodes",
            len(self._expr_nodes),
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
        )
        
        # 创建引擎（传入 instances）
        engine = cls(engine_config, instances=instances)
        engine._nodes = nodes + expr_nodes
        
        # 根据 lag_requirements 配置每个变量的历史数据长度
        # 只有需要历史数据的变量才创建历史缓冲区
        for var_name, max_lag_steps in config.lag_requirements.items():
            # 加上 50% 的安全余量
            safe_lag_steps = int(max_lag_steps * 1.5)
            engine.vars.configure_lag(var_name, safe_lag_steps)
            logger.debug(
                "配置变量历史数据: %s, max_lag_steps=%d (需求=%d)",
                var_name,
                safe_lag_steps,
                max_lag_steps,
            )
        
        # 初始化所有实例的属性到VariableStore
        for instance_name, instance in instances.items():
            stored_attrs = getattr(instance.__class__, "stored_attributes", [])
            for attr_name in stored_attrs:
                var_key = f"{instance_name}.{attr_name}"
                # 检查该属性是否需要历史数据
                if var_key in config.lag_requirements:
                    max_lag_steps = config.lag_requirements[var_key]
                    safe_lag_steps = int(max_lag_steps * 1.5)
                    engine.vars.configure_lag(var_key, safe_lag_steps)
                    logger.debug(
                        "配置实例属性历史数据: %s, max_lag_steps=%d (需求=%d)",
                        var_key,
                        safe_lag_steps,
                        max_lag_steps,
                    )
                
                if hasattr(instance, attr_name):
                    value = getattr(instance, attr_name)
                    engine.vars.set(var_key, value)
        
        return engine

    # 数据管理 API ------------------------------------------------------
    def enable_realtime_data(self, config: Any) -> None:
        """
        启用实时数据管理（REALTIME 模式）
        
        Args:
            config: 实时数据配置（RealtimeConfig）
        """
        if not DATA_MANAGER_AVAILABLE:
            raise ImportError("data_manager module not available. Please install redis.")
        
        if RealtimeDataManager is None:
            raise ImportError("RealtimeDataManager not available. Please install redis.")
        
        self._realtime_manager = RealtimeDataManager(config)
        logger.info("实时数据管理已启用")
    
    def enable_history_storage(self, config: Any) -> None:
        """
        启用历史数据存储（REALTIME 模式）
        
        Args:
            config: 历史数据配置（HistoryConfig）
        """
        if not DATA_MANAGER_AVAILABLE:
            raise ImportError("data_manager module not available. Please install duckdb.")
        
        if HistoryStorage is None:
            raise ImportError("HistoryStorage not available. Please install duckdb.")
        
        self._history_storage = HistoryStorage(config)
        logger.info("历史数据存储已启用")

    # 基本执行 API ------------------------------------------------------
    def run_realtime(self) -> Iterable[Dict[str, Any]]:
        """
        实时模式执行（永久运行，阻塞运行）。
        
        特点：
            - 自动设置 Clock 为 REALTIME 模式（每个周期会 sleep）
            - 永久运行，直到外部中断（KeyboardInterrupt 等）
            - 返回生成器，用于流式处理数据
            - 适合实时模拟、在线运行、与外部系统交互
        
        Returns:
            Iterable[Dict[str, Any]] - 生成器，持续产生快照
        
        示例：
            # 实时运行，与外部系统交互
            try:
                for snapshot in engine.run_realtime():
                    send_to_opcua(snapshot)
                    read_external_input()
            except KeyboardInterrupt:
                print("停止运行")
        """
        # 自动设置 Clock 为 REALTIME 模式
        self.clock.config.mode = ClockMode.REALTIME
        logger.info("切换到 REALTIME 模式（实时运行）")
        
        self.clock.start()
        try:
            while True:
                snapshot = self._step_once()
                
                # 如果启用了实时数据管理，推送到 Redis（每个周期都推送）
                if self._realtime_manager is not None:
                    try:
                        self._realtime_manager.push_snapshot(snapshot)
                    except Exception as e:
                        logger.error(f"Failed to push snapshot to Redis: {e}", exc_info=True)
                
                # 如果启用了历史存储，存储到 DuckDB（只在 need_sample=True 时）
                if self._history_storage is not None:
                    try:
                        need_sample = snapshot.get("need_sample", False)
                        if need_sample:
                            # 使用当前时间作为时间戳（真实时间）
                            timestamp = datetime.now()
                            self._history_storage.store_snapshot(snapshot, timestamp, need_sample)
                    except Exception as e:
                        logger.error(f"Failed to store snapshot to DuckDB: {e}", exc_info=True)
                
                yield snapshot
        finally:
            self.clock.stop()
            # 关闭数据管理模块
            if self._realtime_manager is not None:
                try:
                    self._realtime_manager.close()
                except Exception as e:
                    logger.error(f"Failed to close realtime manager: {e}", exc_info=True)
            
            if self._history_storage is not None:
                try:
                    self._history_storage.close()
                except Exception as e:
                    logger.error(f"Failed to close history storage: {e}", exc_info=True)
    
    def run_generator(self, n: int) -> List[Dict[str, Any]]:
        """
        生成器模式执行（快速批量生成）。
        
        特点：
            - 自动设置 Clock 为 GENERATOR 模式（不 sleep，快速执行）
            - 执行指定周期数，返回所有快照的列表
            - 适合批量数据生成、测试、离线仿真
        
        Args:
            n: 执行周期数（必须 > 0）
        
        Returns:
            List[Dict[str, Any]] - 所有周期的快照列表
        
        示例：
            # 批量生成 10000 个周期的数据
            results = engine.run_generator(10000)
            
            # 保存到文件
            save_to_csv(results, 'output.csv')
        """
        if n <= 0:
            raise ValueError(f"生成器模式必须指定周期数 > 0，got n={n}")
        
        # 自动设置 Clock 为 GENERATOR 模式
        self.clock.config.mode = ClockMode.GENERATOR
        logger.info("切换到 GENERATOR 模式（快速批量生成），执行 %d 个周期", n)
        
        results: List[Dict[str, Any]] = []
        self.clock.start()
        try:
            for _ in range(n):
                snapshot = self._step_once()
                results.append(snapshot)
        finally:
            self.clock.stop()
        return results
    
    def _step_once(self) -> Dict[str, Any]:
        """
        执行一个周期（内部方法）。

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


