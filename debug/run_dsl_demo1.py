"""
运行 dsl_demo1.yaml 组态并导出数据

使用 GENERATOR 模式运行 10000 个周期，并使用 pid_loop_tuning.yaml 模板导出。
"""

import pathlib
from pathlib import Path

# 导入程序和函数（触发注册）
import programs  # noqa: F401
import functions  # noqa: F401

# 导入 core 模块
from core.parser import DSLParser
from core.engine import UnifiedEngine


def run_dsl_demo1():
    """运行 dsl_demo1.yaml 组态并导出数据。"""
    # 配置文件路径
    config_path = pathlib.Path(__file__).parent.parent / "config" / "dsl_demo1.yaml"
    
    # 解析配置文件
    parser = DSLParser()
    config = parser.parse_file(config_path)
    
    # 创建引擎
    engine = UnifiedEngine.from_program_config(config)
    
    # 运行 10000 个周期（GENERATOR 模式）
    results = engine.run_generator(10000)
    
    # 导出数据（使用 pid_loop_tuning.yaml 模板）
    output_path = Path(__file__).parent.parent / "output" / "dsl_demo1_output.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    engine.export_to_csv(
        snapshots=results,
        template_name="pid_loop_tuning",
        output_path=output_path,
    )
    
    print(f"运行完成：共 {len(results)} 个周期")
    print(f"导出文件：{output_path}")


if __name__ == "__main__":
    run_dsl_demo1()

