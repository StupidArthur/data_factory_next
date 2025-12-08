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
    - 参数：pb（比例带）、ti（积分时间）、td（微分时间）
    """

    # 文档属性（用于网页展示）
    name = "pid"
    chinese_name = "PID控制器"
    doc = """
# PID控制算法

通用的PID（比例-积分-微分）控制算法，用于过程控制。

## 特点

- **输入**：pv（过程变量）、sv（设定值）
- **输出**：mv（操作变量）
- **控制方式**：比例项 + 积分项 + 微分项

## 控制公式

- 比例项：`p_term = pb * error`
- 积分项：`i_term = pb / ti * integral`（当 ti > 0 时）
- 微分项：`d_term = pb * td * (error - last_error) / cycle_time`
- 输出：`mv = p_term + i_term + d_term`（限制在 [l, h] 范围内）

## 使用示例

```yaml
- name: pid1
  type: PID
  init_args:
    pb: 120
    ti: 30
    td: 0.15
    sv: 1.0
    h: 100.0
    l: 0.0
  expression: pid1.execute(pv=tank1.level, sv=sin1.out)
```
"""
    params_table = """
| 参数名 | 含义 | 初值 |
|--------|------|------|
| pb | 比例带，控制器的比例增益参数 | 12.0 |
| ti | 积分时间（秒），用于消除稳态误差 | 30.0 |
| td | 微分时间（秒），用于改善动态响应 | 0.15 |
| pv | 过程变量初始值，当前被控变量的值 | 0.0 |
| sv | 设定值，期望的目标值 | 0.0 |
| mv | 操作变量初始值，控制器的输出值 | 0.0 |
| h | 输出上限，mv的最大值 | 100.0 |
| l | 输出下限，mv的最小值 | 0.0 |
"""

    # 需要存储的属性
    stored_attributes = ["mv", "pv", "sv", "pb", "ti", "td", "h", "l"]

    # 默认参数
    default_params = {
        "pb": 12.0,  # 比例带
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
        p_term = self.pb * error

        # 积分项
        self._integral += error * self.cycle_time
        i_term = self.pb / self.ti * self._integral if self.ti > 0 else 0.0

        # 微分项
        d_term = self.pb * self.td * (error - self._last_error) / self.cycle_time
        self._last_error = error

        # 计算输出
        self.mv = p_term + i_term + d_term

        # 限制输出范围
        self.mv = max(self.l, min(self.h, self.mv))


# 注册算法（如果直接导入此模块）
if __name__ != "__main__":
    InstanceRegistry.register_algorithm("PID", PID)

