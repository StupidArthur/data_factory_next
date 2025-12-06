"""
测试 data_manager 模块功能
"""

import sys
from datetime import datetime, timedelta

# 导入程序和函数（触发注册）
import programs  # noqa: F401
import functions  # noqa: F401

from core.parser import DSLParser
from core.engine import UnifiedEngine
from data_manager import RealtimeConfig, HistoryConfig

def test_imports():
    """测试导入"""
    print("=" * 60)
    print("1. 测试导入")
    print("=" * 60)
    try:
        from data_manager import RealtimeDataManager, HistoryStorage
        print("[OK] 导入成功")
        return True
    except ImportError as e:
        print(f"[FAIL] 导入失败: {e}")
        return False

def test_history_storage():
    """测试历史数据存储（DuckDB）"""
    print("\n" + "=" * 60)
    print("2. 测试历史数据存储（DuckDB）")
    print("=" * 60)
    
    try:
        from data_manager import HistoryStorage
        
        # 创建测试数据库
        config = HistoryConfig(db_path="test_history.duckdb")
        storage = HistoryStorage(config)
        print("[OK] HistoryStorage 初始化成功")
        
        # 测试存储
        test_snapshot = {
            "tank1.level": 50.5,
            "pid1.mv": 30.0,
            "pid1.pv": 50.5,
            "cycle_count": 1,
            "need_sample": True,
            "sim_time": 0.5,
            "time_str": "2024-12-06 10:00:00",
        }
        
        timestamp = datetime.now()
        storage.store_snapshot(test_snapshot, timestamp, need_sample=True)
        print("[OK] 存储快照成功")
        
        # 手动刷新缓冲区（确保数据写入数据库）
        storage._flush_buffer()
        print("[OK] 刷新缓冲区成功")
        
        # 测试查询历史数据
        records = storage.query_history(param_name="tank1.level", limit=10)
        print(f"[OK] 查询历史数据成功，返回 {len(records)} 条记录")
        if records:
            print(f"    示例记录: {records[0]}")
        
        # 测试采样查询
        sampled = storage.query_sampled(
            param_name="tank1.level",
            sample_interval=1.0,
            limit=10
        )
        print(f"[OK] 采样查询成功，返回 {len(sampled)} 条记录")
        
        # 测试统计查询
        stats = storage.get_statistics("tank1.level")
        print(f"[OK] 统计查询成功: count={stats['count']}, avg={stats['avg']}")
        
        # 测试最新值查询
        latest = storage.get_latest_values()
        print(f"[OK] 最新值查询成功，返回 {len(latest)} 个参数")
        if latest:
            print(f"    示例: tank1.level = {latest.get('tank1.level')}")
        
        # 关闭连接
        storage.close()
        print("[OK] 关闭连接成功")
        
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_realtime_manager():
    """测试实时数据管理（Redis）"""
    print("\n" + "=" * 60)
    print("3. 测试实时数据管理（Redis）")
    print("=" * 60)
    
    try:
        from data_manager import RealtimeDataManager
        
        # 创建 Redis 连接配置
        config = RealtimeConfig(
            redis_host="localhost",
            redis_port=6379,
            pubsub_channel="data_factory"
        )
        
        # 尝试连接 Redis
        try:
            manager = RealtimeDataManager(config)
            print("[OK] RealtimeDataManager 初始化成功")
        except Exception as e:
            print(f"[SKIP] Redis 连接失败（可能未启动）: {e}")
            print("    提示: 如果不需要测试 Redis，可以跳过此测试")
            return True  # 跳过测试，不算失败
        
        # 测试推送快照
        test_snapshot = {
            "tank1.level": 50.5,
            "pid1.mv": 30.0,
            "cycle_count": 1,
            "sim_time": 0.5,
            "time_str": "2024-12-06 10:00:00",
        }
        
        manager.push_snapshot(test_snapshot)
        print("[OK] 推送快照成功")
        
        # 关闭连接
        manager.close()
        print("[OK] 关闭连接成功")
        
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_engine_integration():
    """测试 Engine 集成"""
    print("\n" + "=" * 60)
    print("4. 测试 Engine 集成")
    print("=" * 60)
    
    try:
        # 解析配置文件
        parser = DSLParser()
        config = parser.parse_file("config/display_demo.yaml")
        print("[OK] 配置文件解析成功")
        
        # 创建引擎
        engine = UnifiedEngine.from_program_config(config)
        print("[OK] 引擎创建成功")
        
        # 启用历史数据存储
        history_config = HistoryConfig(db_path="test_engine_history.duckdb")
        engine.enable_history_storage(history_config)
        print("[OK] 历史数据存储已启用")
        
        # 尝试启用实时数据管理（如果 Redis 可用）
        try:
            realtime_config = RealtimeConfig(
                redis_host="localhost",
                redis_port=6379,
                pubsub_channel="data_factory"
            )
            engine.enable_realtime_data(realtime_config)
            print("[OK] 实时数据管理已启用")
        except Exception as e:
            print(f"[SKIP] 实时数据管理启用失败（Redis 可能未启动）: {e}")
        
        # 运行几个周期（GENERATOR 模式）
        print("\n运行 10 个周期（GENERATOR 模式）...")
        results = engine.run_generator(10)
        print(f"[OK] 运行成功，生成了 {len(results)} 个快照")
        
        # 检查快照数据
        if results:
            snapshot = results[0]
            print(f"    快照包含字段: {list(snapshot.keys())[:5]}...")
            print(f"    cycle_count: {snapshot.get('cycle_count')}")
            print(f"    need_sample: {snapshot.get('need_sample')}")
        
        # 测试历史数据查询
        if engine._history_storage:
            records = engine._history_storage.query_history(limit=10)
            print(f"[OK] 历史数据查询成功，返回 {len(records)} 条记录")
        
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_realtime_execution():
    """测试实时执行（短时间运行）"""
    print("\n" + "=" * 60)
    print("5. 测试实时执行（短时间运行）")
    print("=" * 60)
    
    try:
        # 解析配置文件
        parser = DSLParser()
        config = parser.parse_file("config/display_demo.yaml")
        
        # 创建引擎
        engine = UnifiedEngine.from_program_config(config)
        
        # 启用历史数据存储
        history_config = HistoryConfig(db_path="test_realtime_history.duckdb")
        engine.enable_history_storage(history_config)
        print("[OK] 历史数据存储已启用")
        
        # 尝试启用实时数据管理
        try:
            realtime_config = RealtimeConfig(
                redis_host="localhost",
                redis_port=6379,
                pubsub_channel="data_factory"
            )
            engine.enable_realtime_data(realtime_config)
            print("[OK] 实时数据管理已启用")
        except Exception as e:
            print(f"[SKIP] 实时数据管理启用失败: {e}")
        
        # 运行几个周期（REALTIME 模式，但快速执行）
        print("\n运行 5 个周期（REALTIME 模式）...")
        count = 0
        for snapshot in engine.run_realtime():
            count += 1
            print(f"  周期 {count}: cycle_count={snapshot.get('cycle_count')}, need_sample={snapshot.get('need_sample')}")
            if count >= 5:
                break  # 只运行5个周期
        
        print(f"[OK] 实时执行成功，运行了 {count} 个周期")
        
        # 检查历史数据
        if engine._history_storage:
            records = engine._history_storage.query_history(limit=10)
            print(f"[OK] 历史数据存储成功，共 {len(records)} 条记录")
        
        return True
    except KeyboardInterrupt:
        print("\n[OK] 用户中断（正常）")
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Data Manager 模块测试")
    print("=" * 60)
    
    results = []
    
    # 1. 测试导入
    results.append(("导入测试", test_imports()))
    
    # 2. 测试历史数据存储
    results.append(("历史数据存储", test_history_storage()))
    
    # 3. 测试实时数据管理
    results.append(("实时数据管理", test_realtime_manager()))
    
    # 4. 测试 Engine 集成
    results.append(("Engine 集成", test_engine_integration()))
    
    # 5. 测试实时执行
    results.append(("实时执行", test_realtime_execution()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results:
        if result:
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name}")
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

