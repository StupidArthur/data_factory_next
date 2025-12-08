"""
历史数据存储模块（DuckDB）

负责将历史数据存储到 DuckDB，并提供查询接口。
"""

from __future__ import annotations

import duckdb
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logger import get_logger


logger = get_logger()

# 常量定义
BATCH_INSERT_SIZE = 100  # 批量插入缓冲区大小（每N条记录批量插入一次）


@dataclass
class HistoryConfig:
    """
    历史数据配置
    
    Attributes:
        db_path: DuckDB 文件路径（可配置）
        stored_variables: 需要存储的变量列表（None=全部存储）
    """
    db_path: str = "engine_history.duckdb"
    stored_variables: Optional[List[str]] = None


class HistoryStorage:
    """
    历史数据存储管理器（DuckDB）
    
    功能：
    - 按采样周期存储历史数据（使用 Clock 的 need_sample）
    - 提供历史数据查询接口
    - 提供采样查询接口（按时间间隔采样）
    - 提供统计查询接口
    - 提供最新值查询接口
    """
    
    def __init__(self, config: HistoryConfig):
        """
        初始化历史数据存储管理器
        
        Args:
            config: 历史数据配置
        """
        self.config = config
        
        # 确保数据库目录存在
        db_path = Path(config.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化 DuckDB 连接
        self._conn = duckdb.connect(str(db_path))
        
        # 创建表结构
        self._create_table()
        
        # 批量插入缓冲区
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = BATCH_INSERT_SIZE
        
        logger.info(
            "HistoryStorage initialized: db_path=%s, stored_variables=%s",
            config.db_path,
            "all" if config.stored_variables is None else len(config.stored_variables),
        )
    
    def _create_table(self) -> None:
        """创建数据表结构"""
        try:
            # 创建表（如果不存在）
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS data_records (
                    id BIGINT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    param_name VARCHAR NOT NULL,
                    param_value DOUBLE NOT NULL,
                    instance_name VARCHAR NOT NULL,
                    param_type VARCHAR,
                    cycle_count INTEGER,
                    sim_time DOUBLE
                )
            """)
            
            # 创建索引（如果不存在）
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp_param 
                ON data_records(timestamp, param_name)
            """)
            
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON data_records(timestamp)
            """)
            
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_param_name 
                ON data_records(param_name)
            """)
            
            logger.info("Database table and indexes created")
        except Exception as e:
            logger.error(f"Failed to create table: {e}", exc_info=True)
            raise
    
    def store_snapshot(
        self,
        snapshot: Dict[str, Any],
        timestamp: datetime,
        need_sample: bool,
    ) -> None:
        """
        存储快照（只在 need_sample=True 时存储）
        
        Args:
            snapshot: 快照数据字典
            timestamp: 时间戳（datetime 对象）
            need_sample: 是否需要采样（来自 Clock.step() 的返回值）
        """
        if not need_sample:
            # 不需要采样，跳过存储
            return
        
        try:
            # 获取时间戳和周期信息
            sim_time = snapshot.get("sim_time", 0.0)
            cycle_count = snapshot.get("cycle_count", 0)
            
            # 准备记录
            records = []
            for param_name, param_value in snapshot.items():
                # 跳过元数据字段
                if param_name in ["cycle_count", "need_sample", "time_str", "sim_time", "exec_ratio"]:
                    continue
                
                # 如果指定了存储变量列表，只存储指定的变量
                if self.config.stored_variables is not None:
                    if param_name not in self.config.stored_variables:
                        continue
                
                # 解析参数名：instance_name.param_name
                parts = param_name.split(".", 1)
                if len(parts) != 2:
                    instance_name = "unknown"
                    param = param_name
                else:
                    instance_name, param = parts
                
                # 判断参数类型（简单判断：如果包含算法名，可能是算法参数）
                param_type = "variable"
                if any(alg in instance_name.lower() for alg in ["pid", "controller", "algorithm"]):
                    param_type = "algorithm"
                elif any(model in instance_name.lower() for model in ["tank", "valve", "model"]):
                    param_type = "model"
                
                # 只存储数值类型
                if isinstance(param_value, (int, float)):
                    record = {
                        "timestamp": timestamp,
                        "param_name": param_name,
                        "param_value": float(param_value),
                        "instance_name": instance_name,
                        "param_type": param_type,
                        "cycle_count": cycle_count,
                        "sim_time": sim_time,
                    }
                    records.append(record)
            
            # 添加到缓冲区
            self._buffer.extend(records)
            
            # 如果缓冲区达到阈值，批量插入
            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()
            
        except Exception as e:
            logger.error(f"Failed to store snapshot: {e}", exc_info=True)
    
    def _flush_buffer(self) -> None:
        """刷新缓冲区，批量插入数据"""
        if not self._buffer:
            return
        
        try:
            # 获取下一个 ID
            result = self._conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM data_records").fetchone()
            start_id = result[0] if result else 1
            
            # 批量插入
            for i, record in enumerate(self._buffer):
                record_id = start_id + i
                self._conn.execute("""
                    INSERT INTO data_records 
                    (id, timestamp, param_name, param_value, instance_name, param_type, cycle_count, sim_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    record["timestamp"],
                    record["param_name"],
                    record["param_value"],
                    record["instance_name"],
                    record["param_type"],
                    record["cycle_count"],
                    record["sim_time"],
                ))
            
            # 提交事务
            self._conn.commit()
            
            logger.debug("批量插入成功: %d 条记录", len(self._buffer))
            
            # 清空缓冲区
            self._buffer.clear()
        except Exception as e:
            logger.warning(
                "批量插入失败: 记录数=%d, 错误=%s, 已回滚事务",
                len(self._buffer),
                e,
                exc_info=True,
            )
            self._conn.rollback()
            self._buffer.clear()
    
    def query_history(
        self,
        param_name: Optional[str] = None,
        instance_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        查询历史数据
        
        Args:
            param_name: 参数名称（可选），如 "tank1.level"
            instance_name: 实例名称（可选），如 "tank1"
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            limit: 返回记录数限制，默认 1000
        
        Returns:
            历史数据记录列表
        """
        try:
            # 构建查询条件
            conditions = []
            params = []
            
            if param_name:
                conditions.append("param_name = ?")
                params.append(param_name)
            
            if instance_name:
                conditions.append("instance_name = ?")
                params.append(instance_name)
            
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            
            # 构建 SQL
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"""
                SELECT id, timestamp, param_name, param_value, instance_name, param_type, cycle_count, sim_time
                FROM data_records
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            # 执行查询
            result = self._conn.execute(sql, params).fetchall()
            
            # 转换为字典列表
            records = []
            for row in result:
                records.append({
                    "id": row[0],
                    "timestamp": row[1].isoformat() if isinstance(row[1], datetime) else str(row[1]),
                    "param_name": row[2],
                    "param_value": row[3],
                    "instance_name": row[4],
                    "param_type": row[5],
                    "cycle_count": row[6],
                    "sim_time": row[7],
                })
            
            logger.debug(f"Query history returned {len(records)} records")
            return records
        except Exception as e:
            logger.error(f"Failed to query history: {e}", exc_info=True)
            return []
    
    def query_sampled(
        self,
        param_name: Optional[str] = None,
        instance_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sample_interval: Optional[float] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        采样查询（按时间间隔采样）
        
        Args:
            param_name: 参数名称（可选）
            instance_name: 实例名称（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            sample_interval: 采样间隔（秒），如果提供，会按时间间隔采样
            limit: 返回记录数限制，默认 1000
        
        Returns:
            采样后的历史数据记录列表
        """
        try:
            # 如果没有指定采样间隔，直接查询
            if sample_interval is None or sample_interval <= 0:
                return self.query_history(
                    param_name=param_name,
                    instance_name=instance_name,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                )
            
            # 构建查询条件（先获取所有符合条件的时间戳）
            conditions = []
            params = []
            
            if param_name:
                conditions.append("param_name = ?")
                params.append(param_name)
            
            if instance_name:
                conditions.append("instance_name = ?")
                params.append(instance_name)
            
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            
            # 获取所有符合条件的时间戳（去重，按时间排序）
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"""
                SELECT DISTINCT timestamp
                FROM data_records
                WHERE {where_clause}
                ORDER BY timestamp ASC
            """
            
            all_timestamps = self._conn.execute(sql, params).fetchall()
            
            # 采样时间戳
            sampled_timestamps = []
            last_sampled_time = None
            
            for row in all_timestamps:
                ts = row[0]
                if isinstance(ts, datetime):
                    ts_timestamp = ts.timestamp()
                else:
                    ts_timestamp = float(ts)
                
                if last_sampled_time is None:
                    sampled_timestamps.append(ts)
                    last_sampled_time = ts_timestamp
                else:
                    time_diff = ts_timestamp - last_sampled_time
                    if time_diff >= sample_interval:
                        sampled_timestamps.append(ts)
                        last_sampled_time = ts_timestamp
            
            if not sampled_timestamps:
                return []
            
            # 查询采样后的数据
            conditions.append("timestamp IN ({})".format(",".join(["?"] * len(sampled_timestamps))))
            params.extend(sampled_timestamps)
            
            where_clause = " AND ".join(conditions)
            sql = f"""
                SELECT id, timestamp, param_name, param_value, instance_name, param_type, cycle_count, sim_time
                FROM data_records
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            # 执行查询
            result = self._conn.execute(sql, params).fetchall()
            
            # 转换为字典列表
            records = []
            for row in result:
                records.append({
                    "id": row[0],
                    "timestamp": row[1].isoformat() if isinstance(row[1], datetime) else str(row[1]),
                    "param_name": row[2],
                    "param_value": row[3],
                    "instance_name": row[4],
                    "param_type": row[5],
                    "cycle_count": row[6],
                    "sim_time": row[7],
                })
            
            logger.debug(f"Query sampled returned {len(records)} records (from {len(sampled_timestamps)} timestamps)")
            return records
        except Exception as e:
            logger.error(f"Failed to query sampled: {e}", exc_info=True)
            return []
    
    def get_statistics(
        self,
        param_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            param_name: 参数名称，如 "tank1.level"
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
        
        Returns:
            统计信息字典，包含 count, min, max, avg, sum
        """
        try:
            # 构建查询条件
            conditions = ["param_name = ?"]
            params = [param_name]
            
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            
            # 构建 SQL
            where_clause = " AND ".join(conditions)
            sql = f"""
                SELECT 
                    COUNT(*) as count,
                    MIN(param_value) as min,
                    MAX(param_value) as max,
                    AVG(param_value) as avg,
                    SUM(param_value) as sum
                FROM data_records
                WHERE {where_clause}
            """
            
            # 执行查询
            result = self._conn.execute(sql, params).fetchone()
            
            if not result or result[0] == 0:
                return {
                    "param_name": param_name,
                    "count": 0,
                    "min": None,
                    "max": None,
                    "avg": None,
                    "sum": None,
                }
            
            return {
                "param_name": param_name,
                "count": result[0],
                "min": float(result[1]) if result[1] is not None else None,
                "max": float(result[2]) if result[2] is not None else None,
                "avg": float(result[3]) if result[3] is not None else None,
                "sum": float(result[4]) if result[4] is not None else None,
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}", exc_info=True)
            return {
                "param_name": param_name,
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
                "sum": None,
            }
    
    def get_latest_values(
        self,
        instance_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取最新值
        
        Args:
            instance_name: 实例名称（可选），如果提供则只返回该实例的参数
        
        Returns:
            参数字典，key 为参数名，value 为最新值
        """
        try:
            # 构建查询条件
            conditions = []
            params = []
            
            if instance_name:
                conditions.append("instance_name = ?")
                params.append(instance_name)
            
            # 使用子查询获取每个参数的最大时间戳
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"""
                SELECT param_name, param_value
                FROM data_records d1
                WHERE {where_clause}
                AND timestamp = (
                    SELECT MAX(timestamp)
                    FROM data_records d2
                    WHERE d2.param_name = d1.param_name
                    {f"AND d2.instance_name = ?" if instance_name else ""}
                )
            """
            
            if instance_name:
                params.append(instance_name)
            
            # 执行查询
            result = self._conn.execute(sql, params).fetchall()
            
            # 转换为字典
            latest_values = {}
            for row in result:
                latest_values[row[0]] = row[1]
            
            logger.debug(f"Get latest values returned {len(latest_values)} parameters")
            return latest_values
        except Exception as e:
            logger.error(f"Failed to get latest values: {e}", exc_info=True)
            return {}
    
    def close(self) -> None:
        """关闭数据库连接"""
        try:
            # 刷新缓冲区
            self._flush_buffer()
            
            # 关闭连接
            if self._conn:
                self._conn.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Failed to close database connection: {e}", exc_info=True)

