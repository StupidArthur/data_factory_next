"""
DSL 测试脚本

用于测试 DSL 解析和执行流程。
"""

import pathlib
import sys

# 添加项目根目录到路径
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.parser import DSLParser
from core.engine import UnifiedEngine

# 导入程序和函数（触发注册）
import programs  # noqa: F401
import functions  # noqa: F401


def test_dsl_demo1():
    """测试 dsl_demo1.yaml 的解析和执行。"""
    print("=" * 60)
    print("测试 DSL 解析和执行")
    print("=" * 60)

    # 1. 解析配置文件
    config_path = project_root / "config" / "dsl_demo1.yaml"
    print(f"\n1. 解析配置文件: {config_path}")

    parser = DSLParser()
    try:
        config = parser.parse_file(config_path)
        print(f"   [OK] 解析成功")
        print(f"   - 程序项数量: {len(config.program)}")
        print(f"   - 历史记录长度: {config.record_length}")
        print(f"   - 需要历史数据的变量: {len(config.lag_requirements)}")
        if config.lag_requirements:
            print(f"   - Lag 需求: {config.lag_requirements}")
    except Exception as e:
        print(f"   [FAIL] 解析失败: {e}")
        import traceback

        traceback.print_exc()
        return

    # 2. 创建引擎
    print(f"\n2. 创建执行引擎")
    try:
        engine = UnifiedEngine.from_program_config(config)
        print(f"   [OK] 引擎创建成功")
        print(f"   - 节点数量: {len(engine._nodes)}")
        print(f"   - 实例数量: {len(engine._instances)}")
    except Exception as e:
        print(f"   [FAIL] 引擎创建失败: {e}")
        import traceback

        traceback.print_exc()
        return

    # 3. 执行几个周期
    print(f"\n3. 执行 10 个周期")
    try:
        results = engine.run_generator(10)
        print(f"   [OK] 执行成功，共 {len(results)} 个周期")

        # 打印前 3 个周期的快照
        print(f"\n   前 3 个周期的快照:")
        for i, snapshot in enumerate(results[:3]):
            print(f"   周期 {i+1}:")
            # 只打印部分关键变量
            key_vars = [
                "pid1.mv",
                "tank1.level",
                "sin1.out",
                "non_sense_3",
                "non_sense_4",
            ]
            for var in key_vars:
                if var in snapshot:
                    print(f"     {var} = {snapshot[var]:.4f}")
            print(f"     cycle_count = {snapshot['cycle_count']}")
            print(f"     sim_time = {snapshot['sim_time']:.2f}")

    except Exception as e:
        print(f"   [FAIL] 执行失败: {e}")
        import traceback

        traceback.print_exc()
        return

    print(f"\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_dsl_demo1()

