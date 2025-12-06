"""
OPCUA Server 模块

独立启动的 OPCUA Server，从 Redis 读取数据并更新节点。
节点的 name、display_name、browse_name、node_id 都使用位号名（param_name）。
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

import redis
from asyncua import Server, ua

from utils.logger import get_logger


logger = get_logger()


@dataclass
class OPCUAServerConfig:
    """
    OPCUA Server 配置
    
    Attributes:
        server_url: OPCUA Server 地址，默认 opc.tcp://0.0.0.0:18951
        redis_host: Redis 主机地址
        redis_port: Redis 端口
        redis_db: Redis 数据库编号
        redis_password: Redis 密码（可选）
        pubsub_channel: Pub/Sub 频道名称，用于接收数据更新通知
        update_cycle: 更新周期（秒），默认 0.1 秒
    """
    server_url: str = "opc.tcp://0.0.0.0:18951"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    pubsub_channel: str = "data_factory"
    update_cycle: float = 0.1


class OPCUAServer:
    """
    OPCUA Server
    
    功能：
    - 从 Redis 读取数据（data_factory:current）
    - 监听 Pub/Sub 频道接收更新通知
    - 动态创建节点（使用位号名作为节点标识）
    - 更新节点值
    """
    
    # Redis 键前缀
    REDIS_KEY_PREFIX = "data_factory"
    
    def __init__(self, config: OPCUAServerConfig):
        """
        初始化 OPCUA Server
        
        Args:
            config: OPCUA Server 配置
        """
        self.config = config
        
        # 初始化 Redis 连接
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True,
        )
        
        # 测试 Redis 连接
        try:
            self.redis_client.ping()
            logger.info("Redis connection established in OPCUA Server")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        
        # OPCUA Server
        self.server: Optional[Server] = None
        self.namespace_idx: Optional[int] = None
        
        # 存储节点映射：位号名（param_name） -> 节点对象
        self.node_map: Dict[str, Any] = {}
        
        # 存储节点类型映射：位号名 -> VariantType
        self.node_type_map: Dict[str, ua.VariantType] = {}
        
        # 运行控制
        self._running = False
        self._asyncio_loop: Optional[asyncio.AbstractEventLoop] = None
        self._server_task: Optional[asyncio.Task] = None
        self._update_task: Optional[asyncio.Task] = None
        self._pubsub_task: Optional[asyncio.Task] = None
        
        logger.info(
            "OPCUA Server initialized: server_url=%s, redis=%s:%d/%d, channel=%s",
            config.server_url,
            config.redis_host,
            config.redis_port,
            config.redis_db,
            config.pubsub_channel,
        )
    
    async def _init_server(self) -> None:
        """初始化 OPCUA Server"""
        self.server = Server()
        await self.server.init()
        
        # 设置端点
        self.server.set_endpoint(self.config.server_url)
        
        # 设置服务器名称
        self.server.set_server_name("Data Factory OPCUA Server")
        
        # 注册命名空间
        uri = "http://data_factory.opcua"
        self.namespace_idx = await self.server.register_namespace(uri)
        logger.info(f"OPCUA Server namespace registered: {uri} (idx={self.namespace_idx})")
        
        # 获取 Objects 文件夹
        objects = self.server.get_objects_node()
        
        # 创建根文件夹
        root_folder = await objects.add_folder(
            self.namespace_idx,
            "DataFactory",
            "DataFactory"
        )
        
        # 存储根文件夹（用于后续创建节点）
        self._root_folder = root_folder
        
        logger.info("OPCUA Server initialized")
    
    async def _create_node(self, param_name: str, initial_value: float = 0.0) -> None:
        """
        创建 OPCUA 节点（使用位号名）
        
        Args:
            param_name: 位号名（如 "tank1.level"）
            initial_value: 初始值
        """
        try:
            # 使用位号名作为节点的所有标识
            # name、display_name、browse_name、node_id 都使用位号名
            
            # 创建字符串类型的 NodeId（使用位号名）
            node_id = ua.NodeId(param_name, self.namespace_idx)
            
            # 创建变量节点
            var_node = await self._root_folder.add_variable(
                node_id,  # NodeId（使用位号名）
                param_name,  # BrowseName（使用位号名）
                ua.Variant(initial_value, ua.VariantType.Double)
            )
            
            # 设置 DisplayName（使用位号名）
            await var_node.set_display_name(ua.LocalizedText(param_name))
            
            # 设置节点为只读
            await var_node.set_writable(False)
            
            # 存储节点映射
            self.node_map[param_name] = var_node
            self.node_type_map[param_name] = ua.VariantType.Double
            
            logger.debug(f"Created OPCUA node: {param_name} (node_id={node_id})")
        except Exception as e:
            logger.error(f"Failed to create node {param_name}: {e}", exc_info=True)
    
    async def _update_nodes(self, params: Dict[str, Any]) -> None:
        """
        更新 OPCUA 节点值
        
        Args:
            params: 参数字典，key 为位号名，value 为参数值
        """
        for param_name, param_value in params.items():
            try:
                # 如果节点不存在，创建它
                if param_name not in self.node_map:
                    await self._create_node(param_name, float(param_value) if isinstance(param_value, (int, float)) else 0.0)
                
                # 获取节点
                node = self.node_map.get(param_name)
                if node is None:
                    continue
                
                # 只更新数值类型
                if isinstance(param_value, (int, float)):
                    # 获取节点类型
                    variant_type = self.node_type_map.get(param_name, ua.VariantType.Double)
                    
                    # 更新节点值
                    await node.write_value(ua.Variant(float(param_value), variant_type))
                    
                    logger.debug(f"Updated node {param_name} = {param_value}")
            except Exception as e:
                logger.error(f"Failed to update node {param_name}: {e}", exc_info=True)
    
    async def _update_loop(self) -> None:
        """更新循环（从 Redis 读取数据并更新 OPCUA 节点）"""
        while self._running:
            try:
                cycle_start_time = time.time()
                
                # 从 Redis 读取当前数据
                redis_key = f"{self.REDIS_KEY_PREFIX}:current"
                json_data = self.redis_client.get(redis_key)
                
                if json_data:
                    try:
                        data = json.loads(json_data)
                        params = data.get("params", {})
                        
                        # 更新 OPCUA 节点
                        await self._update_nodes(params)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON data from Redis: {e}")
                
                # 计算执行时间
                cycle_time = time.time() - cycle_start_time
                
                # 睡眠到下一个周期
                sleep_time = self.config.update_cycle - cycle_time
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(
                        f"Update cycle time ({cycle_time:.4f}s) exceeds cycle time ({self.config.update_cycle}s)"
                    )
            except Exception as e:
                logger.error(f"Error in update loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.update_cycle)
    
    async def _pubsub_loop(self) -> None:
        """Pub/Sub 监听循环（接收数据更新通知）"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(self.config.pubsub_channel)
        
        logger.info(f"Subscribed to Redis Pub/Sub channel: {self.config.pubsub_channel}")
        
        try:
            while self._running:
                try:
                    # 接收消息（非阻塞）
                    message = pubsub.get_message(timeout=0.1)
                    
                    if message and message["type"] == "message":
                        # 收到更新通知，立即从 Redis 读取最新数据
                        redis_key = f"{self.REDIS_KEY_PREFIX}:current"
                        json_data = self.redis_client.get(redis_key)
                        
                        if json_data:
                            try:
                                data = json.loads(json_data)
                                params = data.get("params", {})
                                
                                # 更新 OPCUA 节点
                                await self._update_nodes(params)
                                
                                logger.debug(f"Updated nodes from Pub/Sub notification")
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON data from Redis: {e}")
                    
                    await asyncio.sleep(0.01)  # 短暂休眠，避免 CPU 占用过高
                except Exception as e:
                    logger.error(f"Error in pubsub loop: {e}", exc_info=True)
                    await asyncio.sleep(0.1)
        finally:
            pubsub.close()
            logger.info("Pub/Sub connection closed")
    
    async def _run_server(self) -> None:
        """运行 OPCUA Server"""
        try:
            # 启动服务器
            await self.server.start()
            logger.info(f"OPCUA Server started at {self.config.server_url}")
            
            # 启动更新任务
            self._update_task = asyncio.create_task(self._update_loop())
            
            # 启动 Pub/Sub 任务
            self._pubsub_task = asyncio.create_task(self._pubsub_loop())
            
            # 等待服务器运行
            try:
                while self._running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("Server tasks cancelled")
        except Exception as e:
            logger.error(f"Error running OPCUA Server: {e}", exc_info=True)
            raise
        finally:
            # 取消任务
            if self._update_task and not self._update_task.done():
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass
            
            if self._pubsub_task and not self._pubsub_task.done():
                self._pubsub_task.cancel()
                try:
                    await self._pubsub_task
                except asyncio.CancelledError:
                    pass
            
            # 停止服务器
            if self.server:
                await self.server.stop()
                logger.info("OPCUA Server stopped")
    
    def start(self) -> None:
        """启动 OPCUA Server（在新的事件循环中运行）"""
        if self._running:
            logger.warning("OPCUA Server is already running")
            return
        
        self._running = True
        
        # 创建新的事件循环（在新线程中）
        def run_in_thread():
            self._asyncio_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._asyncio_loop)
            
            try:
                # 初始化服务器
                self._asyncio_loop.run_until_complete(self._init_server())
                
                # 运行服务器
                self._asyncio_loop.run_until_complete(self._run_server())
            except Exception as e:
                logger.error(f"Error in OPCUA Server thread: {e}", exc_info=True)
            finally:
                self._asyncio_loop.close()
        
        # 启动线程
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        
        logger.info("OPCUA Server started in background thread")
    
    def stop(self) -> None:
        """停止 OPCUA Server"""
        if not self._running:
            logger.warning("OPCUA Server is not running")
            return
        
        self._running = False
        
        # 停止服务器（通过设置标志，让事件循环自然退出）
        logger.info("Stopping OPCUA Server...")
    
    def close(self) -> None:
        """关闭 OPCUA Server 和 Redis 连接"""
        self.stop()
        
        # 关闭 Redis 连接
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")

