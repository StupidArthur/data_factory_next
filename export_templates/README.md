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
- `time_column_name`: 时间列名称，严格区分大小写（`timeStamp` 或 `Timestamp`）
- `time_format`: 时间格式字符串（如 `"%Y/%m/%d %H:%M:%S"` 或 `"%Y-%m-%d %H:%M:%S"`）
- `header_rows`: 标题行数（1 或 2）
- `filter_sampled_only`: 是否只导出 `need_sample=True` 的数据
- `columns`: 要导出的位号名列表（按顺序）
- `column_descriptions`: 位号描述列表（与 `columns` 对应，空字符串则使用默认描述"某工业数据"）

### 示例配置

#### 单行标题（moban_1.yaml）

```yaml
name: moban_1
time_column_name: timeStamp
time_format: "%Y/%m/%d %H:%M:%S"
header_rows: 1
filter_sampled_only: false
columns:
  - sin1.out
  - valve1.current_opening
  - non_sense_3
column_descriptions: []
```

#### 双行标题（moban_2.yaml）

```yaml
name: moban_2
time_column_name: Timestamp
time_format: "%Y-%m-%d %H:%M:%S"
header_rows: 2
filter_sampled_only: true
columns:
  - sin1.out
  - valve1.current_opening
  - non_sense_3
  - non_sense_1
  - non_sense_2
column_descriptions:
  - "正弦波输出"
  - "阀门开度"
  - ""  # 空字符串，将使用默认描述"某工业数据"
  - "无意义变量1"
  - "无意义变量2"
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
时间戳,正弦波输出,阀门开度,某工业数据,无意义变量1,无意义变量2
2024-5-24 01:02:03,100.0,50.0,75.5,45.2,30.8
2024-5-24 01:02:04,101.0,51.0,76.5,46.2,31.8
```

## 注意事项

1. 时间格式从 `sim_time` 重新生成，使用模板中配置的 `time_format`
2. 如果 `filter_sampled_only=true`，只导出 `need_sample=True` 的数据
3. 如果 `columns` 为空，则导出所有变量（排除元数据字段）
4. 如果 `column_descriptions` 为空字符串，则使用默认描述"某工业数据"
5. 时间列名称严格区分大小写（`timeStamp` 或 `Timestamp`）

