"""
程序基类

统一的基础类，用于所有程序实例（算法和模型）。
所有程序实例都按统一的周期执行，通过 execute() 方法更新内部状态。
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.variable import RingBuffer


class BaseProgram:
    """
    程序基类（统一算法和模型的基础类）。

    设计约定：
    - 所有程序实例都按统一的周期（cycle_time）执行。
    - execute() 更新内部状态（例如 PID 的积分项），并更新自身属性（如 mv、pv 等）。
    - 需要对外存储的属性通过 stored_attributes 声明，供上层引擎写入 VariableStore。
    - 程序内部如果需要自己的历史数据（与 VariableStore 独立），使用 _internal_history。
    """

    #: 需要对外存储的属性名列表（例如 ["mv", "pv", "sv"]）
    stored_attributes: List[str] = []

    #: 默认参数，供子类覆盖，例如 {"kp": 12.0, "ti": 30.0, ...}
    default_params: Dict[str, Any] = {}

    def __init__(self, cycle_time: float, **kwargs: Any) -> None:
        """
        初始化程序实例。

        Args:
            cycle_time: 控制器周期（秒），由引擎在创建实例时统一注入。
            **kwargs: 其他初始化参数（来自 DSL 的 init_args），会覆盖 default_params。
        """
        self.cycle_time = cycle_time

        # 合并默认参数与 DSL 提供的参数
        params = {**self.default_params, **kwargs}
        for key, value in params.items():
            setattr(self, key, value)

        # 程序内部历史数据（与 VariableStore 的缓存完全独立）
        # 用于程序自身运算需要的历史（例如更长的积分窗口等）
        self._internal_history: Dict[str, RingBuffer] = {}

    # ---- 内部历史数据工具方法 ------------------------------------------
    def _ensure_internal_history(self, attr_name: str, maxlen: int = 1000) -> None:
        """
        确保某个属性拥有内部历史缓冲区。

        注意：
        - 这里的 maxlen 与 VariableStore 的 record_length 无关，
          完全由程序自身决定。
        """
        if attr_name not in self._internal_history:
            self._internal_history[attr_name] = RingBuffer(maxlen=maxlen)

    def _update_internal_history(self, attr_name: str, value: float) -> None:
        """更新内部历史。仅在该属性已启用内部历史时追加。"""
        if attr_name in self._internal_history:
            self._internal_history[attr_name].append(value)

    def _get_internal_history(self, attr_name: str, steps: int, default: float = 0.0) -> float:
        """按步数获取内部历史数据。"""
        if attr_name in self._internal_history:
            return self._internal_history[attr_name].get_by_lag(steps, default)
        return default

    # ---- 子类需要实现的核心接口 ----------------------------------------
    def execute(self, **kwargs: Any) -> None:  # pragma: no cover - 由子类实现
        """
        执行程序一个周期。

        Args:
            **kwargs: 当前周期的输入参数（由引擎根据 DSL 表达式解析后传入）。
        """
        raise NotImplementedError

