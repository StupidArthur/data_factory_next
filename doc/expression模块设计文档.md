# Expression 模块设计文档

## 1. 模块概述

`expression` 模块是 data_next 系统的核心表达式执行引擎，负责解析和执行 DSL 表达式。该模块支持复杂的表达式语法，包括：

- 四则混合运算、小括号
- 方法调用：`instance.execute(...)`
- 属性访问：`instance.attribute`
- 函数调用：`abs()`, `sqrt()` 等
- 历史数据访问：`variable[-N]` 或 `instance.attribute[-N]`
- 赋值表达式：`variable = expression`（用于 Variable 类型）

### 1.1 设计目标

1. **安全性**：通过 AST 验证确保表达式在受控环境中执行，防止恶意代码注入
2. **灵活性**：支持复杂的表达式语法，满足各种计算场景
3. **可扩展性**：通过代理模式支持实例属性和方法调用
4. **性能**：编译表达式为 code object，提高执行效率

### 1.2 模块位置

- 文件路径：`core/expression.py`
- 依赖模块：
  - `core/variable.py`：变量存储和历史数据管理
  - `core/instance.py`：实例注册表

## 2. 架构设计

### 2.1 整体架构

```
ExpressionNode/AlgorithmNode
    ↓
ExpressionEvaluator
    ↓
AST 解析与验证
    ↓
执行环境构建（env）
    ├── InstanceProxy（实例代理）
    ├── AttributeProxy（属性代理）
    ├── VariableAccessor（变量访问器）
    └── 无状态函数（从 InstanceRegistry 获取）
    ↓
编译与执行（eval）
    ↓
返回结果
```

### 2.2 核心组件关系

```
ExpressionEvaluator
    ├── 依赖 VariableStore（变量存储）
    ├── 依赖 InstanceRegistry（实例注册表）
    ├── 创建 InstanceProxy（实例代理）
    ├── 创建 AttributeProxy（属性代理）
    └── 创建 VariableAccessor（变量访问器）

ExpressionNode
    ├── 持有 ExpressionConfig（配置）
    ├── 使用 ExpressionEvaluator（求值器）
    └── 写入 VariableStore（结果存储）

AlgorithmNode
    ├── 持有算法实例
    ├── 解析方法调用表达式
    ├── 使用 ExpressionEvaluator（参数解析）
    └── 写入 VariableStore（属性存储）
```

## 3. 核心组件详解

### 3.1 ExpressionError

**职责**：表达式执行相关错误的异常类。

**定义**：
```python
class ExpressionError(Exception):
    """表达式执行相关错误。"""
```

**使用场景**：
- AST 节点验证失败
- 表达式解析失败
- 表达式执行失败

### 3.2 ExpressionConfig

**职责**：表达式节点配置，定义表达式的名称和表达式字符串。

**数据结构**：
```python
@dataclass
class ExpressionConfig:
    name: str          # 节点名称（变量名或实例名）
    expression: str    # 表达式字符串
```

**示例**：
```python
# Variable 类型
ExpressionConfig(
    name="non_sense_3",
    expression="non_sense_1[-30] + 2 * non_sense_2"
)

# 算法/模型类型
ExpressionConfig(
    name="pid1",
    expression="pid1.execute(PV=tank1.level, SV=sin1.out)"
)
```

### 3.3 ExpressionEvaluator

**职责**：表达式求值器，负责解析、验证和执行表达式。

**核心方法**：

#### 3.3.1 `evaluate(expression: str) -> float`

**功能**：执行表达式，返回数值结果。

**执行流程**：
1. 使用 `ast.parse()` 解析表达式为 AST
2. 调用 `_validate_ast()` 验证 AST 节点类型
3. 调用 `_extract_variable_names()` 提取变量名
4. 调用 `_build_env()` 构建执行环境
5. 编译 AST 为 code object
6. 在受控环境中执行（`eval(compiled, {"__builtins__": {}}, env)`）

**关键设计**：
- 使用 `{"__builtins__": {}}` 禁用内置函数，提高安全性
- 只允许特定的 AST 节点类型，防止代码注入

#### 3.3.2 `_validate_ast(node: ast.AST) -> None`

**功能**：验证 AST 节点是否允许。

**允许的节点类型**：
- `Expression`：表达式根节点
- `BinOp`：二元运算（+、-、*、/ 等）
- `UnaryOp`：一元运算（+、-、not 等）
- `Call`：函数调用和方法调用（支持关键字参数）
- `Attribute`：属性访问（`instance.attribute`）
- `Subscript`：下标访问（`variable[-N]`）
- `Name`：名称引用（变量名、函数名）
- `Constant` / `Num`：常量
- `Assign`：赋值表达式（用于 Variable 类型）

**不允许的节点类型**：
- `Import` / `ImportFrom`：禁止导入
- `For` / `While`：禁止循环
- `If` / `IfExp`：禁止条件语句（可扩展支持）
- `Lambda`：禁止匿名函数
- 其他未明确允许的节点类型

#### 3.3.3 `_extract_variable_names(node: ast.AST) -> set[str]`

**功能**：提取表达式中的所有变量名（不在 instances 中的名称）。

**逻辑**：
1. 遍历 AST，查找所有 `ast.Name` 节点
2. 排除实例名（在 `instances` 字典中）
3. 排除函数名（在 `InstanceRegistry` 中注册的函数）
4. 剩余的名称即为变量名

#### 3.3.4 `_build_env(variable_names: set[str]) -> Dict[str, Any]`

**功能**：构造表达式执行环境。

**环境组成**：
1. **实例代理**：为每个实例创建 `InstanceProxy` 对象
2. **无状态函数**：从 `InstanceRegistry` 获取所有注册的函数
3. **变量访问器**：为每个变量创建 `VariableAccessor` 对象

### 3.4 InstanceProxy

**职责**：实例代理对象，用于在表达式中访问实例属性和调用方法。

**设计模式**：代理模式

**支持的操作**：
- `instance.attribute`：访问实例属性（返回 `AttributeProxy`）
- `instance.execute(...)`：调用实例的 `execute` 方法

**实现细节**：
```python
class InstanceProxy:
    def __getattr__(self, name: str) -> AttributeProxy:
        """获取属性代理"""
        return AttributeProxy(...)
    
    def execute(self, **kwargs: Any) -> None:
        """调用实例的 execute 方法"""
        self._instance.execute(**kwargs)
```

**使用示例**：
```python
# 在表达式中使用
pid1.MV              # 访问 pid1 的 MV 属性
pid1.execute(PV=10)  # 调用 pid1 的 execute 方法
```

### 3.5 AttributeProxy

**职责**：属性代理对象，支持当前值访问和历史值访问。

**支持的操作**：
- `float(proxy)` 或直接使用：获取当前值
- `proxy[-N]`：获取历史值（N 步之前）
- 数值运算：`+`、`-`、`*`、`/`（支持左运算和右运算）

**实现细节**：
```python
class AttributeProxy:
    def __float__(self) -> float:
        """获取当前值（优先从 VariableStore 获取）"""
        # 优先从 VariableStore 获取（可能已更新）
        # 否则从实例属性获取
    
    def __getitem__(self, lag_steps: int) -> float:
        """获取历史值"""
        # 使用 VariableStore.get_with_lag() 获取历史值
    
    # 数值运算支持
    def __add__(self, other: Any) -> float: ...
    def __mul__(self, other: Any) -> float: ...
    # ... 其他运算
```

**存储键名规则**：
- 使用 `instance_name.attribute_name` 作为存储键
- 例如：`pid1.MV` 存储在 `VariableStore` 中的键名为 `"pid1.MV"`

**使用示例**：
```python
# 在表达式中使用
tank1.level          # 当前值
tank1.level[-30]     # 30 步之前的值
tank1.level + 10     # 当前值 + 10
```

### 3.6 VariableAccessor

**职责**：变量访问器，支持变量当前值访问和历史值访问。

**支持的操作**：
- `float(accessor)` 或直接使用：获取当前值
- `accessor[-N]`：获取历史值（N 步之前）
- 数值运算：`+`、`-`、`*`、`/`（支持左运算和右运算）

**实现细节**：
```python
class VariableAccessor:
    def __float__(self) -> float:
        """获取当前值"""
        return float(self._vars.get(self._var_name, 0.0))
    
    def __getitem__(self, lag_steps: int) -> float:
        """获取历史值"""
        return float(self._vars.get_with_lag(self._var_name, lag_steps, 0.0))
    
    # 数值运算支持（与 AttributeProxy 相同）
```

**存储键名规则**：
- 直接使用变量名作为存储键
- 例如：`non_sense_3` 存储在 `VariableStore` 中的键名为 `"non_sense_3"`

**使用示例**：
```python
# 在表达式中使用
non_sense_1          # 当前值
non_sense_1[-30]      # 30 步之前的值
non_sense_1 * 2       # 当前值 * 2
```

### 3.7 ExpressionNode

**职责**：表达式节点（用于 Variable 类型），每个周期执行一次表达式计算，结果写入 VariableStore。

**核心方法**：

#### 3.7.1 `step(vars_store: VariableStore) -> float`

**功能**：执行一个周期计算。

**执行流程**：
1. 创建 `ExpressionEvaluator`（传入 `vars_store` 和 `instances`）
2. 检查表达式是否是赋值表达式（`variable_name = expression`）
   - 如果是赋值表达式，提取右侧表达式执行
   - 如果不是，直接执行表达式
3. 调用 `evaluator.evaluate()` 得到计算结果
4. 将结果写入 `VariableStore`（使用 `config.name` 作为键名）
5. 返回计算结果

**赋值表达式处理**：
- 支持 `variable_name = expression` 格式
- 使用 `ast.parse()` 检测是否为 `ast.Assign` 节点
- 提取右侧表达式字符串（使用 `ast.unparse()` 或手动解析）

**使用示例**：
```python
# 配置
config = ExpressionConfig(
    name="non_sense_3",
    expression="non_sense_3 = non_sense_1[-30] + 2 * non_sense_2"
)

# 执行
node = ExpressionNode(config, instances)
value = node.step(vars_store)  # 计算结果并写入 VariableStore
```

### 3.8 AlgorithmNode

**职责**：算法节点（用于算法/模型类型），每个周期调用实例的 `execute` 方法，并存储指定属性。

**核心方法**：

#### 3.8.1 `_parse_expression(expression: str) -> Dict[str, str]`

**功能**：解析表达式，提取方法调用的关键字参数。

**解析逻辑**：
1. 使用 `ast.parse()` 解析表达式
2. 验证根节点是 `ast.Call`（方法调用）
3. 遍历 `node.keywords`，提取关键字参数
4. 将参数值转换为字符串表达式（用于后续解析）

**参数值转换**：
- 支持 `ast.Name`：变量名
- 支持 `ast.Attribute`：属性访问（`instance.attribute`）
- 支持 `ast.Subscript`：历史数据访问（`variable[-N]` 或 `instance.attribute[-N]`）
- 支持 `ast.Constant` / `ast.Num`：常量
- 复杂表达式使用 `ast.unparse()` 或 `repr()` 作为后备

**返回格式**：
```python
{
    "pv": "tank1.level",
    "sv": "sin1.out"
}
```

#### 3.8.2 `step(vars_store: VariableStore) -> None`

**功能**：执行一个周期。

**执行流程**：
1. 创建 `ExpressionEvaluator`（用于解析参数值）
2. 遍历 `_parsed_args`，解析每个参数表达式
3. 调用 `evaluator.evaluate()` 得到参数值
4. 调用实例的 `execute(**resolved_args)` 方法
5. 遍历 `_stored_attributes`，将实例属性写入 `VariableStore`

**属性存储规则**：
- 使用 `instance_name.attribute_name` 作为存储键
- 例如：`pid1.MV` 存储在 `VariableStore` 中的键名为 `"pid1.MV"`

**使用示例**：
```python
# 配置
instance = PID(...)
expression = "pid1.execute(PV=tank1.level, SV=sin1.out)"
stored_attributes = ["mv", "pv", "sv", "error"]

# 执行
node = AlgorithmNode(instance, expression, stored_attributes, "pid1", instances)
node.step(vars_store)  # 调用 execute 并存储属性
```

## 4. 数据流

### 4.1 ExpressionNode 数据流

```
ExpressionConfig
    ↓
ExpressionNode.step()
    ↓
ExpressionEvaluator.evaluate()
    ├── AST 解析
    ├── AST 验证
    ├── 变量名提取
    ├── 执行环境构建
    │   ├── InstanceProxy（实例代理）
    │   ├── AttributeProxy（属性代理）
    │   ├── VariableAccessor（变量访问器）
    │   └── 无状态函数
    ├── 编译与执行
    └── 返回结果
    ↓
VariableStore.set(name, value)
    ↓
结果写入历史缓冲区
```

### 4.2 AlgorithmNode 数据流

```
AlgorithmNode.step()
    ↓
解析参数表达式
    ├── ExpressionEvaluator.evaluate()
    └── 解析每个参数值
    ↓
instance.execute(**resolved_args)
    ↓
遍历 stored_attributes
    ↓
VariableStore.set(f"{instance_name}.{attr_name}", value)
    ↓
属性值写入历史缓冲区
```

### 4.3 历史数据访问流程

```
表达式中的 variable[-N] 或 instance.attribute[-N]
    ↓
VariableAccessor.__getitem__() 或 AttributeProxy.__getitem__()
    ↓
VariableStore.get_with_lag(name, steps, default)
    ↓
VariableState.get_with_lag(steps, default)
    ↓
RingBuffer.get_by_lag(steps, default)
    ↓
返回历史值
```

## 5. 表达式语法支持

### 5.1 基本运算

```python
# 四则运算
a + b
a - b
a * b
a / b

# 括号
(a + b) * c

# 一元运算
-a
+b
```

### 5.2 变量访问

```python
# 当前值
variable_name

# 历史值
variable_name[-30]  # 30 步之前的值
```

### 5.3 属性访问

```python
# 当前值
instance.attribute

# 历史值
instance.attribute[-30]  # 30 步之前的值
```

### 5.4 方法调用

```python
# 算法/模型执行
pid1.execute(PV=tank1.level, SV=sin1.out)

# 支持复杂参数表达式
pid1.execute(
    PV=tank1.level[-10],
    SV=sin1.out + 5
)
```

### 5.5 函数调用

```python
# 无状态函数（从 InstanceRegistry 获取）
abs(x)
sqrt(x)
sin(x)
cos(x)
log(x)
exp(x)
```

### 5.6 赋值表达式

```python
# Variable 类型专用
variable_name = expression

# 示例
non_sense_3 = non_sense_1[-30] + 2 * non_sense_2
```

### 5.7 复杂表达式示例

```python
# 混合运算
result = (a + b) * c - d / e

# 历史数据计算
diff = current_value - current_value[-1]

# 属性与变量混合
output = pid1.mv + tank1.level * 0.5

# 函数调用
normalized = abs(value) / sqrt(value * value + 1)
```

## 6. 安全性设计

### 6.1 AST 验证

- 只允许特定的 AST 节点类型
- 禁止导入、循环、条件语句等危险操作
- 防止代码注入攻击

### 6.2 执行环境隔离

- 使用 `{"__builtins__": {}}` 禁用内置函数
- 只提供明确允许的函数和对象
- 防止访问系统资源

### 6.3 错误处理

- 所有异常都包装为 `ExpressionError`
- 提供详细的错误信息（表达式字符串、错误类型）
- 便于调试和问题定位

## 7. 性能优化

### 7.1 表达式编译

- 使用 `compile()` 将 AST 编译为 code object
- 避免重复解析和验证
- 提高执行效率

### 7.2 代理对象缓存

- `InstanceProxy`、`AttributeProxy`、`VariableAccessor` 在每次求值时创建
- 可以考虑缓存优化（当前未实现）

### 7.3 历史数据访问

- 使用 `RingBuffer`（基于 `deque`）实现高效的历史数据访问
- O(1) 时间复杂度的追加和访问

## 8. 扩展点

### 8.1 支持更多 AST 节点类型

- 条件表达式：`if_exp`（三元运算符）
- 比较运算：`Compare`（`<`、`>`、`==` 等）
- 逻辑运算：`And`、`Or`（`and`、`or`）

### 8.2 支持更多函数类型

- 通过 `InstanceRegistry.register_function()` 注册新函数
- 支持自定义无状态函数

### 8.3 表达式缓存

- 缓存编译后的 code object
- 避免重复编译相同表达式

### 8.4 错误恢复

- 支持表达式执行失败时的默认值策略
- 支持表达式执行失败时的重试机制

## 9. 使用示例

### 9.1 Variable 类型表达式

```python
from data_next.core.expression import ExpressionNode, ExpressionConfig
from data_next.core.variable import VariableStore

# 创建变量存储
vars_store = VariableStore(max_lag_steps=100)

# 创建表达式配置
config = ExpressionConfig(
    name="result",
    expression="result = a + b * c"
)

# 创建表达式节点
node = ExpressionNode(config, instances={})

# 设置输入变量
vars_store.set("a", 1.0)
vars_store.set("b", 2.0)
vars_store.set("c", 3.0)

# 执行表达式
value = node.step(vars_store)  # 结果：7.0

# 获取结果
result = vars_store.get("result")  # 7.0
```

### 9.2 算法节点表达式

```python
from data_next.core.expression import AlgorithmNode

# 创建算法实例
pid = PID(PB=1.0, TI=30.0, TD=0.15)

# 创建算法节点
node = AlgorithmNode(
    instance=pid,
    expression="pid1.execute(PV=tank1.level, SV=sin1.out)",
    stored_attributes=["mv", "pv", "sv", "error"],
    instance_name="pid1",
    instances={"tank1": tank, "sin1": sin_gen}
)

# 执行算法
node.step(vars_store)

# 获取输出
mv = vars_store.get("pid1.MV")
```

### 9.3 复杂表达式

```python
# 历史数据计算
config = ExpressionConfig(
    name="diff",
    expression="diff = current_value - current_value[-1]"
)

# 属性访问
config = ExpressionConfig(
    name="output",
    expression="output = pid1.MV + tank1.level * 0.5"
)

# 函数调用
config = ExpressionConfig(
    name="normalized",
    expression="normalized = abs(value) / sqrt(value * value + 1)"
)
```

## 10. 设计考虑

### 10.1 为什么使用代理模式？

- **解耦**：表达式执行不需要直接访问实例对象
- **统一接口**：所有访问都通过代理，便于统一处理
- **历史数据支持**：代理可以自动处理历史数据访问

### 10.2 为什么分离 ExpressionNode 和 AlgorithmNode？

- **职责分离**：Variable 类型和算法/模型类型的处理逻辑不同
- **灵活性**：可以独立扩展和优化
- **清晰性**：代码结构更清晰，易于理解

### 10.3 为什么使用 AST 而不是正则表达式？

- **准确性**：AST 可以准确解析 Python 表达式语法
- **安全性**：AST 验证可以防止代码注入
- **可扩展性**：易于扩展支持新的语法特性

### 10.4 为什么使用 `eval()` 而不是其他方式？

- **性能**：编译后的 code object 执行效率高
- **灵活性**：支持完整的 Python 表达式语法
- **安全性**：通过 AST 验证和执行环境隔离保证安全

## 11. 已知限制

### 11.1 不支持的操作

- 循环语句（`for`、`while`）
- 条件语句（`if`、`if_exp`）
- 导入语句（`import`）
- Lambda 表达式
- 列表/字典推导式

### 11.2 性能考虑

- 每次求值都创建新的代理对象（可优化）
- 表达式编译结果未缓存（可优化）
- 复杂表达式的 AST 遍历可能较慢

### 11.3 错误处理

- 表达式执行失败时只抛出异常，不提供恢复机制
- 历史数据不足时返回默认值（0.0），可能不够灵活

## 12. 未来改进方向

1. **表达式缓存**：缓存编译后的 code object，提高性能
2. **条件表达式支持**：支持三元运算符和比较运算
3. **错误恢复机制**：支持表达式执行失败时的默认值策略
4. **性能优化**：优化代理对象创建和 AST 遍历
5. **调试支持**：提供表达式执行过程的详细日志
6. **类型检查**：支持表达式类型检查和验证

---

**文档版本**：v1.0  
**最后更新**：2025-12-02  
**维护者**：data_next 开发团队

