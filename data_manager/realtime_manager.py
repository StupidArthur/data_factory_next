"""
实时数据管理模块

负责将实时数据推送到 Redis，并通知 OPCUA 模块。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import redis
from redis.connection import ConnectionPool

from utils.logger import get_logger


logger = get_logger()


@dataclass
class RealtimeConfig:
    """
    实时数据配置
    
    Attributes:
        redis_host: Redis 主机地址
        redis_port: Redis 端口
        redis_db: Redis 数据库编号
        redis_password: Redis 密码（可选）
        pubsub_channel: Pub/Sub 频道名称，用于通知 OPCUA 模块
        use_connection_pool: 是否使用连接池（默认 False，单线程场景不需要）
    """
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    pubsub_channel: str = "data_factory"
    use_connection_pool: bool = False


class RealtimeDataManager:
    """
    实时数据管理器
    
    功能：
    - 按 Clock 执行周期推送数据到 Redis
    - 更新 data_factory:current 键（最新数据）
    - 发布通知到 Pub/Sub（通知 OPCUA 模块）
    """
    
    # Redis 键前缀
    REDIS_KEY_PREFIX = "data_factory"
    
    def __init__(self, config: RealtimeConfig):
        """
        初始化实时数据管理器
        
        Args:
            config: 实时数据配置
        """
        self.config = config
        self._redis_client: Optional[redis.Redis] = None
        self._connection_pool: Optional[ConnectionPool] = None
        
        # 初始化 Redis 连接
        self._init_redis()
        
        logger.info(
            "RealtimeDataManager initialized: redis=%s:%d/%d, channel=%s",
            config.redis_host,
            config.redis_port,
            config.redis_db,
            config.pubsub_channel,
        )
    
    def _init_redis(self) -> None:
        """初始化 Redis 连接"""
        try:
            if self.config.use_connection_pool:
                # 使用连接池
                self._connection_pool = ConnectionPool(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    password=self.config.redis_password,
                    decode_responses=True,
                    max_connections=10,
                )
                self._redis_client = redis.Redis(connection_pool=self._connection_pool)
            else:
                # 普通连接
                self._redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    password=self.config.redis_password,
                    decode_responses=True,
                )
            
            # 测试连接
            self._redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def push_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """
        推送快照到 Redis（每个周期都推送）
        
        操作：
        1. 更新 data_factory:current 键（最新数据）
        2. 发布通知到 Pub/Sub（通知 OPCUA 模块）
        
        Args:
            snapshot: 快照数据字典，包含所有变量值和元数据
        """
        try:
            # 准备数据
            current_key = f"{self.REDIS_KEY_PREFIX}:current"
            
            # 构建推送数据
            push_data = {
                "timestamp": snapshot.get("sim_time", 0.0),
                "datetime": snapshot.get("time_str", ""),
                "cycle_count": snapshot.get("cycle_count", 0),
                "sim_time": snapshot.get("sim_time", 0.0),
                "params": {
                    k: v
                    for k, v in snapshot.items()
                    if k not in ["cycle_count", "need_sample", "time_str", "sim_time", "exec_ratio"]
                },
            }
            
            # 更新 current 键
            self._redis_client.set(current_key, json.dumps(push_data))
            
            # 发布通知到 Pub/Sub（通知 OPCUA 模块）
            notification = {
                "timestamp": snapshot.get("sim_time", 0.0),
                "cycle_count": snapshot.get("cycle_count", 0),
            }
            self._redis_client.publish(self.config.pubsub_channel, json.dumps(notification))
            
            logger.debug(
                "Snapshot pushed to Redis: cycle_count=%d, params_count=%d",
                snapshot.get("cycle_count", 0),
                len(push_data["params"]),
            )
        except Exception as e:
            logger.error(f"Failed to push snapshot to Redis: {e}", exc_info=True)
            # 不抛出异常，避免影响主流程
    
    def close(self) -> None:
        """关闭 Redis 连接"""
        try:
            if self._redis_client:
                if self.config.use_connection_pool:
                    # 连接池会自动管理连接，只需要关闭池
                    if self._connection_pool:
                        self._connection_pool.disconnect()
                else:
                    # 普通连接需要手动关闭
                    self._redis_client.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Failed to close Redis connection: {e}", exc_info=True)

