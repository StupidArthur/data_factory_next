"""
OPCUA Server 调试脚本

启动 OPCUA Server。
"""

import signal
import sys
import time

from data_manager.opcua_server import OPCUAServer, OPCUAServerConfig
from utils.logger import get_logger

logger = get_logger()


def debug_opcua():
    """启动 OPCUA Server"""
    # 创建配置
    # 注意：使用 0.0.0.0 监听所有接口，客户端连接时使用 localhost 或实际IP
    config = OPCUAServerConfig(
        server_url="opc.tcp://0.0.0.0:18953",  # 使用标准端口
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password=None,
        pubsub_channel="data_factory",
        update_cycle=1.0,  # 降低更新频率到1秒，减少性能开销
    )
    
    # 创建 OPCUA Server
    server = OPCUAServer(config)
    
    # 注册信号处理（优雅退出）
    def signal_handler(sig, frame):
        logger.info("收到中断信号，正在关闭...")
        server.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("=" * 60)
        logger.info("启动 OPCUA Server")
        logger.info(f"Server URL: {config.server_url}")
        logger.info(f"Redis: {config.redis_host}:{config.redis_port}/{config.redis_db}")
        logger.info("=" * 60)
        
        server.start()
        logger.info("OPCUA Server 运行中，按 Ctrl+C 停止")
        
        # 保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭...")
    except Exception as e:
        logger.error(f"错误: {e}", exc_info=True)
    finally:
        server.close()
        logger.info("OPCUA Server 已停止")


if __name__ == "__main__":
    debug_opcua()

