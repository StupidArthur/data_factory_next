"""
快速测试历史数据存储功能（不 sleep）
"""

import sys
import pathlib

# 添加项目根目录到路径
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import programs  # noqa: F401
import functions  # noqa: F401

from datetime import datetime
from core.parser import DSLParser
from core.engine import UnifiedEngine
from data_manager import HistoryConfig

def test_storage_quick():
    """快速测试存储功能"""
    print("=" * 60)
    print("快速测试历史数据存储")
    print("=" * 60)
    
    # 1. 解析配置文件
    parser = DSLParser()
    config_path = project_root / "config" / "display_demo.yaml"
    config = parser.parse_file(config_path)
    print("[OK] 配置文件解析成功")
    
    # 2. 创建引擎
    engine = UnifiedEngine.from_program_config(config)
    print("[OK] 引擎创建成功")
    
    # 3. 启用历史数据存储
    history_config = HistoryConfig(db_path=str(project_root / "tests" / "test_quick_history.duckdb"))
    engine.enable_history_storage(history_config)
    print("[OK] 历史数据存储已启用")
    
    # 4. 手动运行几个周期并存储（模拟 run_realtime 的逻辑）
    print("\n手动运行 20 个周期并存储...")
    engine.clock.config.mode = engine.clock.config.mode  # 保持当前模式
    engine.clock.start()
    
    stored_count = 0
    for i in range(20):
        snapshot = engine._step_once()
        
        # 手动存储（模拟 run_realtime 的逻辑）
        if engine._history_storage:
            need_sample = snapshot.get("need_sample", False)
            if need_sample:
                timestamp = datetime.now()
                engine._history_storage.store_snapshot(snapshot, timestamp, need_sample)
                stored_count += 1
    
    engine.clock.stop()
    print(f"[OK] 运行了 20 个周期，存储了 {stored_count} 个快照")
    
    # 5. 刷新缓冲区
    if engine._history_storage:
        engine._history_storage._flush_buffer()
        print("[OK] 刷新缓冲区成功")
    
    # 6. 查询历史数据
    if engine._history_storage:
        records = engine._history_storage.query_history(limit=100)
        print(f"[OK] 历史数据查询成功，返回 {len(records)} 条记录")
        
        if records:
            print("\n前5条记录:")
            for i, record in enumerate(records[:5]):
                print(f"  {i+1}. {record['param_name']} = {record['param_value']:.4f} "
                      f"(cycle_count={record['cycle_count']})")
            
            # 按参数名分组统计
            param_counts = {}
            for record in records:
                param_name = record['param_name']
                param_counts[param_name] = param_counts.get(param_name, 0) + 1
            
            print(f"\n参数统计（共 {len(param_counts)} 个参数）:")
            for param_name, count in sorted(param_counts.items()):
                print(f"  {param_name}: {count} 条记录")
        
        # 7. 测试统计查询
        if records:
            param_name = records[0]['param_name']
            stats = engine._history_storage.get_statistics(param_name)
            print(f"\n[OK] 统计查询成功 ({param_name}):")
            print(f"  count={stats['count']}, min={stats['min']:.4f}, max={stats['max']:.4f}, avg={stats['avg']:.4f}")
        
        # 8. 测试最新值查询
        latest = engine._history_storage.get_latest_values()
        print(f"\n[OK] 最新值查询成功，返回 {len(latest)} 个参数")
        if latest:
            print("  前5个参数:")
            for i, (param_name, value) in enumerate(list(latest.items())[:5]):
                print(f"    {param_name} = {value:.4f}")
    
    # 9. 关闭连接
    if engine._history_storage:
        engine._history_storage.close()
        print("\n[OK] 关闭连接成功")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_storage_quick()

