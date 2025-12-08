"""
独立启动 OPCUA Server

使用方式：
    python -m data_manager.run_opcua_server
    或者
    python data_manager/run_opcua_server.py
"""

import signal
import sys
import time
from typing import Optional

from data_manager.opcua_server import OPCUAServer, OPCUAServerConfig
from utils.logger import get_logger


logger = get_logger()


def run_opcua_server(
    server_url: str = "opc.tcp://0.0.0.0:18951",
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
    pubsub_channel: str = "data_factory",
    update_cycle: float = 0.1,
) -> None:
    """
    运行 OPCUA Server
    
    Args:
        server_url: OPCUA Server 地址，默认 opc.tcp://0.0.0.0:18951
        redis_host: Redis 主机地址，默认 localhost
        redis_port: Redis 端口，默认 6379
        redis_db: Redis 数据库编号，默认 0
        redis_password: Redis 密码（可选），默认 None
        pubsub_channel: Redis Pub/Sub 频道名称，默认 data_factory
        update_cycle: 更新周期（秒），默认 0.1
    """
    # 创建配置
    config = OPCUAServerConfig(
        server_url=server_url,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
        redis_password=redis_password,
        pubsub_channel=pubsub_channel,
        update_cycle=update_cycle,
    )
    
    # 创建 OPCUA Server
    server = OPCUAServer(config)
    
    # 注册信号处理（优雅退出）
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal, shutting down...")
        server.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动服务器
        logger.info("=" * 60)
        logger.info("Starting Data Factory OPCUA Server")
        logger.info("=" * 60)
        logger.info(f"Server URL: {config.server_url}")
        logger.info(f"Redis: {config.redis_host}:{config.redis_port}/{config.redis_db}")
        logger.info(f"Pub/Sub Channel: {config.pubsub_channel}")
        logger.info(f"Update Cycle: {config.update_cycle}s")
        logger.info("=" * 60)
        
        server.start()
        
        # 保持运行
        logger.info("OPCUA Server is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        server.close()
        logger.info("OPCUA Server stopped")


if __name__ == "__main__":
    # 使用函数参数方式，在 __main__ 中直接调用
    run_opcua_server()
