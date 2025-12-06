"""
测试 OPCUA Server 模块
"""

import time
import json
import redis
from data_manager.opcua_server import OPCUAServer, OPCUAServerConfig

def test_opcua_server():
    """测试 OPCUA Server"""
    print("=" * 60)
    print("测试 OPCUA Server")
    print("=" * 60)
    
    # 1. 创建配置
    config = OPCUAServerConfig(
        server_url="opc.tcp://0.0.0.0:18951",
        redis_host="localhost",
        redis_port=6379,
        pubsub_channel="data_factory",
        update_cycle=0.1,
    )
    
    # 2. 创建 OPCUA Server
    try:
        server = OPCUAServer(config)
        print("[OK] OPCUA Server 创建成功")
    except Exception as e:
        print(f"[FAIL] OPCUA Server 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 启动服务器
    try:
        server.start()
        print("[OK] OPCUA Server 启动成功")
        print("    服务器地址: opc.tcp://0.0.0.0:18951")
        print("    等待服务器初始化...")
        time.sleep(2)  # 等待服务器初始化
    except Exception as e:
        print(f"[FAIL] OPCUA Server 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 测试推送数据到 Redis
    try:
        redis_client = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,
        )
        
        # 推送测试数据
        test_data = {
            "timestamp": time.time(),
            "datetime": "2024-12-06 10:00:00",
            "cycle_count": 1,
            "sim_time": 0.5,
            "params": {
                "tank1.level": 50.5,
                "pid1.mv": 30.0,
                "pid1.pv": 50.5,
                "valve1.current_opening": 25.0,
            },
        }
        
        redis_key = "data_factory:current"
        redis_client.set(redis_key, json.dumps(test_data))
        print("[OK] 测试数据已推送到 Redis")
        
        # 发布通知
        redis_client.publish("data_factory", json.dumps({"timestamp": time.time(), "cycle_count": 1}))
        print("[OK] 更新通知已发布到 Pub/Sub")
        
        # 等待节点更新
        print("    等待节点更新（3秒）...")
        time.sleep(3)
        
        # 检查节点是否创建
        if len(server.node_map) > 0:
            print(f"[OK] 节点已创建，共 {len(server.node_map)} 个节点")
            print("    节点列表:")
            for param_name in list(server.node_map.keys())[:5]:
                print(f"      - {param_name}")
        else:
            print("[WARN] 节点尚未创建（可能需要更多时间）")
        
    except Exception as e:
        print(f"[FAIL] 测试数据推送失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. 停止服务器
    try:
        server.stop()
        time.sleep(1)  # 等待停止
        server.close()
        print("[OK] OPCUA Server 已停止")
    except Exception as e:
        print(f"[FAIL] OPCUA Server 停止失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n提示：")
    print("  1. 可以使用 OPCUA 客户端连接到 opc.tcp://localhost:18951")
    print("  2. 节点名称使用位号名（如 tank1.level, pid1.mv）")
    print("  3. 独立启动方式: python -m data_manager.run_opcua_server")

if __name__ == "__main__":
    test_opcua_server()

