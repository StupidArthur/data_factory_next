"""
程序库

包含各种控制算法和物理模型，例如：
- PID: PID控制器
- SIN: 正弦波生成器
- RANDOM: 随机数生成器
- CYLINDRICAL_TANK: 圆柱水箱模型
- VALVE: 阀门模型
"""

from .sin import SIN
from .random import RANDOM
from .pid import PID
from .cylindrical_tank import CYLINDRICAL_TANK
from .valve import VALVE

# 自动注册算法和模型
from core.instance import InstanceRegistry

InstanceRegistry.register_algorithm("SIN", SIN)
InstanceRegistry.register_algorithm("RANDOM", RANDOM)
InstanceRegistry.register_algorithm("PID", PID)
InstanceRegistry.register_model("CYLINDRICAL_TANK", CYLINDRICAL_TANK)
InstanceRegistry.register_model("VALVE", VALVE)

__all__ = ["SIN", "RANDOM", "PID", "CYLINDRICAL_TANK", "VALVE"]

