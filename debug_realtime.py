"""
实时模式调试脚本

运行 dsl_demo1.yaml，使用 REALTIME 模式。
"""

import pathlib

# 导入程序和函数（触发注册）
import programs  # noqa: F401
import functions  # noqa: F401

from core.parser import DSLParser
from core.engine import UnifiedEngine
from data_manager import RealtimeDataManager, RealtimeConfig
from utils.logger import get_logger

logger = get_logger()


def debug_realtime():
    """运行 dsl_demo1.yaml，REALTIME 模式"""
    # 解析配置文件
    config_path = pathlib.Path(__file__).parent / "config" / "dsl_demo1.yaml"
    logger.info(f"解析配置文件: {config_path}")
    
    parser = DSLParser()
    config = parser.parse_file(config_path)
    
    # 创建引擎
    engine = UnifiedEngine.from_program_config(config)
    
    # 启用实时数据管理（推送到 Redis，供 OPCUA Server 使用）
    try:
        realtime_config = RealtimeConfig(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            redis_password=None,
            pubsub_channel="data_factory",
        )
        engine.enable_realtime_data(realtime_config)
        logger.info("实时数据管理已启用（推送到 Redis）")
    except Exception as e:
        logger.warning(f"启用实时数据管理失败（Redis 可能未启动）: {e}")
        logger.warning("OPCUA Server 将无法获取数据更新")
    
    logger.info("引擎创建成功，开始实时运行（按 Ctrl+C 停止）")
    
    # 实时运行
    try:
        for snapshot in engine.run_realtime():
            # 可以在这里处理快照数据
            pass
    except KeyboardInterrupt:
        logger.info("用户中断，停止运行")


if __name__ == "__main__":
    debug_realtime()

