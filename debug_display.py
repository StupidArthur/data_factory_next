"""
Display调试脚本

用于调试display_demo.yaml的运行逻辑。
- 使用GENERATOR模式（不sleep）
- 简单打印输出
"""

"""
Display调试脚本

用于调试display_demo.yaml的运行逻辑。
- 使用GENERATOR模式（不sleep）
- 简单打印输出

运行方式：
    python run_debug.py
    或者
    python -m debug_display（需要从项目根目录的父目录运行）
"""

import pathlib
import sys

# 导入程序和函数（触发注册）
import programs  # noqa: F401
import functions  # noqa: F401

# 导入 core 模块
from core.parser import DSLParser
from core.clock import ClockMode


def debug_display():
    """调试display_demo.yaml的运行逻辑。"""
    print("=" * 60)
    print("Display调试")
    print("=" * 60)

    # 1. 解析配置文件
    config_path = pathlib.Path(__file__).parent / "config" / "display_demo.yaml"
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
        
        # 确保使用GENERATOR模式（不sleep）
        config.clock.mode = ClockMode.GENERATOR
        print(f"   - 时钟模式: {config.clock.mode.name} (不sleep)")
    except Exception as e:
        print(f"   [FAIL] 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. 创建引擎
    print(f"\n2. 创建执行引擎")
    try:
        from core.engine import UnifiedEngine
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
    print(f"\n3. 执行 20 个周期（GENERATOR模式，不sleep）")
    try:
        results = engine.run_for_steps(10000)
        print(f"   [OK] 执行成功，共 {len(results)} 个周期")

        # # 打印每个周期的快照
        # print(f"\n   周期快照:")
        # for i, snapshot in enumerate(results):
        #     print(f"   周期 {i+1} (cycle_count={snapshot['cycle_count']}, sim_time={snapshot['sim_time']:.2f}):")
        #     # 打印所有变量
        #     for var_name, var_value in snapshot.items():
        #         if var_name not in ['cycle_count', 'need_sample', 'time_str', 'sim_time', 'exec_ratio']:
        #             print(f"     {var_name} = {var_value:.4f}")
        #     print()
        
    except Exception as e:
        print(f"   [FAIL] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"\n" + "=" * 60)
    print("调试完成！")
    print("=" * 60)


if __name__ == "__main__":
    debug_display()

