"""
正弦波生成算法

根据配置的周期（秒）和控制器周期，生成正弦波信号。
"""

import math

from core.instance import InstanceRegistry
from .base import BaseProgram


class SINE_WAVE(BaseProgram):
    """
    正弦波生成算法。

    特点：
    - 根据周期（秒）和控制器周期，计算每个周期应该生成的角度
    - 输出：out = amplitude * sin(2π * (cycle_count / cycles_per_period) + phase)
    """

    # 文档属性（用于网页展示）
    name = "sine_wave"
    chinese_name = "正弦波"
    doc = """
# 正弦波生成算法

根据配置的周期（秒）和控制器周期，生成正弦波信号。

## 特点

- 根据周期（秒）和控制器周期，计算每个周期应该生成的角度
- 输出公式：`out = amplitude * sin(2π * (cycle_count / cycles_per_period) + phase)`
- 支持相位偏移，可以生成不同相位的正弦波

## 使用示例

```yaml
- name: sin1
  type: SINE_WAVE
  init_args:
    amplitude: 100.0
    period: 1200
    phase: 0.0
  expression: sin1.execute()
```
"""
    params_table = """
| 参数名 | 含义 | 初值 |
|--------|------|------|
| amplitude | 振幅，正弦波的最大值 | 100.0 |
| period | 周期（秒），一个完整正弦波的时间长度 | 1200.0 |
| phase | 相位（弧度），正弦波的初始相位偏移 | 0.0 |
"""

    # 需要存储的属性
    stored_attributes = ["out", "amplitude", "period", "phase"]

    # 默认参数
    default_params = {
        "amplitude": 100.0,  # 振幅
        "period": 1200.0,  # 周期（秒）
        "phase": 0.0,  # 相位（弧度）
    }

    def __init__(self, cycle_time: float, **kwargs):
        """
        初始化正弦波生成器。

        Args:
            cycle_time: 控制器周期（秒）
            **kwargs: 其他参数（amplitude, period, phase）
        """
        super().__init__(cycle_time, **kwargs)
        self._cycle_count = 0

    def execute(self) -> None:
        """
        执行一个周期，生成正弦波值。

        注意：不需要输入参数，算法内部维护周期计数。
        """
        # 计算一个完整周期需要多少个控制器周期
        cycles_per_period = self.period / self.cycle_time

        # 计算当前角度（归一化到 [0, 2π)）
        angle = 2 * math.pi * (self._cycle_count % cycles_per_period) / cycles_per_period + self.phase

        # 生成正弦波值
        self.out = self.amplitude * math.sin(angle)

        # 更新周期计数
        self._cycle_count += 1


# 注册算法（如果直接导入此模块）
if __name__ != "__main__":
    InstanceRegistry.register_algorithm("SINE_WAVE", SINE_WAVE)

