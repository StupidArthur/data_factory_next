"""
随机数生成算法

生成在指定范围内随机变化的数值，支持最大步进限制。
"""

import random

from core.instance import InstanceRegistry
from .base import BaseProgram


class RANDOM(BaseProgram):
    """
    随机数生成算法。

    特点：
    - 在 [L, H] 范围内生成随机数
    - 每次变化不超过 max_step（避免突变）
    - 输出：out（当前随机值）
    """

    # 需要存储的属性
    stored_attributes = ["out"]

    # 默认参数
    default_params = {
        "L": 0.0,  # 最小值
        "H": 100.0,  # 最大值
        "max_step": 3.0,  # 最大步进（每次变化不超过此值）
    }

    def __init__(self, cycle_time: float, **kwargs):
        """
        初始化随机数生成器。

        Args:
            cycle_time: 控制器周期（秒）
            **kwargs: 其他参数（L, H, max_step）
        """
        super().__init__(cycle_time, **kwargs)
        # 初始化输出值（在范围内随机）
        self.out = random.uniform(self.L, self.H)

    def execute(self) -> None:
        """
        执行一个周期，生成新的随机值。

        注意：不需要输入参数，算法内部维护当前值。
        """
        # 生成目标值（在范围内）
        target = random.uniform(self.L, self.H)

        # 计算变化量，限制在 max_step 内
        change = target - self.out
        if abs(change) > self.max_step:
            change = self.max_step if change > 0 else -self.max_step

        # 更新输出值
        self.out += change

        # 确保在范围内
        self.out = max(self.L, min(self.H, self.out))


# 注册算法（如果直接导入此模块）
if __name__ != "__main__":
    InstanceRegistry.register_algorithm("RANDOM", RANDOM)

