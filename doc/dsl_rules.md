# DSL 组态规则总结

## 一、顶层结构

```yaml
program:
  - name: <实例名称>
    type: <类型>
    init_args: <初始化参数（可选）>
    expression: <表达式>
```

## 二、核心规则

### 2.1 实例类型分类

#### A. 算法/模型类型（有状态实例）
- **类型**：`PID`, `SINE_WAVE`, `SQUARE_WAVE`, `TRIANGLE_WAVE`, `LIST_WAVE`, `CYLINDRICAL_TANK`, `VALVE`, `RANDOM` 等
- **特点**：
  - 必须有 `init_args`（初始化参数）
  - `expression` 格式：`<instance_name>.execute(...)`
  - 每个周期调用 `execute()` 更新内部状态
  - 可以输出多个属性（如 `pid1.MV`, `tank1.level`）

#### B. 变量类型（无状态计算）
- **类型**：`Variable`
- **特点**：
  - 无 `init_args`
  - `expression` 格式：`<variable_name> = <expression>`
  - 纯表达式计算，支持 lag 语法（如 `v1[-30]`）

### 2.2 表达式语法

#### A. 方法调用表达式（算法/模型实例）
```yaml
expression: pid1.execute(PV=tank1.level, SV=sin1.out)
expression: tank1.execute(valve_opening=valve1.current_opening)
expression: sin1.execute()
```

**特点**：
- 支持关键字参数（`pv=...`, `sv=...`）
- 参数可以是其他实例的属性（`tank1.level`, `sin1.out`）
- 参数可以是常量
- 无参数时可以省略括号内容：`sin1.execute()` 或 `sin1.execute`

#### B. 赋值表达式（Variable 类型）
```yaml
expression: non_sense_3 = non_sense_1[-30] + 2 * non_sense_2
expression: non_sense_4 = sin(non_sense_3, 3600, 0)
```

**特点**：
- 支持 lag 语法：`variable_name[-lag_steps]`
- 支持数学函数：`sin()`, `cos()`, `sqrt()` 等
- 支持四则运算、括号等
- 左侧变量名必须与 `name` 字段一致

#### C. 属性访问
- 在表达式中可以访问其他实例的属性：
  - `tank1.level`
  - `pid1.MV`
  - `valve1.current_opening`
  - `sin1.out`

### 2.3 依赖关系与执行顺序

- **自动推导**：通过解析表达式中的变量引用，自动构建依赖图
- **拓扑排序**：根据依赖关系确定执行顺序
- **循环依赖检测**：如果存在循环依赖，应报错或提供手动指定顺序的机制

### 2.4 实例初始化

- `init_args` 中的参数会传递给实例的构造函数
- 不同实例类型有不同的参数集合（如 PID 有 `pb`, `ti`, `td`，Tank 有 `height`, `radius`）

## 三、设计优势

1. **统一组态方式**：所有实例（算法/模型/变量）都用同一套 `program` 列表描述
2. **表达式驱动**：依赖关系和执行顺序由表达式自动推导，无需手动配置 `connections` 和 `execution_order`
3. **向后兼容**：Variable 类型保持 data_factory 的表达式风格
4. **向前扩展**：算法/模型实例通过 `execute()` 方法调用，符合 mock_server 的执行模型

## 四、潜在欠缺与待明确问题

### 4.1 实例属性访问的语义

**问题**：`pid1.execute(...)` 返回什么？如何访问返回值？

**当前示例中的用法**：
- `pid1.execute(PV=tank1.level, SV=sin1.out)` - 调用 execute
- `valve1.execute(target_opening=pid1.MV)` - 访问 `pid1.MV` 属性

**待明确**：
1. `execute()` 是否返回一个对象/字典，包含所有输出属性？
2. 还是 `execute()` 只是更新内部状态，属性通过 `instance.attribute` 访问？
3. 如果 `pid1.execute()` 返回 `{MV: 50.0, ...}`，那么 `pid1.MV` 是访问返回值还是访问实例属性？

**建议**：
- `execute()` 更新内部状态，不返回值（或返回 None）
- 属性通过 `instance.attribute` 访问，这些属性在 `execute()` 调用后自动更新
- 在表达式解析时，`pid1.MV` 会被解析为"访问 `pid1` 实例的 `MV` 属性"

### 4.2 时间变量 `t` 和控制器周期

**已明确**：
1. **时间 `t` 不传递**：所有算法按照"下个周期应该如何计算"来执行，而不是根据时间生成
2. **控制器周期需要传递**：控制器周期（如 0.5 秒）需要隐性传递给算法实例，用于计算周期数
   - 例如：`sin` 的周期配置为 3600 秒，对于控制器周期 0.5 秒而言，就是 7200 次运算完成一个 sin 周期
3. **Variable 类型中的时间**：Variable 类型的表达式可以使用 `t` 作为时间变量（用于数学表达式）

**实现方式**：
- `execute()` 方法由引擎自动注入控制器周期（`cycle_time`）作为参数或通过上下文传递
- 表达式中的 `t` 仅用于 Variable 类型的数学表达式

### 4.3 存储概念（无输出概念）

**已明确**：
- **没有输出的概念**，只有算法或变量是否需要存储的概念
- **Variable 类型**：默认需要存储
- **算法/模型类型（program）**：其参数在 Class 中定义哪些是需要存储的参数
  - 例如：PID 类定义 `mv`, `pv`, `sv` 需要存储
  - 例如：Tank 类定义 `level` 需要存储

**实现方式**：
- 每个算法/模型类需要定义 `stored_attributes` 列表，指定哪些属性需要存储
- 引擎在每周期执行后，自动存储这些属性的值到 `VariableStore`

### 4.4 实例属性的初始化

**已明确**：
1. **初始化优先级**：DSL 中的 `init_args` > Class 中的 default 值
2. **初始化时机**：第 0 次执行全局的实例化，不需要等待就开始下一个周期（离线模式，在线模式先不支持）
3. **初始值设置**：`init_args` 中的值在实例创建时自动设置到对应属性
4. **第一个周期**：第一个周期 `execute()` 调用前，属性已有初始值

**实现方式**：
- 引擎在初始化时，先创建所有实例，使用 `init_args` 覆盖 Class 的 default 值
- 第 0 次执行：实例化所有对象，设置初始值到 `VariableStore`
- 第 1 次执行：开始第一个周期的计算

### 4.5 表达式中的函数调用

**已明确**：
1. **表达式中的函数类型**：
   - **实例化的算法**：`pid1.execute(...)`, `tank1.execute(...)` - 有状态的算法实例
   - **无状态的函数**：`abs()`, `sqrt()`, `sin()` 等 - 临时调用，没有状态
2. **函数注册**：无状态的函数也会包含在算法库中，可以在表达式中直接调用
3. **示例修正**：
   ```yaml
   # 错误示例（dsl写得不好）：
   - name: non_sense_4
     type: Variable
     expression: non_sense_4 = sin(non_sense_3, 3600, 0)
   
   # 正确示例：
   - name: sin1
     type: SINE_WAVE
     init_args:
       amplitude: 100.0
       period: 3600
       phase: 0.0
     expression: sin1.execute()
   
   - name: non_sense_4
     type: Variable
     expression: non_sense_4 = abs(non_sense_3) + sqrt(non_sense_3)
   ```

**实现方式**：
- 提供函数注册机制，支持注册无状态的数学函数
- 这些函数可以在 Variable 类型的表达式中直接调用
- 函数库包括：`abs`, `sqrt`, `sin`, `cos`, `tan`, `log`, `exp` 等标准数学函数

### 4.6 循环依赖的处理

**问题**：如果存在循环依赖（如 `pid1 -> valve1 -> tank1 -> pid1`），如何确定执行顺序？

**当前示例**：
- `pid1.execute(PV=tank1.level, SV=sin1.out)` 依赖 `tank1.level`
- `tank1.execute(valve_opening=valve1.current_opening)` 依赖 `valve1.current_opening`
- `valve1.execute(target_opening=pid1.MV)` 依赖 `pid1.MV`
- 这是一个循环依赖

**待明确**：
1. 是否允许循环依赖？
2. 如果允许，如何确定第一次执行时的初始值？
3. 是否需要手动指定执行顺序？

**建议**：
- 允许循环依赖（这是控制系统的常见情况）
- 第一次执行时，使用 `init_args` 中的初始值
- 执行顺序可以通过拓扑排序的“强连通分量”处理，或者手动指定
- 对于循环依赖，可以按照“先计算所有输入，再更新所有输出”的方式处理

### 4.7 实例类型的注册与扩展

**问题**：如何注册新的实例类型（如 `CUSTOM_MODEL`）？

**待明确**：
1. 是否需要类型注册机制？
2. 如何将 YAML 中的 `type: PID` 映射到实际的 Python 类？

**建议**：
- 需要类型注册机制（如 `InstanceRegistry`）
- 支持插件式扩展，允许用户注册自定义类型

### 4.8 配置验证

**问题**：如何验证配置的正确性？

**待明确**：
1. 表达式语法错误如何检测？
2. 类型不匹配如何检测？
3. 缺少必需的 `init_args` 如何检测？

**建议**：
- 在加载配置时进行静态验证
- 提供清晰的错误信息，指出问题所在的行和字段

## 五、已明确的实现规则

1. **属性访问语义**：`instance.attribute` 访问的是实例属性，在 `execute()` 调用后更新
2. **控制器周期注入**：`execute()` 方法自动接收控制器周期（`cycle_time`），无需在表达式中传递
3. **循环依赖处理**：支持循环依赖，使用初始值进行第一次计算
4. **存储机制**：Variable 默认存储，算法/模型的存储属性由 Class 定义
5. **初始化优先级**：DSL `init_args` > Class default 值
6. **第 0 次执行**：全局实例化，不等待直接开始第 1 周期（离线模式）
7. **函数调用**：支持实例化算法（有状态）和无状态函数（如 `abs`, `sqrt`）
8. **类型注册机制**：提供类型注册和扩展机制
9. **配置验证**：在加载时进行完整的静态验证

## 六、实现架构设计要点

### 6.1 实例类型系统
- **算法/模型基类**：定义 `execute()` 接口和 `stored_attributes` 属性
- **类型注册表**：将 YAML 中的 `type: PID` 映射到实际的 Python 类
- **实例工厂**：根据类型和 `init_args` 创建实例

### 6.2 表达式解析系统
- **AST 解析**：解析表达式，识别方法调用、属性访问、函数调用
- **依赖分析**：从表达式中提取变量依赖，构建依赖图
- **拓扑排序**：确定执行顺序，处理循环依赖

### 6.3 执行引擎
- **第 0 周期**：实例化所有对象，设置初始值
- **第 1+ 周期**：按拓扑顺序执行所有节点
- **存储机制**：自动存储 Variable 和算法/模型的 `stored_attributes`
- **周期注入**：自动将控制器周期传递给 `execute()` 方法

### 6.4 历史数据存储机制
- **统一存储**：所有 Variable 和算法/模型属性的历史数据统一存储在 `VariableStore` 中
- **存储长度**：通过 `record_length` 配置项指定历史记录长度（默认 1000）
- **存储键名**：
  - Variable：直接使用变量名（如 `non_sense_3`）
  - 算法/模型属性：使用 `instance_name.attribute_name`（如 `pid1.MV`、`tank1.level`）
- **访问语法**：
  - 当前值：`variable_name` 或 `instance.attribute`
  - 历史值：`variable_name[-30]` 或 `instance.attribute[-30]`
- **自动管理**：每次 `set()` 调用时，值会自动追加到历史缓冲区，无需手动管理

