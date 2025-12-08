"""
CSV 导出器

负责将快照数据导出为 CSV 格式。
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from utils.logger import get_logger

from .template_manager import ExportTemplate, DEFAULT_TIME_DESCRIPTION, DEFAULT_PARAM_DESCRIPTION


logger = get_logger()

# 元数据字段（不导出为数据列）
METADATA_FIELDS = {"cycle_count", "need_sample", "time_str", "sim_time", "exec_ratio"}


class CSVExporter:
    """
    CSV 导出器
    
    支持单行标题和双行标题格式。
    """
    
    def __init__(self, template: ExportTemplate, sample_interval: Optional[float] = None) -> None:
        """
        初始化 CSV 导出器
        
        Args:
            template: 导出模板配置
            sample_interval: 采样间隔（秒），用于计算导出时间间隔
        """
        self.template = template
        self.sample_interval = sample_interval or 1.0  # 默认 1 秒
        
        logger.info(
            "CSVExporter initialized: template=%s, columns=%d, header_rows=%d, sample_interval=%.3f",
            template.name,
            len(template.columns),
            template.header_rows,
            self.sample_interval,
        )
    
    def export(
        self,
        snapshots: List[Dict[str, Any]],
        output_path: str | Path,
        start_time: Optional[float] = None,
    ) -> None:
        """
        导出快照数据到 CSV 文件
        
        Args:
            snapshots: 快照数据列表
            output_path: 输出文件路径
            start_time: 起始时间（时间戳），用于计算相对时间（当前未使用，保留用于未来扩展）
        """
        output_path = Path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 过滤数据（如果需要）
        filtered_snapshots = self._filter_snapshots(snapshots)
        
        if not filtered_snapshots:
            logger.warning("没有数据需要导出")
            return
        
        # 确定要导出的列
        columns = self._determine_columns(filtered_snapshots[0])
        
        # 写入 CSV 文件
        try:
            with output_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # 写入标题行
                self._write_header(writer, columns)
                
                # 写入数据行
                self._write_data_rows(writer, filtered_snapshots, columns)
            
            logger.info(
                "CSV 导出成功: 文件=%s, 行数=%d, 列数=%d",
                output_path,
                len(filtered_snapshots) + self.template.header_rows,
                len(columns) + 1,  # +1 是时间列
            )
        except Exception as e:
            logger.error("CSV 导出失败: 文件=%s, 错误=%s", output_path, e, exc_info=True)
            raise
    
    def _filter_snapshots(self, snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤快照数据
        
        Args:
            snapshots: 原始快照列表
            
        Returns:
            过滤后的快照列表
        """
        if self.template.filter_sampled_only:
            return [s for s in snapshots if s.get("need_sample", False)]
        return snapshots
    
    def _determine_columns(self, sample_snapshot: Dict[str, Any]) -> List[str]:
        """
        确定要导出的列
        
        Args:
            sample_snapshot: 示例快照（用于获取所有可用的位号名）
            
        Returns:
            要导出的列名列表（不包括时间列）
        """
        if self.template.columns:
            # 使用配置的列列表
            # 验证列是否存在
            available_keys = set(sample_snapshot.keys()) - METADATA_FIELDS
            columns = []
            for col in self.template.columns:
                if col in available_keys:
                    columns.append(col)
                else:
                    logger.warning("位号不存在，跳过: %s", col)
            return columns
        else:
            # 使用快照中的所有变量（排除元数据）
            columns = [k for k in sample_snapshot.keys() if k not in METADATA_FIELDS]
            # 按原始顺序排序（Python 3.7+ 字典保持插入顺序）
            return columns
    
    def _write_header(self, writer: csv.writer, columns: List[str]) -> None:
        """
        写入标题行
        
        Args:
            writer: CSV writer 对象
            columns: 要导出的列名列表
        """
        # 第一行标题
        header_row = [self.template.time_column_name] + columns
        writer.writerow(header_row)
        
        # 第二行描述（如果需要）
        if self.template.header_rows == 2:
            description_row = [DEFAULT_TIME_DESCRIPTION]
            for i, col in enumerate(columns):
                desc = self.template.get_column_description(i)
                description_row.append(desc)
            writer.writerow(description_row)
    
    def _write_data_rows(
        self,
        writer: csv.writer,
        snapshots: List[Dict[str, Any]],
        columns: List[str],
    ) -> None:
        """
        写入数据行
        
        Args:
            writer: CSV writer 对象
            snapshots: 快照数据列表
            columns: 要导出的列名列表
        """
        for snapshot in snapshots:
            # 从快照中获取 sim_time 并重新格式化
            sim_time = snapshot.get("sim_time", 0.0)
            time_str = self._format_time(sim_time)
            
            # 构建数据行
            row = [time_str]
            for col in columns:
                value = snapshot.get(col, "")
                # 转换为字符串，处理 None
                if value is None:
                    row.append("")
                else:
                    row.append(str(value))
            
            writer.writerow(row)
    
    def _format_time(self, timestamp: float) -> str:
        """
        格式化时间戳
        
        Args:
            timestamp: 时间戳（秒）
            
        Returns:
            格式化后的时间字符串
        """
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime(self.template.time_format)

