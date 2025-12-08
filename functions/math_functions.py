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


# 函数文档元数据（用于网页展示）
abs_func.__doc_metadata__ = {
    "name": "abs",
    "chinese_name": "绝对值",
    "doc": """
# abs 函数

计算数值的绝对值。

## 功能

返回输入数值的绝对值，即去掉符号的数值。

## 使用示例

```python
abs(-5)      # 返回 5.0
abs(3.14)    # 返回 3.14
abs(0)       # 返回 0.0
```
""",
    "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入数值 | int 或 float |
"""
}


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


# 函数文档元数据（用于网页展示）
sqrt_func.__doc_metadata__ = {
    "name": "sqrt",
    "chinese_name": "平方根",
    "doc": """
# sqrt 函数

计算数值的平方根。

## 功能

返回输入数值的平方根。输入值必须 >= 0，否则会抛出 ValueError。

## 使用示例

```python
sqrt(4)      # 返回 2.0
sqrt(9.0)    # 返回 3.0
sqrt(2)      # 返回 1.4142135623730951
```
""",
    "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入数值（必须 >= 0） | int 或 float |
"""
}

