"""
列表波生成算法

根据配置的列表值和时间点，循环播放列表波形。
"""

from typing import List, Tuple

from core.instance import InstanceRegistry
from .base import BaseProgram


class LIST_WAVE(BaseProgram):
    """
    列表波生成算法。

    特点：
    - 根据配置的列表值和时间点，循环播放列表波形
    - init_args 格式：wave_list = [(v1, t1), (v2, t2), (v3, t3), ...]
    - 其中 v 是值，t 是该值持续的时间（秒）
    - 播放完整个列表后，循环从头开始
    """

    # 文档属性（用于网页展示）
    name = "list_wave"
    chinese_name = "列表波"
    doc = """
# 列表波生成算法

根据配置的列表值和时间点，循环播放列表波形。

## 特点

- 根据配置的列表值和时间点，循环播放列表波形
- 支持任意自定义波形模式
- 播放完整个列表后，循环从头开始

## 使用示例

```yaml
- name: list1
  type: LIST_WAVE
  init_args:
    wave_list:
      - [10.0, 5.0]    # 值为10，持续5秒
      - [20.0, 3.0]    # 值为20，持续3秒
      - [0.0, 2.0]     # 值为0，持续2秒
  expression: list1.execute()
```
"""
    params_table = """
| 参数名 | 含义 | 初值 |
|--------|------|------|
| wave_list | 波形列表，格式：[(v1, t1), (v2, t2), ...]，其中v是值，t是持续时间（秒） | [(0.0, 1.0)] |
"""

    # 需要存储的属性
    stored_attributes = ["out", "wave_list"]

    # 默认参数
    default_params = {
        "wave_list": [(0.0, 1.0)],  # 默认：值为0，持续1秒
    }

    def __init__(self, cycle_time: float, **kwargs):
        """
        初始化列表波生成器。

        Args:
            cycle_time: 控制器周期（秒）
            **kwargs: 其他参数（wave_list）
        """
        super().__init__(cycle_time, **kwargs)
        
        # 验证 wave_list 格式
        if not isinstance(self.wave_list, list) or len(self.wave_list) == 0:
            raise ValueError("wave_list 必须是非空列表，格式：[(v1, t1), (v2, t2), ...]")
        
        for item in self.wave_list:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError("wave_list 中的每个元素必须是 (value, time) 格式")
            if item[1] <= 0:
                raise ValueError("时间值必须大于0")
        
        # 计算每个时间点对应的周期数
        self._cycle_counts: List[int] = []
        for _, time in self.wave_list:
            cycles = int(time / self.cycle_time)
            if cycles == 0:
                cycles = 1  # 至少持续1个周期
            self._cycle_counts.append(cycles)
        
        # 计算总周期数
        self._total_cycles = sum(self._cycle_counts)
        
        # 内部状态
        self._cycle_count = 0  # 总周期计数
        self._current_segment = 0  # 当前段索引
        self._segment_cycle_count = 0  # 当前段内的周期计数

    def execute(self) -> None:
        """
        执行一个周期，生成列表波值。

        注意：不需要输入参数，算法内部维护周期计数。
        """
        # 获取当前段的值
        current_value, _ = self.wave_list[self._current_segment]
        self.out = current_value
        
        # 更新当前段内的周期计数
        self._segment_cycle_count += 1
        
        # 如果当前段的时间已用完，切换到下一段
        if self._segment_cycle_count >= self._cycle_counts[self._current_segment]:
            self._segment_cycle_count = 0
            self._current_segment = (self._current_segment + 1) % len(self.wave_list)
        
        # 更新总周期计数
        self._cycle_count += 1


# 注册算法（如果直接导入此模块）
if __name__ != "__main__":
    InstanceRegistry.register_algorithm("LIST_WAVE", LIST_WAVE)

