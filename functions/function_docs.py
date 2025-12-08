"""
函数文档元数据

为标准数学函数提供文档元数据，用于网页展示。
"""

import math


# 函数名到文档元数据的映射（全局字典，用于存储无法添加属性的内置函数的文档）
_FUNCTION_DOC_METADATA: dict[str, dict] = {}


# 标准数学函数的文档元数据字典
FUNCTION_DOCS = {
    "sin": {
        "name": "sin",
        "chinese_name": "正弦",
        "doc": """
# sin 函数

计算角度的正弦值。

## 功能

返回给定角度（弧度）的正弦值，结果范围在 [-1, 1] 之间。

## 使用示例

```python
sin(0)           # 返回 0.0
sin(math.pi/2)  # 返回 1.0
sin(math.pi)    # 返回 0.0
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 角度（弧度） | float |
"""
    },
    "cos": {
        "name": "cos",
        "chinese_name": "余弦",
        "doc": """
# cos 函数

计算角度的余弦值。

## 功能

返回给定角度（弧度）的余弦值，结果范围在 [-1, 1] 之间。

## 使用示例

```python
cos(0)           # 返回 1.0
cos(math.pi/2)  # 返回 0.0
cos(math.pi)    # 返回 -1.0
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 角度（弧度） | float |
"""
    },
    "tan": {
        "name": "tan",
        "chinese_name": "正切",
        "doc": """
# tan 函数

计算角度的正切值。

## 功能

返回给定角度（弧度）的正切值。

## 使用示例

```python
tan(0)           # 返回 0.0
tan(math.pi/4)  # 返回 1.0
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 角度（弧度） | float |
"""
    },
    "log": {
        "name": "log",
        "chinese_name": "自然对数",
        "doc": """
# log 函数

计算自然对数（以 e 为底）。

## 功能

返回给定数值的自然对数。

## 使用示例

```python
log(1)      # 返回 0.0
log(math.e) # 返回 1.0
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入数值（必须 > 0） | float |
"""
    },
    "exp": {
        "name": "exp",
        "chinese_name": "指数",
        "doc": """
# exp 函数

计算 e 的 x 次方。

## 功能

返回 e（自然常数，约 2.718）的 x 次方。

## 使用示例

```python
exp(0)  # 返回 1.0
exp(1)  # 返回 2.718281828459045
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 指数 | float |
"""
    },
    "fabs": {
        "name": "fabs",
        "chinese_name": "绝对值（浮点）",
        "doc": """
# fabs 函数

计算浮点数的绝对值。

## 功能

返回输入浮点数的绝对值。

## 使用示例

```python
fabs(-5.5)  # 返回 5.5
fabs(3.14)  # 返回 3.14
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入数值 | float |
"""
    },
    "asin": {
        "name": "asin",
        "chinese_name": "反正弦",
        "doc": """
# asin 函数

计算反正弦值（弧度）。

## 功能

返回给定值的反正弦值（弧度），输入范围 [-1, 1]，输出范围 [-π/2, π/2]。

## 使用示例

```python
asin(0)   # 返回 0.0
asin(1)   # 返回 π/2
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入值（范围 [-1, 1]） | float |
"""
    },
    "acos": {
        "name": "acos",
        "chinese_name": "反余弦",
        "doc": """
# acos 函数

计算反余弦值（弧度）。

## 功能

返回给定值的反余弦值（弧度），输入范围 [-1, 1]，输出范围 [0, π]。

## 使用示例

```python
acos(1)   # 返回 0.0
acos(0)   # 返回 π/2
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入值（范围 [-1, 1]） | float |
"""
    },
    "atan": {
        "name": "atan",
        "chinese_name": "反正切",
        "doc": """
# atan 函数

计算反正切值（弧度）。

## 功能

返回给定值的反正切值（弧度），输出范围 [-π/2, π/2]。

## 使用示例

```python
atan(0)   # 返回 0.0
atan(1)   # 返回 π/4
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入值 | float |
"""
    },
    "floor": {
        "name": "floor",
        "chinese_name": "向下取整",
        "doc": """
# floor 函数

向下取整。

## 功能

返回不大于输入值的最大整数。

## 使用示例

```python
floor(3.7)  # 返回 3.0
floor(-3.7) # 返回 -4.0
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入数值 | float |
"""
    },
    "ceil": {
        "name": "ceil",
        "chinese_name": "向上取整",
        "doc": """
# ceil 函数

向上取整。

## 功能

返回不小于输入值的最小整数。

## 使用示例

```python
ceil(3.2)   # 返回 4.0
ceil(-3.2)  # 返回 -3.0
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| x | 输入数值 | float |
"""
    },
    "min": {
        "name": "min",
        "chinese_name": "最小值",
        "doc": """
# min 函数

返回多个值中的最小值。

## 功能

返回给定参数中的最小值。

## 使用示例

```python
min(3, 1, 5)  # 返回 1
min(3.5, 1.2) # 返回 1.2
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| *args | 多个数值参数 | 可变参数 |
"""
    },
    "max": {
        "name": "max",
        "chinese_name": "最大值",
        "doc": """
# max 函数

返回多个值中的最大值。

## 功能

返回给定参数中的最大值。

## 使用示例

```python
max(3, 1, 5)  # 返回 5
max(3.5, 1.2) # 返回 3.5
```
""",
        "params_table": """
| 参数名 | 含义 | 类型 |
|--------|------|------|
| *args | 多个数值参数 | 可变参数 |
"""
    }
}


def attach_doc_metadata(func, function_name: str):
    """
    为函数附加文档元数据。
    
    对于可以添加属性的函数（如自定义函数），直接在函数对象上设置 `__doc_metadata__` 属性。
    对于无法添加属性的函数（如内置函数），将文档元数据存储到全局字典中。
    
    Args:
        func: 函数对象
        function_name: 函数名称（用于查找文档）
    """
    if function_name not in FUNCTION_DOCS:
        return
    
    doc_metadata = FUNCTION_DOCS[function_name]
    
    # 尝试在函数对象上设置属性（适用于自定义函数）
    try:
        func.__doc_metadata__ = doc_metadata
    except (AttributeError, TypeError):
        # 如果无法设置属性（如内置函数），存储到全局字典中
        _FUNCTION_DOC_METADATA[function_name] = doc_metadata


def get_function_doc_metadata(function_name: str) -> dict | None:
    """
    获取函数的文档元数据。
    
    先尝试从函数对象的 `__doc_metadata__` 属性获取，
    如果不存在，则从全局字典中获取。
    
    Args:
        function_name: 函数名称
    
    Returns:
        文档元数据字典，如果不存在则返回 None
    """
    # 先从全局字典中查找（适用于内置函数）
    if function_name in _FUNCTION_DOC_METADATA:
        return _FUNCTION_DOC_METADATA[function_name]
    
    # 如果全局字典中没有，返回 None
    # 注意：对于自定义函数，文档元数据存储在函数对象的 __doc_metadata__ 属性中
    # 这部分由 DocHelper.get_function_doc() 处理
    return None

