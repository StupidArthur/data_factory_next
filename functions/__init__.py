"""
无状态函数库

包含可以在表达式中直接调用的数学函数，例如：
- abs, sqrt, sin, cos, tan, log, exp 等

所有函数通过 InstanceRegistry 注册，可以在表达式中直接使用。
"""

import math

from core.instance import InstanceRegistry

# 导入自定义函数
from .math_functions import abs_func, sqrt_func

# 注册自定义数学函数（带错误处理）
InstanceRegistry.register_function("abs", abs_func)
InstanceRegistry.register_function("sqrt", sqrt_func)

# 注册标准数学函数（来自 math 模块）
InstanceRegistry.register_function("sin", math.sin)
InstanceRegistry.register_function("cos", math.cos)
InstanceRegistry.register_function("tan", math.tan)
InstanceRegistry.register_function("log", math.log)
InstanceRegistry.register_function("exp", math.exp)
InstanceRegistry.register_function("fabs", math.fabs)
InstanceRegistry.register_function("asin", math.asin)
InstanceRegistry.register_function("acos", math.acos)
InstanceRegistry.register_function("atan", math.atan)
InstanceRegistry.register_function("floor", math.floor)
InstanceRegistry.register_function("ceil", math.ceil)

# 注册内置函数
InstanceRegistry.register_function("min", min)
InstanceRegistry.register_function("max", max)

__all__ = []

