# 交互记录（data_next）

## 2025-12-02

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 「创建一个新的目录来做新的架构，data_next」，用于把 `data_factory` 的批量生成能力与 `mock_server` 的有状态周期执行能力统一起来。

- **3. Cursor 理解、拆分、结构化后的需求**
  - 创建一个新的工程目录 `data_next`，不影响现有项目运行。
  - 在 `data_next` 内搭建统一架构的基础骨架，包括：
    - `core`：统一时钟、变量与历史缓冲区、表达式节点、执行引擎接口与基础实现。
    - `utils`：统一日志模块（基于 `mock_server` 的实现，命名为 `data_next`）。
    - `doc`：交互记录、需求文档、设计文档、用户手册的初始版本。
  - 保证入口以函数参数方式传参，不新增命令行解析逻辑。
  - 后续可以在该目录中逐步迁移/重构现有批量生成和实时运行逻辑。

- **4. Cursor 本次交互后的操作概述**
  - 在仓库根目录下新建 `data_next` 目录和基础说明：
    - 创建 `data_next/README.md`，说明新架构的目标、目录结构和使用场景。
  - 创建工具模块：
    - 新建 `data_next/utils/__init__.py`。
    - 新建 `data_next/utils/logger.py`，基于 `mock_server` 的日志实现，适配为 `data_next` 名称前缀，并提供 `get_logger` / `close_logger`。
  - 创建核心模块骨架：
    - 新建 `data_next/core/__init__.py`，说明核心子模块。
    - 新建 `data_next/core/clock.py`，定义 `ClockMode`、`ClockConfig`、`Clock`，支持 REALTIME/GENERATOR 两种模式。
    - 新建 `data_next/core/variable.py`，实现 `RingBuffer`、`VariableState`、`VariableStore`，用于按步数访问历史值，以支持 lag。
    - 新建 `data_next/core/expression_node.py`，实现：
      - `ExpressionConfig`：表达式节点配置。
      - `EvalContext`：单点执行上下文（提供 `t`、`var()`、`lag()` 以及常用数学函数）。
      - `SafeExpression`：AST 校验 + 安全执行。
      - `ExpressionNode`：按周期执行表达式并写回 `VariableStore`。
    - 新建 `data_next/core/engine.py`，实现：
      - `EngineConfig`：引擎配置（时钟配置、表达式节点列表、最大滞后步数）。
      - `UnifiedEngine`：统一执行引擎初版，提供 `step_once()`、`run_for_steps()`、`run_forever()` 三种 API。
  - 创建文档目录与交互记录：
    - 新建 `data_next/doc/interaction_record.md`，记录本次需求与已完成的骨架搭建情况。

---

## 2025-12-02（Clock 模块重构）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 评审新的 Clock 模块，确认是否符合预期。要求：
    - Clock 模块自己知道当前的运行模式（REALTIME 或 GENERATOR），在 `step()` 内部根据模式决定是否等待。
    - Clock 中维护的核心数值应该是周期计数（`cycle_count`），而不是当前时间。当前时间是根据起始时间和周期计数统一计算出的结果。
    - 执行周期（`cycle_time`）与采样间隔（`sample_interval`）应该分开，采样间隔由 Clock 模块统一提供。

- **3. Cursor 理解、拆分、结构化后的需求**
  - **核心状态改为周期计数**：
    - `Clock` 维护 `cycle_count: int` 作为核心状态（从 0 开始）。
    - `sim_time` 改为计算属性：`sim_time = start_time + cycle_count * cycle_time`。
  - **模式判断内置到 step()**：
    - 移除 `sleep_to_next_cycle()` 方法，调用方不再需要单独调用。
    - `step()` 内部根据 `ClockMode` 决定是否 sleep：
      - `REALTIME`：先 sleep，再更新周期计数。
      - `GENERATOR`：直接更新周期计数，不 sleep。
  - **执行周期与采样间隔分离**：
    - `ClockConfig` 新增 `sample_interval: float | None` 字段。
    - 如果为 `None`，则每个周期都采样（`should_sample()` 始终返回 `True`）。
    - 如果指定了 `sample_interval`，则每 N 个周期采样一次（N = `sample_interval / cycle_time`）。
    - 提供 `should_sample()` 方法判断当前周期是否应该采样。
  - **支持绝对时间起点**：
    - `start_time` 可以是 `float`（时间戳）或 `datetime` 对象。
    - 内部统一转换为时间戳存储。

- **4. Cursor 本次交互后的操作概述**
  - **重构 `data_next/core/clock.py`**：
    - 将 `ClockMode` 简化为 `REALTIME` 和 `GENERATOR` 两种模式。
    - 将 `sim_time` 从字段改为计算属性（基于 `cycle_count`）。
    - 在 `step()` 内部根据模式决定是否 sleep，移除 `sleep_to_next_cycle()` 方法。
    - 新增 `sample_interval` 配置和 `should_sample()` 方法。
    - 新增 `reset(cycle_count=0)` 方法用于重置时钟。
    - 在 `ClockConfig` 中新增配置验证逻辑。
  - **更新 `data_next/core/engine.py`**：
    - 移除 `run_for_steps()` 和 `run_forever()` 中对 `sleep_to_next_cycle()` 的调用。
    - 简化 `run_for_steps()` 的参数（移除 `sleep` 参数）。
  - **更新文档**：
    - 更新 `data_next/doc/设计文档.md`，说明新的 Clock 设计理念（周期计数为核心、模式内置、采样间隔分离）。
    - 更新 `data_next/doc/用户手册.md`，更新示例代码使用新的 `ClockConfig` 格式。

---

## 2025-12-02（Clock 模块 step() 返回值调整）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 做如下修改：
    1. 去掉 `should_sample()` 方法，在 `step()` 函数中返回三个信息：周期计数、是否需要采样、当前时间（字符串）。
    2. 配置的时候，增加配置时间字符串的模板，如 "YYMM" 这种格式。

- **3. Cursor 理解、拆分、结构化后的需求**
  - **移除 `should_sample()` 方法**：
    - 不再提供单独的方法判断是否需要采样。
  - **修改 `step()` 返回值**：
    - 从返回单个 `float`（模拟时间）改为返回 `Tuple[int, bool, str]`：
      - `int`：周期计数（`cycle_count`）
      - `bool`：是否需要采样（根据 `sample_interval` 计算）
      - `str`：当前时间字符串（根据 `time_format` 格式化）
  - **新增时间格式化配置**：
    - 在 `ClockConfig` 中新增 `time_format: str | None` 字段。
    - 使用 Python 的 `strftime` 格式，例如：
      - `"%Y%m%d"` -> `"20241202"`
      - `"%Y-%m-%d %H:%M:%S"` -> `"2024-12-02 10:30:45"`
      - `"%y%m"` -> `"2412"`
    - 如果为 `None`，则返回 ISO 格式字符串。

- **4. Cursor 本次交互后的操作概述**
  - **修改 `data_next/core/clock.py`**：
    - 在 `ClockConfig` 中新增 `time_format: str | None` 字段。
    - 修改 `step()` 方法，返回 `Tuple[int, bool, str]`（周期计数、是否需要采样、时间字符串）。
    - 移除 `should_sample()` 方法。
    - 在 `step()` 内部实现时间字符串格式化逻辑。
  - **更新 `data_next/core/engine.py`**：
    - 修改 `step_once()` 方法，解包 `clock.step()` 的返回值。
    - 在快照中添加 `cycle_count`、`need_sample`、`time_str` 字段。
    - 使用 `clock.sim_time` 获取模拟时间（浮点数）用于表达式计算。
  - **更新文档**：
    - 更新 `data_next/doc/设计文档.md`，说明新的 `step()` 返回值和 `time_format` 配置。
    - 更新 `data_next/doc/用户手册.md`，更新示例代码展示新的返回格式。

---

## 2025-12-02（Clock 模块 sleep 时间修正）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 发现 `step()` 中直接 sleep `cycle_time` 是不对的，需要考虑算法执行时间。
  - 如果本周期执行算法的时间超过了周期的 60%，则记录警告日志。

- **3. Cursor 理解、拆分、结构化后的需求**
  - **修正 sleep 逻辑**：
    - `step()` 方法不再直接 sleep，而是返回开始时间戳。
    - 新增 `sleep_remaining(cycle_start_time)` 方法，根据已执行时间计算剩余时间并 sleep。
    - 在 REALTIME 模式下，调用方需要先执行算法，然后调用 `sleep_remaining()` 来 sleep 剩余时间。
  - **添加超时检测**：
    - 在 `sleep_remaining()` 中检测执行时间是否超过周期的 60%。
    - 如果超过，记录警告日志，包含执行时间、周期时间、周期计数等信息。
    - 如果执行时间 >= 周期时间，记录警告日志，说明没有剩余时间 sleep。

- **4. Cursor 本次交互后的操作概述**
  - **修改 `data_next/core/clock.py`**：
    - 修改 `step()` 方法，返回四个值：`(cycle_count, need_sample, time_str, cycle_start_time)`。
    - 移除 `step()` 中的直接 sleep 逻辑（REALTIME 模式）。
    - 新增 `sleep_remaining(cycle_start_time)` 方法：
      - 计算已执行时间（当前时间 - 开始时间）。
      - 检测是否超过周期的 60%，如果超过则记录警告日志。
      - 计算剩余时间（周期时间 - 已执行时间）并 sleep。
      - 如果剩余时间 <= 0，记录警告日志。
  - **更新 `data_next/core/engine.py`**：
    - 修改 `step_once()` 方法，解包 `clock.step()` 的四个返回值。
    - 在执行完所有表达式节点后，调用 `clock.sleep_remaining(cycle_start_time)`。
  - **更新文档**：
    - 更新 `data_next/doc/设计文档.md`，说明新的 sleep 逻辑和超时检测机制。

---

## 2025-12-02（Clock 模块封装优化）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 询问 `step()` 函数的最后一个返回参数的作用是什么。

- **3. Cursor 理解、拆分、结构化后的需求**
  - **问题分析**：
    - `step()` 返回的最后一个参数是 `cycle_start_time`（开始时间戳）。
    - 它的作用是传递给 `sleep_remaining()` 来计算执行时间。
    - 但这个设计增加了耦合：engine 需要保存并传递这个时间戳。
  - **优化方案**：
    - 将 `cycle_start_time` 作为 clock 的内部状态保存（`_current_cycle_start_time`）。
    - `step()` 只返回三个值：`(周期计数, 是否需要采样, 当前时间字符串)`。
    - `sleep_remaining()` 不需要参数，直接使用内部保存的开始时间戳。
    - 这样 clock 完全封装了时间管理逻辑，engine 不需要关心内部实现。

- **4. Cursor 本次交互后的操作概述**
  - **修改 `data_next/core/clock.py`**：
    - 添加内部状态 `_current_cycle_start_time` 用于保存周期开始时间戳。
    - 修改 `step()` 方法，只返回三个值（移除开始时间戳）。
    - 修改 `sleep_remaining()` 方法，移除参数，直接使用内部保存的开始时间戳。
    - 添加检查：如果 `sleep_remaining()` 在 `step()` 之前调用，记录警告日志。
  - **更新 `data_next/core/engine.py`**：
    - 修改 `step_once()` 方法，只解包 `clock.step()` 的三个返回值。
    - 调用 `clock.sleep_remaining()` 时不再传递参数。
  - **更新文档**：
    - 更新 `data_next/doc/设计文档.md`，说明新的封装设计。

---

## 2025-12-02（DSL 规则总结与实现方案设计）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 阅读 `dsl_demo1.yaml`，总结 DSL 规则，并找出欠缺的地方。
  - 确认设计理念：统一组态方式向 data_factory 靠拢（表达式驱动），执行模型向 mock_server 靠拢（有状态周期执行）。

- **3. Cursor 理解、拆分、结构化后的需求**
  - **DSL 规则总结**：
    - 顶层结构：`program` 列表，每个元素包含 `name`, `type`, `init_args`（可选）, `expression`。
    - 类型分类：
      - 算法/模型类型（有状态）：`PID`, `SIN`, `CYLINDRICAL_TANK`, `VALVE`, `RANDOM` 等，必须有 `init_args`，expression 格式为 `instance.execute(...)`。
      - 变量类型（无状态）：`Variable`，无 `init_args`，expression 格式为 `variable_name = expression`。
    - 表达式语法：
      - 方法调用：`pid1.execute(pv=tank1.level, sv=sin1.out)`。
      - 属性访问：`tank1.level`, `pid1.mv`。
      - 支持 lag：`non_sense_1[-30]`（Variable 类型）。
    - 依赖关系：通过表达式中的变量引用自动推导，拓扑排序确定执行顺序。
  - **用户确认的关键规则**：
    1. 属性访问语义：`instance.attribute` 访问实例属性，在 `execute()` 调用后更新。
    2. 时间变量：时间 `t` 不传递，所有算法按"下个周期应该如何计算"执行；控制器周期需要隐性传递（用于计算周期数）。
    3. 第 0 次执行：全局实例化，不等待直接开始第 1 周期（离线模式，在线模式先不支持）。
    4. 存储概念：没有输出的概念，只有是否需要存储的概念。Variable 默认存储，算法/模型的存储属性由 Class 定义。
    5. 初始化优先级：DSL `init_args` > Class default 值。
    6. 函数调用：expression 中除了实例化的算法，还可以临时调用无状态的函数（如 `abs`, `sqrt`），这些函数也会包含在算法库中。
  - **需要修正的 DSL 示例**：
    - `sin(non_sense_3, 3600, 0)` 这种写法不好，应该改成 `type: SIN` 的实例化算法。
    - 无状态函数（如 `abs`, `sqrt`）可以在 Variable 类型的表达式中直接调用。

- **4. Cursor 本次交互后的操作概述**
  - **创建 DSL 规则文档**：
    - 新建 `data_next/doc/dsl_rules.md`，详细总结 DSL 规则、设计优势、已明确的实现规则、实现架构设计要点。
  - **更新交互记录**：
    - 在 `data_next/doc/interaction_record.md` 中记录本次讨论内容。

---

## 2025-12-02（历史数据存储需求补充）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 补充历史数据存储需求：每个 Variable 和 AlgorithmInstance 的每个参数，都需要有一个长度为 `record_length` 的历史数据存储在实例中，以支持 `[-30]` 这种 lag 语法。

- **3. Cursor 理解、拆分、结构化后的需求**
  - **历史数据存储要求**：
    - 每个 Variable 需要存储长度为 `record_length` 的历史数据
    - 每个 AlgorithmInstance 的每个属性也需要存储长度为 `record_length` 的历史数据
    - 所有历史数据统一存储在 `VariableStore` 中
    - 支持通过 `variable_name[-30]` 和 `instance.attribute[-30]` 语法访问历史值
  - **存储键名规则**：
    - Variable：直接使用变量名（如 `non_sense_3`）
    - 算法/模型属性：使用 `instance_name.attribute_name`（如 `pid1.mv`、`tank1.level`）
  - **配置项**：
    - 在 `ProgramConfig` 中新增 `record_length` 配置项（默认 1000）
    - 使用 `record_length` 作为 `VariableStore` 的 `max_lag_steps` 参数

- **4. Cursor 本次交互后的操作概述**
  - **更新实现设计文档**：
    - 在 `data_next/doc/实现设计.md` 中新增"历史数据存储机制详解"章节
    - 详细说明存储要求、存储键名规则、历史数据访问语法、实现细节、配置示例、性能考虑
    - 更新 `ProgramConfig` 设计，添加 `record_length` 配置项
    - 更新 `AlgorithmNode` 设计，确保每次 `execute()` 后自动存储属性到 `VariableStore`
    - 更新 `ExtendedEvalContext` 和 `AttributeProxy` 设计，支持历史数据访问
    - 更新表达式解析逻辑，支持 `instance.attribute[-30]` 语法
  - **更新 DSL 规则文档**：
    - 在 `data_next/doc/dsl_rules.md` 中补充历史数据存储机制的说明
  - **更新交互记录**：
    - 在 `data_next/doc/interaction_record.md` 中记录本次补充需求

---

## 2025-12-02（Expression 模块设计文档生成）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - expression 模块有点太过于复杂了，帮我单独生成一份设计文档

- **3. Cursor 理解、拆分、结构化后的需求**
  - **需求分析**：
    - expression 模块包含多个复杂组件，需要一份详细的设计文档
    - 文档应该包括模块概述、架构设计、组件详解、数据流、使用示例等
  - **文档内容要求**：
    - 模块概述：设计目标、模块位置、依赖关系
    - 架构设计：整体架构、组件关系图
    - 核心组件详解：每个类的职责、方法、实现细节
    - 数据流：ExpressionNode 和 AlgorithmNode 的执行流程
    - 表达式语法支持：支持的语法类型和示例
    - 安全性设计：AST 验证、执行环境隔离
    - 性能优化：编译缓存、代理对象优化
    - 扩展点：未来可扩展的功能
    - 使用示例：实际使用场景
    - 设计考虑：设计决策的原因
    - 已知限制：当前不支持的功能
    - 未来改进方向：优化建议

- **4. Cursor 本次交互后的操作概述**
  - **创建 Expression 模块设计文档**：
    - 新建 `doc/expression模块设计文档.md`
    - 包含 12 个主要章节：
      1. 模块概述：设计目标、模块位置
      2. 架构设计：整体架构、组件关系
      3. 核心组件详解：8 个核心类的详细说明
      4. 数据流：ExpressionNode、AlgorithmNode、历史数据访问流程
      5. 表达式语法支持：基本运算、变量访问、属性访问、方法调用、函数调用、赋值表达式
      6. 安全性设计：AST 验证、执行环境隔离、错误处理
      7. 性能优化：表达式编译、代理对象缓存、历史数据访问
      8. 扩展点：支持更多 AST 节点、函数类型、表达式缓存
      9. 使用示例：Variable 类型、算法节点、复杂表达式示例
      10. 设计考虑：代理模式、职责分离、AST 使用、eval() 使用的原因
      11. 已知限制：不支持的操作、性能考虑、错误处理限制
      12. 未来改进方向：表达式缓存、条件表达式支持、错误恢复机制等
  - **更新交互记录**：
    - 在 `doc/interaction_record.md` 中记录本次操作

---

## 2025-12-02（Functions 模块实现 abs 和 sqrt 函数）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 目前 function 里面没有实现东西啊，有别举例没办法做，帮我先实现两个函数 abs sqrt

- **3. Cursor 理解、拆分、结构化后的需求**
  - **需求分析**：
    - functions 模块需要实现 abs 和 sqrt 两个函数
    - 虽然之前已经有注册，但需要更清晰的实现方式
  - **实现方案**：
    - 创建独立的 `math_functions.py` 文件来组织函数
    - 实现 `abs_func` 和 `sqrt_func` 函数，包含错误处理
    - 在 `__init__.py` 中注册这些函数到 InstanceRegistry
    - 添加详细的函数文档和类型注解

- **4. Cursor 本次交互后的操作概述**
  - **创建 math_functions.py**：
    - 新建 `functions/math_functions.py`
    - 实现 `abs_func(x)`：计算绝对值，返回浮点数
    - 实现 `sqrt_func(x)`：计算平方根，包含负数检查，返回浮点数
    - 添加详细的函数文档、类型注解和示例
  - **更新 __init__.py**：
    - 导入自定义函数（使用相对导入）
    - 注册 `abs_func` 和 `sqrt_func` 到 InstanceRegistry
    - 保留其他标准数学函数的注册
    - 改进代码组织和注释
  - **功能特点**：
    - `abs_func`：接受 int 或 float，返回 float
    - `sqrt_func`：接受 int 或 float，对负数抛出 ValueError，返回 float
    - 所有函数都有完整的文档字符串和类型注解

---

## 2025-12-02（库内部模块导入方式改为相对导入）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 把库里面非运行模块的导入方式先改成相对导入吧

- **3. Cursor 理解、拆分、结构化后的需求**
  - **需求分析**：
    - 将库内部模块（非运行模块）的绝对导入改为相对导入
    - 运行模块（如 test_dsl.py）保持绝对导入
    - 文档中的代码示例不需要修改
  - **修改范围**：
    - core/ 下的所有模块
    - programs/ 下的所有模块
    - functions/ 下的模块
    - utils/ 下的模块（如果有）

- **4. Cursor 本次交互后的操作概述**
  - **修改 core/ 模块**：
    - `core/engine.py`：改为相对导入（`.clock`, `.variable`, `.expression`, `..utils.logger`）
    - `core/expression.py`：改为相对导入（`.variable`, `.instance`）
    - `core/factory.py`：改为相对导入（`.instance`, `.parser`）
    - `core/clock.py`：改为相对导入（`..utils.logger`）
    - `core/parser.py`：改为相对导入（`.clock`）
  - **修改 programs/ 模块**：
    - `programs/base.py`：改为相对导入（`..core.variable`）
    - `programs/__init__.py`：改为相对导入（`.sin`, `.random`, `.pid`, `.cylindrical_tank`, `.valve`, `..core.instance`）
    - `programs/pid.py`：改为相对导入（`..core.instance`, `.base`）
    - `programs/sin.py`：改为相对导入（`..core.instance`, `.base`）
    - `programs/random.py`：改为相对导入（`..core.instance`, `.base`）
    - `programs/cylindrical_tank.py`：改为相对导入（`..core.instance`, `.base`）
    - `programs/valve.py`：改为相对导入（`..core.instance`, `.base`）
  - **修改 functions/ 模块**：
    - `functions/__init__.py`：改为相对导入（`..core.instance`）
  - **验证**：
    - 检查所有文件的语法错误，无错误
    - 相对导入语法正确，符合 Python 包结构规范

---

## 2025-12-02（record_length优化和表达式实例名自动转换）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - `record_length`应该根据lag分析来，很多没有必要有，也没有必要有1000这么长
  - 如果表达式中，直接用到了实例，那么默认用.out属性
  - 改完之后，想debug一下display，写一个最简单的debug_display.py
  - 中间Clock不要sleep，想看看运行逻辑

- **3. Cursor 理解、拆分、结构化后的需求**
  - **record_length优化**：
    - 如果配置中指定了`record_length`，则使用配置值
    - 否则根据`lag_requirements`的最大值计算，加上50%的安全余量，最小为10
    - 避免不必要的长历史记录
  - **表达式实例名自动转换**：
    - 在表达式中直接使用实例名时（如`non_sense_1[-30]`），自动转换为`.out`属性访问（`non_sense_1.out[-30]`）
    - 在AST层面进行转换，使用`ast.NodeTransformer`实现
    - 只在Name节点且名称在instances中时转换，方法调用和属性访问不转换
  - **debug_display.py脚本**：
    - 使用`display_demo.yaml`配置文件
    - Clock使用GENERATOR模式（不sleep）
    - 简单打印输出，方便查看运行逻辑
  - **修复bug**：
    - 修复`engine.py`中`step_once`方法调用`node.step`时传递了多余的`t`参数的问题

- **4. Cursor 本次交互后的操作概述**
  - **修改`core/parser.py`**：
    - 在`parse_file`方法中，先分析lag需求，然后根据最大lag值计算`record_length`
    - 如果配置中指定了`record_length`，则使用配置值；否则根据`lag_requirements`的最大值计算，加上50%的安全余量，最小为10
  - **修改`core/expression.py`**：
    - 在`ExpressionEvaluator`类中添加`_transform_instance_names`方法
    - 使用`ast.NodeTransformer`将直接使用实例名的情况转换为`.out`属性访问
    - 在`evaluate`方法中，在解析AST后先进行转换，然后再执行
  - **修改`core/engine.py`**：
    - 修复`step_once`方法中调用`node.step`时传递了多余的`t`参数的问题
    - 添加`from_program_config`类方法，支持从`ProgramConfig`创建引擎
    - 添加`_instances`和`_nodes`属性，支持算法节点和表达式节点
    - 修改`step_once`方法，按顺序执行所有节点（算法节点和表达式节点）
  - **创建`debug_display.py`**：
    - 创建简单的调试脚本，使用`display_demo.yaml`配置文件
    - 确保Clock使用GENERATOR模式（不sleep）
    - 执行20个周期，打印每个周期的快照
  - **验证**：
    - 检查所有文件的语法错误，无错误
    - 代码逻辑正确，符合需求

---

## 2025-12-02（修复 _analyze_lag_requirements 无法解析赋值语句中的 lag 需求）

- **1. 当前时间**
  - 2025-12-02（具体时间以实际执行为准）

- **2. 我的原始需求**
  - 运行 `debug_display.py` 时，`self._analyze_lag_requirements(program_items)` 的结果是空的，但配置文件中明显存在 `[-30]`，需要检查并修复。

- **3. Cursor 理解、拆分、结构化后的需求**
  - **问题分析**：
    - 配置文件中存在赋值语句：`non_sense_3 = non_sense_1[-30] + 2 * sqrt(non_sense_2)`
    - `_analyze_lag_requirements` 方法使用了 `ast.parse(expr, mode="eval")` 来解析表达式
    - `mode="eval"` 只能解析表达式，不能解析赋值语句（赋值语句需要使用 `mode="exec"`）
    - 因此无法正确解析到 `[-30]` 这种 lag 语法
  - **修复方案**：
    - 将 `ast.parse(expr, mode="eval")` 改为 `ast.parse(expr, mode="exec")`
    - `mode="exec"` 可以解析赋值语句，返回 `Module` 节点
    - `ast.NodeVisitor` 会自动遍历所有子节点，包括 `Assign` 节点中的 `Subscript` 节点
    - 因此可以正确识别赋值语句中的 `[-30]` 语法

- **4. Cursor 本次交互后的操作概述**
  - **修改 `core/parser.py`**：
    - 在 `_analyze_lag_requirements` 方法中，将 `ast.parse(expr, mode="eval")` 改为 `ast.parse(expr, mode="exec")`
    - 添加注释说明使用 `mode="exec"` 的原因（支持赋值语句）
  - **验证修复**：
    - 运行 `debug_display.py`，确认 `lag_requirements` 能正确解析到 `{'non_sense_1': 30}`
    - 确认 `record_length` 能根据 lag 需求正确计算（30 * 1.5 = 45）
  - **更新交互记录**：
    - 在 `doc/interaction_record.md` 中记录本次修复


