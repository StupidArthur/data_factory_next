"""
数学函数库

提供可以在表达式中直接调用的数学函数。
所有函数都是无状态的，只接受参数并返回计算结果。
"""

import math
from typing import Union


def abs_func(x: Union[int, float]) -> float:
    """
    计算绝对值。

    Args:
        x: 输入数值

    Returns:
        绝对值（浮点数）

    Examples:
        abs_func(-5) -> 5.0
        abs_func(3.14) -> 3.14
    """
    return float(abs(x))


def sqrt_func(x: Union[int, float]) -> float:
    """
    计算平方根。

    Args:
        x: 输入数值（必须 >= 0），可以是 AttributeProxy 或其他可转换为浮点数的对象

    Returns:
        平方根（浮点数）

    Raises:
        ValueError: 如果 x < 0

    Examples:
        sqrt_func(4) -> 2.0
        sqrt_func(9.0) -> 3.0
    """
    # 转换为浮点数（支持 AttributeProxy 等对象）
    x_float = float(x)
    if x_float < 0:
        raise ValueError(f"sqrt 函数不能接受负数: {x_float}")
    return float(math.sqrt(x_float))

