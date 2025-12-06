# Expression 解析和执行流程示例

基于 `config/display_demo.yaml` 配置文件的完整流程解析。

## ⚠️ 重要说明

配置文件中 `non_sense_3` 的表达式为：
```yaml
expression: non_sense_3 = non_sense_1[-30] + 2 * sqrt(non_sense_2)
```

**注意**：根据当前代码实现，这种写法可能存在问题：
- `non_sense_1` 和 `non_sense_2` 是 RANDOM 实例，它们的输出属性是 `out`
- 正确的写法应该是：`non_sense_1.out[-30]` 和 `sqrt(non_sense_2.out)`
- 或者系统有特殊处理，将实例名映射为变量名（需要确认）

**本文档将按照两种理解方式展示流程**：
1. 假设系统支持 `non_sense_1[-30]` 这种简化写法（将实例名作为变量名）
2. 说明正确的写法应该是 `non_sense_1.out[-30]`

## 配置文件内容

```yaml
program:
  - name: sin1
    type: SIN
    init_args:
      amplitude: 100.0
      period: 1200
      phase: 0.0
    expression: sin1.execute()
  - name: valve1
    type: VALVE
    init_args:
      min_opening: 0.0
      max_opening: 100.0
      step: 0.1
      full_travel_time: 10.0
    expression: valve1.execute(target_opening=sin1.out)
  - name: non_sense_1
    type: RANDOM
    init_args:
      L: 0.0
      H: 100.0
      max_step: 3.0
    expression: non_sense_1.execute()
  - name: non_sense_2
    type: RANDOM
    init_args:
      L: 0.0
      H: 100.0
      max_step: 3.0
    expression: non_sense_2.execute()
  - name: non_sense_3
    type: Variable
    expression: non_sense_3 = non_sense_1[-30] + 2 * sqrt(non_sense_2)
```

---

## 阶段一：DSL 解析阶段

### 1.1 YAML 文件解析

**执行位置**：`DSLParser.parse_file()`

**过程**：
1. 读取 YAML 文件，解析为字典结构
2. 解析 `clock` 配置（默认值：cycle_time=0.5, mode=GENERATOR）
3. 解析 `record_length`（默认值：1000）
4. 解析 `program` 列表，创建 `ProgramItem` 对象

**解析结果**：
```python
ProgramConfig(
    clock=ClockConfig(cycle_time=0.5, mode=GENERATOR, ...),
    program=[
        ProgramItem(name="sin1", type="SIN", expression="sin1.execute()", init_args={...}),
        ProgramItem(name="valve1", type="VALVE", expression="valve1.execute(target_opening=sin1.out)", init_args={...}),
        ProgramItem(name="non_sense_1", type="RANDOM", expression="non_sense_1.execute()", init_args={...}),
        ProgramItem(name="non_sense_2", type="RANDOM", expression="non_sense_2.execute()", init_args={...}),
        ProgramItem(name="non_sense_3", type="Variable", expression="non_sense_3 = non_sense_1[-30] + 2 * sqrt(non_sense_2)", init_args={}),
    ],
    record_length=1000,
    lag_requirements={"non_sense_1": 30}  # 分析表达式中的 [-30] 语法
)
```

### 1.2 Lag 需求分析

**执行位置**：`DSLParser._analyze_lag_requirements()`

**过程**：
1. 遍历所有 `ProgramItem` 的表达式
2. 使用 AST 解析表达式，查找 `Subscript` 节点（`[-N]` 语法）
3. 对于 `non_sense_3` 的表达式：`non_sense_1[-30] + 2 * sqrt(non_sense_2)`
   - 发现 `non_sense_1[-30]`，提取变量名 `"non_sense_1"` 和滞后步数 `30`
   - 记录到 `lag_requirements`：`{"non_sense_1": 30}`

**结果**：
- `non_sense_1` 需要支持至少 30 步的历史数据
- `VariableStore` 的 `max_lag_steps` 需要 >= 30（实际使用 `record_length=1000`）

---

## 阶段二：节点创建阶段

### 2.1 实例创建（Program 类型）

**执行位置**：`InstanceFactory.create_instance()`

**过程**：
1. **sin1**：
   - 从 `InstanceRegistry` 获取 `SIN` 类
   - 创建实例：`SIN(cycle_time=0.5, amplitude=100.0, period=1200, phase=0.0)`
   - 存储到 `_instances["sin1"]`

2. **valve1**：
   - 从 `InstanceRegistry` 获取 `VALVE` 类
   - 创建实例：`VALVE(cycle_time=0.5, min_opening=0.0, max_opening=100.0, step=0.1, full_travel_time=10.0)`
   - 存储到 `_instances["valve1"]`

3. **non_sense_1**：
   - 从 `InstanceRegistry` 获取 `RANDOM` 类
   - 创建实例：`RANDOM(cycle_time=0.5, L=0.0, H=100.0, max_step=3.0)`
   - 存储到 `_instances["non_sense_1"]`

4. **non_sense_2**：
   - 从 `InstanceRegistry` 获取 `RANDOM` 类
   - 创建实例：`RANDOM(cycle_time=0.5, L=0.0, H=100.0, max_step=3.0)`
   - 存储到 `_instances["non_sense_2"]`

### 2.2 节点创建

**执行位置**：引擎初始化阶段

**过程**：
1. **sin1, valve1, non_sense_1, non_sense_2**（Program 类型）：
   - 创建 `AlgorithmNode` 对象
   - 每个节点持有：实例对象、表达式字符串、存储属性列表、实例名称

2. **non_sense_3**（Variable 类型）：
   - 创建 `ExpressionNode` 对象
   - 节点持有：
     ```python
     ExpressionConfig(
         name="non_sense_3",
         expression="non_sense_3 = non_sense_1[-30] + 2 * sqrt(non_sense_2)"
     )
     ```
   - 传入 `instances` 字典（包含 sin1, valve1, non_sense_1, non_sense_2）

---

## 阶段三：表达式解析阶段（以 non_sense_3 为例）

### 3.1 表达式字符串

```
non_sense_3 = non_sense_1[-30] + 2 * sqrt(non_sense_2)
```

### 3.2 ExpressionNode.step() 执行流程

**执行位置**：`ExpressionNode.step(vars_store)`

#### 步骤 1：创建 ExpressionEvaluator

```python
evaluator = ExpressionEvaluator(vars_store, self._instances)
# self._instances = {
#     "sin1": SIN实例,
#     "valve1": VALVE实例,
#     "non_sense_1": RANDOM实例,
#     "non_sense_2": RANDOM实例
# }
```

#### 步骤 2：检测赋值表达式

```python
tree = ast.parse("non_sense_3 = non_sense_1[-30] + 2 * sqrt(non_sense_2)", mode="eval")
# tree.body 是 ast.Assign 节点
# 提取右侧表达式：ast.unparse(tree.body.value)
# 得到：non_sense_1[-30] + 2 * sqrt(non_sense_2)
```

#### 步骤 3：调用 ExpressionEvaluator.evaluate()

**执行位置**：`ExpressionEvaluator.evaluate("non_sense_1[-30] + 2 * sqrt(non_sense_2)")`

##### 3.3.1 AST 解析

```python
tree = ast.parse("non_sense_1[-30] + 2 * sqrt(non_sense_2)", mode="eval")
```

**AST 结构**：
```
Expression(
    body=BinOp(
        left=Subscript(
            value=Name(id='non_sense_1'),
            slice=UnaryOp(op=USub(), operand=Constant(value=30))
        ),
        op=Add(),
        right=BinOp(
            left=Constant(value=2),
            op=Mult(),
            right=Call(
                func=Name(id='sqrt'),
                args=[Name(id='non_sense_2')]
            )
        )
    )
)
```

##### 3.3.2 AST 验证

**执行位置**：`ExpressionEvaluator._validate_ast()`

**验证过程**：
- `Expression` ✓
- `BinOp` ✓
- `Subscript` ✓（历史数据访问）
- `Name` ✓
- `UnaryOp` ✓
- `Constant` ✓
- `Call` ✓（函数调用）
- 所有节点类型都在允许列表中 ✓

##### 3.3.3 提取变量名

**执行位置**：`ExpressionEvaluator._extract_variable_names()`

**过程**：
1. 遍历 AST，查找所有 `ast.Name` 节点
2. 对于 `non_sense_1`：
   - 检查是否在 `instances` 中：`"non_sense_1" in instances` → `True`（是 RANDOM 实例）
   - 跳过（不是变量）
3. 对于 `non_sense_2`：
   - 检查是否在 `instances` 中：`"non_sense_2" in instances` → `True`（是 RANDOM 实例）
   - 跳过（不是变量）
4. 对于 `sqrt`：
   - 检查是否是函数：`InstanceRegistry.get_function("sqrt")` → 返回函数对象
   - 跳过（是函数）

**结果**：`variable_names = set()`（空集合，因为表达式中的名称都是实例或函数）

##### 3.3.4 构建执行环境

**执行位置**：`ExpressionEvaluator._build_env()`

**过程**：
1. **添加实例代理**：
   ```python
   env["sin1"] = InstanceProxy("sin1", sin1_instance, vars_store)
   env["valve1"] = InstanceProxy("valve1", valve1_instance, vars_store)
   env["non_sense_1"] = InstanceProxy("non_sense_1", non_sense_1_instance, vars_store)
   env["non_sense_2"] = InstanceProxy("non_sense_2", non_sense_2_instance, vars_store)
   ```

2. **添加无状态函数**：
   ```python
   env["sqrt"] = sqrt_func  # 从 InstanceRegistry 获取
   env["abs"] = abs_func
   # ... 其他函数
   ```

3. **添加变量访问器**：
   ```python
   # variable_names 是空集合，所以不添加变量访问器
   ```

**最终环境**：
```python
env = {
    "sin1": InstanceProxy(...),
    "valve1": InstanceProxy(...),
    "non_sense_1": InstanceProxy(...),
    "non_sense_2": InstanceProxy(...),
    "sqrt": sqrt_func,
    "abs": abs_func,
    # ... 其他函数
}
```

##### 3.3.5 编译和执行

**执行位置**：`ExpressionEvaluator.evaluate()` 的最后部分

```python
compiled = compile(tree, filename="<expression>", mode="eval")
value = eval(compiled, {"__builtins__": {}}, env)
```

**执行过程**（从内到外）：
1. **`non_sense_1[-30]`**：
   - `env["non_sense_1"]` → `InstanceProxy("non_sense_1", ...)`
   - 但是表达式是 `non_sense_1[-30]`，需要访问属性或变量
   - **问题**：`non_sense_1` 是实例，但表达式 `non_sense_1[-30]` 试图直接对实例使用下标
   - **实际情况**：在表达式中，`non_sense_1` 应该是一个变量，而不是实例

**修正理解**：
- 在 `non_sense_1[-30]` 中，`non_sense_1` 应该被识别为变量（因为它在表达式中被用作变量访问）
- 但实际上 `non_sense_1` 是一个 RANDOM 实例，它的输出属性（如 `out`）存储在 `VariableStore` 中

**正确的理解**：
- `non_sense_1` 是 RANDOM 实例，它的输出属性名应该是 `out`（根据 RANDOM 类的 `stored_attributes`）
- 但在表达式中直接写 `non_sense_1[-30]` 时，系统应该将其识别为变量名
- 实际上，`non_sense_1` 的输出值存储在 `VariableStore` 中，键名为 `"non_sense_1.out"`

**重新分析表达式**：
表达式 `non_sense_1[-30]` 中的 `non_sense_1` 应该被识别为变量名（不是实例名），因为：
1. 它在 `instances` 中，但在表达式中被用作变量访问（带下标）
2. 系统需要检查：如果名称在 `instances` 中，但在表达式中不是属性访问（`instance.attr`），则应该作为变量处理

**实际执行流程**：

**重要说明**：根据当前代码实现，`non_sense_1[-30]` 这种写法实际上**无法正常工作**，因为：
- `non_sense_1` 在 `instances` 中，会创建 `InstanceProxy`
- `InstanceProxy` 不支持直接使用下标 `[-30]`
- 正确的写法应该是：`non_sense_1.out[-30]`（访问实例的输出属性）

**但为了演示流程，我们假设系统有特殊处理**，或者配置应该改为：
```yaml
expression: non_sense_3 = non_sense_1.out[-30] + 2 * sqrt(non_sense_2.out)
```

**实际执行流程**（假设配置已修正）：

1. **`non_sense_1.out[-30]`**：
   - `non_sense_1` → `env["non_sense_1"]` → `InstanceProxy("non_sense_1", ...)`
   - `.out` → `InstanceProxy.__getattr__("out")` → `AttributeProxy("non_sense_1", "out", ...)`
   - `[-30]` → `AttributeProxy.__getitem__(-30)`
   - 内部调用 `vars_store.get_with_lag("non_sense_1.out", 30, 0.0)`
   - 返回 30 步之前的历史值

2. **`sqrt(non_sense_2.out)`**：
   - `sqrt` → `env["sqrt"]` → `sqrt_func`
   - `non_sense_2` → `InstanceProxy("non_sense_2", ...)`
   - `.out` → `AttributeProxy("non_sense_2", "out", ...)`
   - `float(AttributeProxy)` → `vars_store.get("non_sense_2.out", 0.0)` → 当前值
   - 调用 `sqrt_func(current_value)`
   - 返回平方根

3. **`2 * sqrt(non_sense_2.out)`**：
   - 乘法运算：`2 * sqrt_result`

4. **`non_sense_1.out[-30] + 2 * sqrt(non_sense_2.out)`**：
   - 加法运算：`lag_value + multiplied_value`

**最终结果**：计算得到的浮点数值

**注意**：如果配置文件中确实写的是 `non_sense_1[-30]`（不带 `.out`），那么：
- 系统会尝试将 `non_sense_1` 作为变量名处理
- 但 `non_sense_1` 在 `instances` 中，所以不会创建 `VariableAccessor`
- 会创建 `InstanceProxy`，但 `InstanceProxy` 不支持下标访问
- **执行会失败**，除非系统有特殊处理逻辑

#### 步骤 4：写入 VariableStore

```python
vars_store.set("non_sense_3", value)
# 内部会：
# 1. 确保变量存在：vars_store.ensure("non_sense_3")
# 2. 更新当前值并写入历史：var_state.update(value)
```

---

## 阶段四：执行阶段（一个周期）

### 4.1 执行顺序

假设执行顺序为：sin1 → valve1 → non_sense_1 → non_sense_2 → non_sense_3

### 4.2 各节点执行

#### 4.2.1 sin1.execute()

**节点类型**：`AlgorithmNode`

**执行过程**：
1. 解析表达式 `sin1.execute()`（无参数）
2. 调用 `sin1_instance.execute()`
3. 更新 `sin1_instance.out` 属性
4. 存储到 `VariableStore`：`vars_store.set("sin1.out", value)`

#### 4.2.2 valve1.execute(target_opening=sin1.out)

**节点类型**：`AlgorithmNode`

**执行过程**：
1. 解析表达式 `valve1.execute(target_opening=sin1.out)`
   - 提取参数：`{"target_opening": "sin1.out"}`
2. 解析参数值：
   - `evaluator.evaluate("sin1.out")`
   - `env["sin1"]` → `InstanceProxy`
   - `InstanceProxy.__getattr__("out")` → `AttributeProxy("sin1", "out", ...)`
   - `float(AttributeProxy)` → `vars_store.get("sin1.out")` → 当前值
3. 调用 `valve1_instance.execute(target_opening=current_value)`
4. 更新 `valve1_instance.current_opening` 属性
5. 存储到 `VariableStore`：`vars_store.set("valve1.current_opening", value)`

#### 4.2.3 non_sense_1.execute()

**节点类型**：`AlgorithmNode`

**执行过程**：
1. 解析表达式 `non_sense_1.execute()`（无参数）
2. 调用 `non_sense_1_instance.execute()`
3. 更新 `non_sense_1_instance.out` 属性
4. 存储到 `VariableStore`：`vars_store.set("non_sense_1.out", value)`
   - **注意**：但实际存储键名可能是 `"non_sense_1"` 或 `"non_sense_1.out"`，取决于实现

#### 4.2.4 non_sense_2.execute()

**节点类型**：`AlgorithmNode`

**执行过程**：同 `non_sense_1.execute()`
- 存储到 `VariableStore`：`vars_store.set("non_sense_2.out", value)`

#### 4.2.5 non_sense_3 = non_sense_1[-30] + 2 * sqrt(non_sense_2)

**节点类型**：`ExpressionNode`

**执行过程**：见阶段三的详细解析

**关键点**：
1. `non_sense_1[-30]` 访问 30 步之前的历史值
2. `sqrt(non_sense_2)` 计算当前值的平方根
3. 计算结果写入 `VariableStore`：`vars_store.set("non_sense_3", value)`

---

## 阶段五：数据存储结构

### 5.1 VariableStore 中的键名

执行完一个周期后，`VariableStore` 中存储的数据：

```python
{
    "sin1.out": 当前值,  # 历史缓冲区：[..., 历史值]
    "valve1.current_opening": 当前值,
    "non_sense_1.out": 当前值,  # 或 "non_sense_1"
    "non_sense_2.out": 当前值,  # 或 "non_sense_2"
    "non_sense_3": 当前值,
}
```

### 5.2 历史数据访问

- `non_sense_1[-30]` → `vars_store.get_with_lag("non_sense_1", 30, 0.0)`
- 如果历史数据不足 30 步，返回默认值 `0.0`

---

## 总结

### 关键流程

1. **DSL 解析**：YAML → `ProgramConfig` → `ProgramItem` 列表
2. **Lag 分析**：识别需要历史数据的变量（`non_sense_1` 需要 30 步）
3. **实例创建**：根据类型创建 Program 实例
4. **节点创建**：Program 类型 → `AlgorithmNode`，Variable 类型 → `ExpressionNode`
5. **表达式解析**：AST 解析 → 验证 → 提取变量名 → 构建环境
6. **表达式执行**：编译 → eval → 返回结果
7. **数据存储**：结果写入 `VariableStore`，自动维护历史缓冲区

### 关键设计点

1. **变量名识别**：区分实例名和变量名
2. **历史数据访问**：通过 `VariableAccessor.__getitem__()` 和 `AttributeProxy.__getitem__()` 实现
3. **函数调用**：从 `InstanceRegistry` 获取函数，放入执行环境
4. **赋值表达式**：支持 `variable = expression` 格式

---

**文档版本**：v1.0  
**最后更新**：2025-12-02

