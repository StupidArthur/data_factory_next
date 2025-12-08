"""
DSL 解析器

负责：
- 从 YAML 文件中读取 DSL 配置（例如 config/dsl_demo1.yaml）
- 解析出 ProgramItem / ProgramConfig
- 分析哪些变量/属性存在 `[-N]` 访问需求（lag_requirements）

注意：
- 本模块暂时只做配置解析，不直接驱动执行引擎。
- 之后 UnifiedEngine 可以基于 ProgramConfig 构建具体的节点与实例。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import ast
import pathlib

import yaml

from .clock import ClockConfig, ClockMode, LAG_SAFETY_MARGIN, MIN_RECORD_LENGTH


@dataclass
class ProgramItem:
    """
    单条 program 配置。

    Attributes:
        name: 实例名称或变量名称（如 "pid1"、"tank1"、"non_sense_3"）。
        type: 类型字符串（如 "PID"、"CYLINDRICAL_TANK"、"Variable"）。
        init_args: 初始化参数字典（可为空）。
        expression: 表达式字符串（方法调用或赋值表达式）。
    """

    name: str
    type: str
    expression: str
    init_args: Dict[str, Any]


@dataclass
class ProgramConfig:
    """
    整体 DSL 配置对象。

    Attributes:
        clock: 时钟配置（只包含本 DSL 关心的字段）。
        program: program 列表（顺序即原始 DSL 中的顺序）。
        record_length: 历史记录长度（用于被 [-N] 访问的变量/属性）。
        lag_requirements: 需要历史数据的变量/属性及其最大 lag 步数。
        export_template: 导出模板配置（可选）。
    """

    clock: ClockConfig
    program: List[ProgramItem]
    record_length: int
    lag_requirements: Dict[str, int]
    export_template: Dict[str, Any] | None = None


class DSLParser:
    """
    DSL 配置解析器。

    当前版本：
    - 只解析一个 YAML 文件，返回 ProgramConfig。
    - 支持：
      - 顶层键：cycle_time, start_time, sample_interval, time_format, record_length
      - program: 列表，每项包含 name, type, init_args(可选), expression
      - 表达式中的 `[-N]` 语法（如 v1[-30], pid1.mv[-10]），用于分析 lag_requirements
    """

    def parse_file(self, path: str | pathlib.Path) -> ProgramConfig:
        """
        从 YAML 文件解析 ProgramConfig。

        Args:
            path: 配置文件路径。
        """
        path_obj = pathlib.Path(path)
        with path_obj.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # 1. 解析 clock 配置
        clock_config = self._parse_clock_config(data)

        # 2. 解析 program 列表
        program_items = self._parse_program_items(data)

        # 3. 分析 lag 需求
        lag_requirements = self._analyze_lag_requirements(program_items)

        # 4. 根据 lag 需求计算 record_length
        # 如果配置中指定了 record_length，则使用配置值；否则根据 lag_requirements 的最大值计算
        if "record_length" in data:
            record_length = int(data.get("record_length"))
        else:
            # 根据 lag_requirements 的最大值计算，加上安全余量，最小为 MIN_RECORD_LENGTH
            max_lag = max(lag_requirements.values()) if lag_requirements else 0
            if max_lag > 0:
                record_length = int(max_lag * LAG_SAFETY_MARGIN)
                if record_length < MIN_RECORD_LENGTH:
                    record_length = MIN_RECORD_LENGTH
            else:
                record_length = MIN_RECORD_LENGTH  # 没有 lag 需求时，使用最小值

        # 5. 解析导出模板配置（可选）
        export_template = data.get("export_template")
        
        return ProgramConfig(
            clock=clock_config,
            program=program_items,
            record_length=record_length,
            lag_requirements=lag_requirements,
            export_template=export_template,
        )

    # ------------------------------------------------------------------#
    # 内部解析工具
    # ------------------------------------------------------------------#
    def _parse_clock_config(self, data: Dict[str, Any]) -> ClockConfig:
        """
        从顶层配置解析时钟配置。

        当前版本简单支持：
        - cycle_time: float，默认 0.5
        - start_time: float 或 ISO 字符串（交给 ClockConfig 自己处理）
        - sample_interval: float，可选
        - time_format: str，可选
        - mode: 暂时默认 GENERATOR（离线快速模式）
        """
        cycle_time = float(data.get("cycle_time", 0.5))
        start_time = data.get("start_time", 0.0)
        sample_interval = data.get("sample_interval")
        time_format = data.get("time_format")

        return ClockConfig(
            cycle_time=cycle_time,
            start_time=start_time,
            mode=ClockMode.GENERATOR,
            sample_interval=sample_interval,
            time_format=time_format,
        )

    def _parse_program_items(self, data: Dict[str, Any]) -> List[ProgramItem]:
        """解析 program 列表。"""
        items_raw = data.get("program", []) or []
        program_items: List[ProgramItem] = []

        for item in items_raw:
            name = str(item["name"])
            type_str = str(item["type"])
            expr = str(item.get("expression", "")).strip()
            init_args = dict(item.get("init_args", {}) or {})

            program_items.append(
                ProgramItem(
                    name=name,
                    type=type_str,
                    expression=expr,
                    init_args=init_args,
                )
            )

        return program_items

    # ------------------------------------------------------------------#
    # lag 需求分析
    # ------------------------------------------------------------------#
    def _analyze_lag_requirements(self, program_items: List[ProgramItem]) -> Dict[str, int]:
        """
        分析哪些变量/属性需要历史数据（被 [-N] 访问），并统计最大 lag。

        返回：
            { 变量或属性名: 需要支持的最大滞后步数 }
        例如：
            {"non_sense_1": 30, "pid1.mv": 10}
        """
        lag_requirements: Dict[str, int] = {}

        for item in program_items:
            expr = item.expression
            if not expr:
                continue

            try:
                # 使用 "exec" 模式解析，因为表达式可能是赋值语句（如 non_sense_3 = non_sense_1[-30]）
                tree = ast.parse(expr, mode="exec")
            except SyntaxError:
                # 表达式语法错误先忽略，后续可以在单独的校验阶段处理
                continue

            class LagVisitor(ast.NodeVisitor):
                def __init__(self) -> None:
                    self.local_requirements: Dict[str, int] = {}

                def visit_Subscript(self, node: ast.Subscript) -> None:
                    """
                    处理 v[-30] / pid1.mv[-10] 这种访问。

                    - node.value: 被下标访问的对象 (Name / Attribute)
                    - node.slice: 下标表达式（常量或一元负号表达式）
                    """
                    lag_steps = self._parse_lag_steps(node.slice)
                    if lag_steps <= 0:
                        self.generic_visit(node)
                        return

                    var_name = self._extract_var_name(node.value)
                    if not var_name:
                        self.generic_visit(node)
                        return

                    prev = self.local_requirements.get(var_name, 0)
                    if lag_steps > prev:
                        self.local_requirements[var_name] = lag_steps

                    self.generic_visit(node)

                @staticmethod
                def _parse_lag_steps(slice_node: ast.AST) -> int:
                    """从切片节点中解析出整数步数（例如 -30 -> 30）。"""
                    # 直接常量：[-30] 或 [30]
                    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, (int, float)):
                        return abs(int(slice_node.value))

                    # 一元运算：[-30]
                    if isinstance(slice_node, ast.UnaryOp) and isinstance(slice_node.operand, ast.Constant):
                        if isinstance(slice_node.operand.value, (int, float)):
                            return abs(int(slice_node.operand.value))

                    return 0

                @staticmethod
                def _extract_var_name(node: ast.AST) -> str:
                    """
                    提取被访问对象的“变量名”：
                    - Name -> "v1"
                    - Attribute (Name.attr) -> "pid1.mv"
                    其他情况返回空字符串。
                    """
                    if isinstance(node, ast.Name):
                        return node.id
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                        return f"{node.value.id}.{node.attr}"
                    return ""

            visitor = LagVisitor()
            visitor.visit(tree)

            # 合并当前表达式的需求到全局
            for var_name, steps in visitor.local_requirements.items():
                prev = lag_requirements.get(var_name, 0)
                if steps > prev:
                    lag_requirements[var_name] = steps

        return lag_requirements


