"""
独立启动 OPCUA Server

使用方式：
    python -m data_manager.run_opcua_server
    或者
    python data_manager/run_opcua_server.py
"""

import argparse
import signal
import sys
from data_manager.opcua_server import OPCUAServer, OPCUAServerConfig
from utils.logger import get_logger


logger = get_logger()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Data Factory OPCUA Server")
    parser.add_argument(
        "--server-url",
        type=str,
        default="opc.tcp://0.0.0.0:18951",
        help="OPCUA Server URL (default: opc.tcp://0.0.0.0:18951)",
    )
    parser.add_argument(
        "--redis-host",
        type=str,
        default="localhost",
        help="Redis host (default: localhost)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redis port (default: 6379)",
    )
    parser.add_argument(
        "--redis-db",
        type=int,
        default=0,
        help="Redis database number (default: 0)",
    )
    parser.add_argument(
        "--redis-password",
        type=str,
        default=None,
        help="Redis password (optional)",
    )
    parser.add_argument(
        "--pubsub-channel",
        type=str,
        default="data_factory",
        help="Redis Pub/Sub channel (default: data_factory)",
    )
    parser.add_argument(
        "--update-cycle",
        type=float,
        default=0.1,
        help="Update cycle in seconds (default: 0.1)",
    )
    
    args = parser.parse_args()
    
    # 创建配置
    config = OPCUAServerConfig(
        server_url=args.server_url,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        redis_db=args.redis_db,
        redis_password=args.redis_password,
        pubsub_channel=args.pubsub_channel,
        update_cycle=args.update_cycle,
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
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        server.close()
        logger.info("OPCUA Server stopped")


if __name__ == "__main__":
    main()

