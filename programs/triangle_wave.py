"""
三角波生成算法

根据配置的周期（秒）和控制器周期，生成三角波信号。
"""

from core.instance import InstanceRegistry
from .base import BaseProgram


class TRIANGLE_WAVE(BaseProgram):
    """
    三角波生成算法。

    特点：
    - 根据周期（秒）和控制器周期，生成三角波信号
    - 输出：从 -amplitude 线性增长到 amplitude，然后线性下降回 -amplitude
    - 支持相位偏移
    """

    # 文档属性（用于网页展示）
    name = "triangle_wave"
    chinese_name = "三角波"
    doc = """
# 三角波生成算法

根据配置的周期（秒）和控制器周期，生成三角波信号。

## 特点

- 根据周期（秒）和控制器周期，生成三角波信号
- 输出：从 -amplitude 线性增长到 amplitude，然后线性下降回 -amplitude
- 支持相位偏移，可以生成不同相位的三角波

## 使用示例

```yaml
- name: triangle1
  type: TRIANGLE_WAVE
  init_args:
    amplitude: 100.0
    period: 1200
    phase: 0.0
  expression: triangle1.execute()
```
"""
    params_table = """
| 参数名 | 含义 | 初值 |
|--------|------|------|
| amplitude | 振幅，三角波的最大值 | 100.0 |
| period | 周期（秒），一个完整三角波的时间长度 | 1200.0 |
| phase | 相位偏移（0-1之间），表示周期内的偏移比例 | 0.0 |
"""

    # 需要存储的属性
    stored_attributes = ["out", "amplitude", "period", "phase"]

    # 默认参数
    default_params = {
        "amplitude": 100.0,  # 振幅
        "period": 1200.0,  # 周期（秒）
        "phase": 0.0,  # 相位偏移（0-1之间，表示周期内的偏移比例）
    }

    def __init__(self, cycle_time: float, **kwargs):
        """
        初始化三角波生成器。

        Args:
            cycle_time: 控制器周期（秒）
            **kwargs: 其他参数（amplitude, period, phase）
        """
        super().__init__(cycle_time, **kwargs)
        self._cycle_count = 0

    def execute(self) -> None:
        """
        执行一个周期，生成三角波值。

        注意：不需要输入参数，算法内部维护周期计数。
        """
        # 计算一个完整周期需要多少个控制器周期
        cycles_per_period = self.period / self.cycle_time

        # 计算当前周期内的位置（0-1之间），考虑相位偏移
        position = ((self._cycle_count % cycles_per_period) / cycles_per_period + self.phase) % 1.0

        # 三角波：前半个周期从 -amplitude 线性增长到 amplitude
        # 后半个周期从 amplitude 线性下降到 -amplitude
        if position < 0.5:
            # 上升阶段：从 -amplitude 到 amplitude
            self.out = -self.amplitude + 4 * self.amplitude * position
        else:
            # 下降阶段：从 amplitude 到 -amplitude
            self.out = self.amplitude - 4 * self.amplitude * (position - 0.5)

        # 更新周期计数
        self._cycle_count += 1


# 注册算法（如果直接导入此模块）
if __name__ != "__main__":
    InstanceRegistry.register_algorithm("TRIANGLE_WAVE", TRIANGLE_WAVE)

