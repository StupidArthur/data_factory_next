# 导出模板管理模块

## 功能说明

导出模板管理模块用于管理 CSV 导出格式的配置，支持单行标题和双行标题两种格式。

## 目录结构

```
export_templates/
├── __init__.py
├── template_manager.py    # 模板管理器
├── csv_exporter.py        # CSV 导出器
├── templates/            # 模板配置目录
│   ├── moban_1.yaml      # 模板示例 1
│   └── moban_2.yaml      # 模板示例 2
└── README.md
```

## 模板配置格式

模板配置文件为 YAML 格式，存储在 `templates/` 目录下。

### 配置项说明

- `name`: 模板名称（如 `moban_1`, `moban_2`）
- `time_column_name`: 时间列名称（可以是任意字符串，如 `timeStamp`、`Timestamp`、`时间` 等）
- `time_format`: 时间格式字符串（如 `"%Y/%m/%d %H:%M:%S"` 或 `"%Y-%m-%d %H:%M:%S"`）
- `header_rows`: 标题行数（1 或 2）
- `uppercase_column_names`: 是否将位号名转换为全大写，默认 `true`

**注意**：
- `columns` 和 `column_descriptions` 由当前运行的组态决定，不在模板中配置
- `filter_sampled_only` 永远为 `True`，只导出采样周期的数据（`need_sample=True`）

### 示例配置

#### 单行标题（moban_1.yaml）

```yaml
name: moban_1
time_column_name: timeStamp
time_format: "%Y/%m/%d %H:%M:%S"
header_rows: 1
```

#### 双行标题（moban_2.yaml）

```yaml
name: moban_2
time_column_name: Timestamp
time_format: "%Y-%m-%d %H:%M:%S"
header_rows: 2
```

## 使用方式

### 方式1：通过 Engine 导出

```python
from core.parser import DSLParser
from core.engine import UnifiedEngine

# 解析配置
parser = DSLParser()
config = parser.parse_file("config/display_demo.yaml")

# 创建引擎
engine = UnifiedEngine.from_program_config(config)

# 生成数据
results = engine.run_generator(10000)

# 导出数据
engine.export_to_csv(results, template_name="moban_1", output_path="output.csv")
```

### 方式2：使用辅助函数

```python
from utils.export_helper import export_to_csv

# 导出数据
export_to_csv(
    snapshots=results,
    template_name="moban_2",
    output_path="output.csv",
    sample_interval=5.0
)
```

## 导出格式

### 单行标题格式

```csv
timeStamp,sin1.out,valve1.current_opening,non_sense_3
2024/5/24 01:02:03,100.0,50.0,75.5
2024/5/24 01:02:04,101.0,51.0,76.5
```

### 双行标题格式

```csv
Timestamp,sin1.out,valve1.current_opening,non_sense_3,non_sense_1,non_sense_2
时间戳,某工业数据,某工业数据,某工业数据,某工业数据,某工业数据
2024-5-24 01:02:03,100.0,50.0,75.5,45.2,30.8
2024-5-24 01:02:04,101.0,51.0,76.5,46.2,31.8
```

## 注意事项

1. **列由组态决定**：导出的列由当前运行的组态决定，模板只配置文件格式
2. **只导出采样数据**：永远只导出采样周期的数据（`need_sample=True`）
3. **时间格式**：时间格式从 `sim_time` 重新生成，使用模板中配置的 `time_format`
4. **双行标题描述**：如果 `header_rows=2`，第二行使用默认描述"某工业数据"
5. **时间列名称**：时间列名称可以是任意字符串，根据需求自定义（如 `timeStamp`、`Timestamp`、`时间` 等）
6. **列名大小写**：如果 `uppercase_column_names=true`（默认），导出的列名会转换为全大写（如 `pid1.mv` → `PID1.MV`）

