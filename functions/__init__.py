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
from .function_docs import attach_doc_metadata

# 注册自定义数学函数（带错误处理）
InstanceRegistry.register_function("abs", abs_func)
InstanceRegistry.register_function("sqrt", sqrt_func)

# 注册标准数学函数（来自 math 模块）并附加文档元数据
InstanceRegistry.register_function("sin", math.sin)
attach_doc_metadata(math.sin, "sin")

InstanceRegistry.register_function("cos", math.cos)
attach_doc_metadata(math.cos, "cos")

InstanceRegistry.register_function("tan", math.tan)
attach_doc_metadata(math.tan, "tan")

InstanceRegistry.register_function("log", math.log)
attach_doc_metadata(math.log, "log")

InstanceRegistry.register_function("exp", math.exp)
attach_doc_metadata(math.exp, "exp")

InstanceRegistry.register_function("fabs", math.fabs)
attach_doc_metadata(math.fabs, "fabs")

InstanceRegistry.register_function("asin", math.asin)
attach_doc_metadata(math.asin, "asin")

InstanceRegistry.register_function("acos", math.acos)
attach_doc_metadata(math.acos, "acos")

InstanceRegistry.register_function("atan", math.atan)
attach_doc_metadata(math.atan, "atan")

InstanceRegistry.register_function("floor", math.floor)
attach_doc_metadata(math.floor, "floor")

InstanceRegistry.register_function("ceil", math.ceil)
attach_doc_metadata(math.ceil, "ceil")

# 注册内置函数并附加文档元数据
InstanceRegistry.register_function("min", min)
attach_doc_metadata(min, "min")

InstanceRegistry.register_function("max", max)
attach_doc_metadata(max, "max")

__all__ = []

