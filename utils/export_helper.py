"""
导出辅助函数

提供便捷的导出功能。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

from export_templates import TemplateManager, CSVExporter
from utils.logger import get_logger


logger = get_logger()


def export_to_csv(
    snapshots: List[Dict[str, Any]],
    template_name: str,
    output_path: str | Path,
    sample_interval: float = 1.0,
) -> None:
    """
    使用指定模板导出数据到 CSV 文件
    
    Args:
        snapshots: 快照数据列表
        template_name: 模板名称（如 moban_1, moban_2）
        output_path: 输出文件路径
        sample_interval: 采样间隔（秒），用于文档说明（实际时间从 sim_time 重新生成）
    """
    # 加载模板
    template_manager = TemplateManager()
    template = template_manager.load_template(template_name)
    
    # 创建导出器并导出
    exporter = CSVExporter(template, sample_interval=sample_interval)
    exporter.export(snapshots, output_path)
    
    logger.info("导出完成: 模板=%s, 文件=%s", template_name, output_path)

