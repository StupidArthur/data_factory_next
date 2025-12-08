"""
圆柱水箱模型

基于托里拆利定律实现液位动态计算。
"""

import math

from core.instance import InstanceRegistry
from .base import BaseProgram


class CYLINDRICAL_TANK(BaseProgram):
    """
    圆柱体水箱模型。

    物理模型：
    - 一个圆柱体的水箱
    - 在水箱最高同高的地方有一个圆形的入水管口，由一个阀门（0~100%）控制
    - 在水箱最低的地方有一个圆形的出水口，一直在出水
    - 出水的流量与当前水位高度相关（根据托里拆利定律）
    """

    # 文档属性（用于网页展示）
    name = "cylindrical_tank"
    chinese_name = "圆柱水箱"
    doc = """
# 圆柱体水箱模型

基于托里拆利定律实现液位动态计算。

## 物理模型

- 一个圆柱体的水箱
- 在水箱最高同高的地方有一个圆形的入水管口，由一个阀门（0~100%）控制
- 在水箱最低的地方有一个圆形的出水口，一直在出水
- 出水的流量与当前水位高度相关（根据托里拆利定律：v = sqrt(2gh)）

## 使用示例

```yaml
- name: tank1
  type: CYLINDRICAL_TANK
  init_args:
    height: 10.0
    radius: 1.0
    initial_level: 0.0
  expression: tank1.execute(valve_opening=valve1.current_opening)
```
"""
    params_table = """
| 参数名 | 含义 | 初值 |
|--------|------|------|
| height | 水箱高度（米） | 2.0 |
| radius | 水箱半径（米） | 0.5 |
| inlet_area | 入水管面积（平方米） | 0.06 |
| inlet_velocity | 入水口水流速（米/秒） | 3.0 |
| outlet_area | 出水口面积（平方米） | 0.001 |
| initial_level | 初始水位（米） | 0.0 |
"""

    # 需要存储的属性
    stored_attributes = ["level", "height", "radius", "inlet_area", "inlet_velocity", "outlet_area", "initial_level", "valve_opening"]

    # 重力加速度（米/秒²）
    GRAVITY = 9.81

    # 默认参数
    default_params = {
        "height": 2.0,  # 水箱高度（米）
        "radius": 0.5,  # 水箱半径（米）
        "inlet_area": 0.06,  # 入水管面积（平方米）
        "inlet_velocity": 3.0,  # 入水口水流速（米/秒）
        "outlet_area": 0.001,  # 出水口面积（平方米）
        "initial_level": 0.0,  # 初始水位（米）
    }

    def __init__(self, cycle_time: float, **kwargs):
        """
        初始化圆柱体水箱模型。

        Args:
            cycle_time: 控制器周期（秒）
            **kwargs: 其他参数
        """
        super().__init__(cycle_time, **kwargs)
        self.level = self.initial_level

        # 水箱底面积
        self.base_area = math.pi * self.radius ** 2

        # 记录最后一次的输入参数值
        self.valve_opening = 0.0

    def execute(self, valve_opening: float = None) -> None:
        """
        执行水箱模型计算。

        Args:
            valve_opening: 入水管阀门开度（%），范围0~100
        """
        if valve_opening is not None:
            self.valve_opening = max(0.0, min(100.0, valve_opening))

        # 限制阀门开度范围
        valve_opening_ratio = self.valve_opening / 100.0

        # 计算入水流量（立方米/秒）
        inlet_flow = self.inlet_area * self.inlet_velocity * valve_opening_ratio

        # 计算出水流量（立方米/秒）
        # 根据托里拆利定律：v = sqrt(2gh)
        if self.level > 0:
            outlet_velocity = math.sqrt(2 * self.GRAVITY * self.level)
            outlet_flow = self.outlet_area * outlet_velocity
        else:
            outlet_flow = 0.0

        # 计算净流量
        net_flow = inlet_flow - outlet_flow

        # 计算水位变化
        volume_change = net_flow * self.cycle_time
        level_change = volume_change / self.base_area

        # 更新水位
        self.level += level_change

        # 限制水位范围
        self.level = max(0.0, min(self.height, self.level))


# 注册模型（如果直接导入此模块）
if __name__ != "__main__":
    InstanceRegistry.register_model("CYLINDRICAL_TANK", CYLINDRICAL_TANK)

