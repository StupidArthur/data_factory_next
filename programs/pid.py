"""
PID控制算法

通用的PID（比例-积分-微分）控制算法。
"""

from core.instance import InstanceRegistry
from .base import BaseProgram


class PID(BaseProgram):
    """
    PID控制算法。

    特点：
    - 输入：pv（过程变量）、sv（设定值）
    - 输出：mv（操作变量）
    - 参数：kp（比例系数）、ti（积分时间）、td（微分时间）
    """

    # 需要存储的属性
    stored_attributes = ["mv", "pv", "sv"]

    # 默认参数
    default_params = {
        "kp": 12.0,  # 比例系数
        "ti": 30.0,  # 积分时间（秒）
        "td": 0.15,  # 微分时间（秒）
        "pv": 0.0,  # 过程变量初始值
        "sv": 0.0,  # 设定值
        "mv": 0.0,  # 输出值初始值
        "h": 100.0,  # 输出上限
        "l": 0.0,  # 输出下限
    }

    def __init__(self, cycle_time: float, **kwargs):
        """
        初始化PID算法。

        Args:
            cycle_time: 控制器周期（秒）
            **kwargs: 其他参数
        """
        super().__init__(cycle_time, **kwargs)
        # PID 内部状态
        self._last_error = 0.0
        self._integral = 0.0

    def execute(self, pv: float = None, sv: float = None) -> None:
        """
        执行 PID 计算。

        Args:
            pv: 过程变量（如果提供则更新）
            sv: 设定值（如果提供则更新）
        """
        if pv is not None:
            self.pv = pv
        if sv is not None:
            self.sv = sv

        # 计算误差
        error = self.sv - self.pv

        # 比例项
        p_term = self.kp * error

        # 积分项
        self._integral += error * self.cycle_time
        i_term = self.kp / self.ti * self._integral if self.ti > 0 else 0.0

        # 微分项
        d_term = self.kp * self.td * (error - self._last_error) / self.cycle_time
        self._last_error = error

        # 计算输出
        self.mv = p_term + i_term + d_term

        # 限制输出范围
        self.mv = max(self.l, min(self.h, self.mv))


# 注册算法（如果直接导入此模块）
if __name__ != "__main__":
    InstanceRegistry.register_algorithm("PID", PID)

