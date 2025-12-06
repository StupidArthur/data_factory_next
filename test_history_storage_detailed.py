"""
详细测试历史数据存储功能
"""

import programs  # noqa: F401
import functions  # noqa: F401

from datetime import datetime
from core.parser import DSLParser
from core.engine import UnifiedEngine
from data_manager import HistoryConfig

def test_history_storage_with_engine():
    """测试引擎集成历史存储"""
    print("=" * 60)
    print("测试引擎集成历史存储")
    print("=" * 60)
    
    # 1. 解析配置文件
    parser = DSLParser()
    config = parser.parse_file("config/display_demo.yaml")
    print("[OK] 配置文件解析成功")
    
    # 2. 创建引擎
    engine = UnifiedEngine.from_program_config(config)
    print("[OK] 引擎创建成功")
    
    # 3. 启用历史数据存储
    history_config = HistoryConfig(db_path="test_detailed_history.duckdb")
    engine.enable_history_storage(history_config)
    print("[OK] 历史数据存储已启用")
    
    # 4. 运行几个周期（REALTIME 模式，但快速执行）
    print("\n运行 20 个周期（REALTIME 模式）...")
    count = 0
    sample_count = 0
    
    for snapshot in engine.run_realtime():
        count += 1
        if snapshot.get('need_sample'):
            sample_count += 1
        
        if count >= 20:
            break
    
    print(f"[OK] 运行了 {count} 个周期，其中 {sample_count} 个需要采样")
    
    # 5. 手动刷新缓冲区（确保数据写入数据库）
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
                      f"(cycle_count={record['cycle_count']}, timestamp={record['timestamp']})")
        
        # 7. 测试统计查询
        if records:
            param_name = records[0]['param_name']
            stats = engine._history_storage.get_statistics(param_name)
            print(f"\n[OK] 统计查询成功 ({param_name}):")
            print(f"  count={stats['count']}, min={stats['min']}, max={stats['max']}, avg={stats['avg']:.4f}")
        
        # 8. 测试采样查询
        sampled = engine._history_storage.query_sampled(
            sample_interval=1.0,  # 每1秒采样一次
            limit=100
        )
        print(f"[OK] 采样查询成功，返回 {len(sampled)} 条记录")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_history_storage_with_engine()

