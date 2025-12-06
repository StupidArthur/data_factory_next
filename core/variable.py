"""
变量状态与历史缓冲区模块

用于支持按周期执行时的有状态计算，以及表达式中的滞后（lag）访问。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Any


@dataclass
class RingBuffer:
    """
    简单环形缓冲区，用于保存固定长度的历史值。

    注意：为了简化实现，这里直接用 deque(maxlen=N)，足够应对当前场景。
    """

    maxlen: int
    _data: Deque[float] = field(default_factory=deque, init=False)

    def append(self, value: float) -> None:
        """追加一个新值。"""
        if self._data.maxlen is None:
            self._data = deque(self._data, maxlen=self.maxlen)
        self._data.append(value)

    def get_by_lag(self, steps: int, default: float = 0.0) -> float:
        """
        按“步数”访问历史值。

        Args:
            steps: 滞后步数（正整数），steps=1 表示上一个周期。
            default: 历史不足时的默认值。
        """
        if steps <= 0 or not self._data:
            return self._data[-1] if self._data else default

        if steps > len(self._data):
            return default

        # deque[-1] 是最新值，[-steps] 是对应的历史值
        return list(self._data)[-steps]


@dataclass
class VariableState:
    """
    单个变量的运行时状态。

    Attributes:
        name: 变量名称（例如 "v1" 或 "tank1.level"）。
        value: 当前周期的数值。
        history: 历史缓冲区，用于实现滞后访问。
    """

    name: str
    value: float = 0.0
    history: RingBuffer | None = None

    def update(self, new_value: float) -> None:
        """更新当前值并写入历史缓冲区。"""
        self.value = new_value
        if self.history is not None:
            self.history.append(new_value)

    def get_with_lag(self, steps: int, default: float = 0.0) -> float:
        """按步数获取历史值。"""
        if self.history is None:
            return self.value
        return self.history.get_by_lag(steps, default=default)


class VariableStore:
    """
    变量存储与访问容器。

    - 管理所有变量的当前值与历史缓冲区。
    - 提供按名称与步数访问变量的方法。
    """

    def __init__(self, max_lag_steps: int = 0) -> None:
        self._vars: Dict[str, VariableState] = {}
        self._max_lag_steps = max_lag_steps

    def ensure(self, name: str, initial: float = 0.0) -> VariableState:
        """确保变量存在，如不存在则创建。"""
        if name not in self._vars:
            history = (
                RingBuffer(maxlen=self._max_lag_steps) if self._max_lag_steps > 0 else None
            )
            self._vars[name] = VariableState(name=name, value=initial, history=history)
        return self._vars[name]

    def set(self, name: str, value: float) -> None:
        """设置变量当前值（并写入历史）。"""
        var = self.ensure(name)
        var.update(value)

    def get(self, name: str, default: float = 0.0) -> float:
        """获取变量当前值。"""
        var = self._vars.get(name)
        if var is None:
            return default
        return var.value

    def get_with_lag(self, name: str, steps: int, default: float = 0.0) -> float:
        """按步数获取变量历史值。"""
        var = self._vars.get(name)
        if var is None:
            return default
        return var.get_with_lag(steps, default=default)

    def snapshot(self) -> Dict[str, Any]:
        """导出当前所有变量的快照（仅当前值）。"""
        return {name: vs.value for name, vs in self._vars.items()}


