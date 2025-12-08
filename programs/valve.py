"""
阀门模型

模拟阀门的开度变化（有延迟，不能瞬间到达目标开度）。
"""

from core.instance import InstanceRegistry
from .base import BaseProgram


class VALVE(BaseProgram):
    """
    阀门模型。

    特点：
    - 有目标开度（target_opening）和当前开度（current_opening）
    - 当前开度会逐渐向目标开度移动（有延迟）
    - 移动速度由 full_travel_time 控制（满行程时间）
    """

    # 文档属性（用于网页展示）
    name = "valve"
    chinese_name = "阀门"
    doc = """
# 阀门模型

模拟阀门的开度变化（有延迟，不能瞬间到达目标开度）。

## 特点

- 有目标开度（target_opening）和当前开度（current_opening）
- 当前开度会逐渐向目标开度移动（有延迟）
- 移动速度由 full_travel_time 控制（满行程时间）

## 使用示例

```yaml
- name: valve1
  type: VALVE
  init_args:
    min_opening: 0.0
    max_opening: 100.0
    full_travel_time: 10.0
    initial_opening: 0.0
  expression: valve1.execute(target_opening=pid1.mv)
```
"""
    params_table = """
| 参数名 | 含义 | 初值 |
|--------|------|------|
| min_opening | 最小开度（%） | 0.0 |
| max_opening | 最大开度（%） | 100.0 |
| full_travel_time | 满行程时间（秒），从最小到最大开度所需时间 | 10.0 |
| initial_opening | 初始开度（%） | 0.0 |
"""

    # 需要存储的属性
    stored_attributes = ["current_opening", "min_opening", "max_opening", "full_travel_time", "initial_opening", "target_opening"]

    # 默认参数
    default_params = {
        "min_opening": 0.0,  # 最小开度（%）
        "max_opening": 100.0,  # 最大开度（%）
        "full_travel_time": 10.0,  # 满行程时间（秒）
        "initial_opening": 0.0,  # 初始开度（%）
    }

    def __init__(self, cycle_time: float, **kwargs):
        """
        初始化阀门模型。

        Args:
            cycle_time: 控制器周期（秒）
            **kwargs: 其他参数
        """
        super().__init__(cycle_time, **kwargs)
        self.current_opening = self.initial_opening
        self.target_opening = self.initial_opening

    def execute(self, target_opening: float = None) -> None:
        """
        执行阀门模型计算。

        Args:
            target_opening: 目标开度（%），范围 min_opening ~ max_opening
        """
        if target_opening is not None:
            self.target_opening = max(self.min_opening, min(self.max_opening, target_opening))

        # 计算移动速度（每秒移动的百分比）
        # 满行程时间 = 从 0% 到 100% 的时间
        max_range = self.max_opening - self.min_opening
        if self.full_travel_time > 0 and max_range > 0:
            speed = max_range / self.full_travel_time  # 每秒移动的百分比
        else:
            speed = float("inf")  # 瞬间到达

        # 计算本次周期应该移动的距离
        distance = speed * self.cycle_time

        # 移动当前开度向目标开度靠近
        diff = self.target_opening - self.current_opening
        if abs(diff) <= distance:
            # 已经到达或超过目标
            self.current_opening = self.target_opening
        else:
            # 向目标移动
            if diff > 0:
                self.current_opening += distance
            else:
                self.current_opening -= distance

        # 确保在范围内
        self.current_opening = max(self.min_opening, min(self.max_opening, self.current_opening))


# 注册模型（如果直接导入此模块）
if __name__ != "__main__":
    InstanceRegistry.register_model("VALVE", VALVE)

