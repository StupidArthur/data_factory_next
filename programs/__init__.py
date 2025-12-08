"""
程序库

包含各种控制算法和物理模型，例如：
- PID: PID控制器
- SINE_WAVE: 正弦波生成器
- SQUARE_WAVE: 方波生成器
- TRIANGLE_WAVE: 三角波生成器
- LIST_WAVE: 列表波生成器（循环播放）
- RANDOM: 随机数生成器
- CYLINDRICAL_TANK: 圆柱水箱模型
- VALVE: 阀门模型
"""

from .sine_wave import SINE_WAVE
from .square_wave import SQUARE_WAVE
from .triangle_wave import TRIANGLE_WAVE
from .list_wave import LIST_WAVE
from .random import RANDOM
from .pid import PID
from .cylindrical_tank import CYLINDRICAL_TANK
from .valve import VALVE

# 自动注册算法和模型
from core.instance import InstanceRegistry

InstanceRegistry.register_algorithm("SINE_WAVE", SINE_WAVE)
InstanceRegistry.register_algorithm("SQUARE_WAVE", SQUARE_WAVE)
InstanceRegistry.register_algorithm("TRIANGLE_WAVE", TRIANGLE_WAVE)
InstanceRegistry.register_algorithm("LIST_WAVE", LIST_WAVE)
InstanceRegistry.register_algorithm("RANDOM", RANDOM)
InstanceRegistry.register_algorithm("PID", PID)
InstanceRegistry.register_model("CYLINDRICAL_TANK", CYLINDRICAL_TANK)
InstanceRegistry.register_model("VALVE", VALVE)

__all__ = ["SINE_WAVE", "SQUARE_WAVE", "TRIANGLE_WAVE", "LIST_WAVE", "RANDOM", "PID", "CYLINDRICAL_TANK", "VALVE"]

