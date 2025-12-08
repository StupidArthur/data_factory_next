"""
导出模板管理器

负责加载和管理导出模板配置。
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml

from utils.logger import get_logger


logger = get_logger()

# 模板配置目录（相对于模块目录）
TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"

# 默认描述（用于双行标题的第二行）
DEFAULT_TIME_DESCRIPTION = "时间戳"
DEFAULT_PARAM_DESCRIPTION = "某工业数据"


@dataclass
class ExportTemplate:
    """
    导出模板配置
    
    注意：
    - columns 和 column_descriptions 由当前运行的组态决定，不在模板中配置
    - filter_sampled_only 永远为 True，只导出采样周期的数据
    
    Attributes:
        name: 模板名称（如 moban_1, moban_2）
        time_column_name: 时间列名称（可以是任意字符串，如 "timeStamp"、"Timestamp"、"时间" 等）
        time_format: 时间格式字符串（如 "%Y/%m/%d %H:%M:%S" 或 "%Y-%m-%d %H:%M:%S"）
        header_rows: 标题行数（1 或 2）
        uppercase_column_names: 是否将位号名转换为全大写，默认 True
    """
    
    name: str
    time_column_name: str = "timeStamp"
    time_format: str = "%Y/%m/%d %H:%M:%S"
    header_rows: int = 1
    uppercase_column_names: bool = True
    
    def __post_init__(self) -> None:
        """验证配置有效性"""
        if self.header_rows not in [1, 2]:
            raise ValueError(f"header_rows must be 1 or 2, got {self.header_rows}")


class TemplateManager:
    """
    模板管理器
    
    负责加载和管理导出模板配置。
    """
    
    def __init__(self, templates_dir: Optional[pathlib.Path] = None) -> None:
        """
        初始化模板管理器
        
        Args:
            templates_dir: 模板配置目录，如果为 None 则使用默认目录
        """
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._templates: Dict[str, ExportTemplate] = {}
        
        # 确保模板目录存在
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("TemplateManager initialized: templates_dir=%s", self.templates_dir)
    
    def load_template(self, name: str) -> ExportTemplate:
        """
        加载模板配置
        
        Args:
            name: 模板名称（如 moban_1, moban_2）
            
        Returns:
            导出模板配置对象
            
        Raises:
            FileNotFoundError: 如果模板文件不存在
            ValueError: 如果模板配置格式错误
        """
        # 如果已加载，直接返回
        if name in self._templates:
            return self._templates[name]
        
        # 加载模板文件
        template_path = self.templates_dir / f"{name}.yaml"
        if not template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
        
        try:
            with template_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            # 解析模板配置
            template = self._parse_template(name, data)
            
            # 缓存模板
            self._templates[name] = template
            
            logger.info("模板加载成功: name=%s, header_rows=%d", name, template.header_rows)
            return template
            
        except Exception as e:
            logger.error("加载模板失败: name=%s, error=%s", name, e, exc_info=True)
            raise ValueError(f"加载模板失败: {name}, 错误: {e}") from e
    
    def _parse_template(self, name: str, data: Dict) -> ExportTemplate:
        """
        解析模板配置数据
        
        Args:
            name: 模板名称
            data: YAML 解析后的字典
            
        Returns:
            导出模板配置对象
        """
        time_column_name = data.get("time_column_name", "timeStamp")
        time_format = data.get("time_format", "%Y/%m/%d %H:%M:%S")
        header_rows = data.get("header_rows", 1)
        uppercase_column_names = data.get("uppercase_column_names", True)
        
        # 忽略旧配置项（向后兼容，但不使用）
        if "columns" in data:
            logger.warning("模板配置中的 'columns' 将被忽略，列由当前运行的组态决定")
        if "column_descriptions" in data:
            logger.warning("模板配置中的 'column_descriptions' 将被忽略")
        if "filter_sampled_only" in data:
            logger.warning("模板配置中的 'filter_sampled_only' 将被忽略，永远只导出采样周期的数据")
        
        return ExportTemplate(
            name=name,
            time_column_name=time_column_name,
            time_format=time_format,
            header_rows=header_rows,
            uppercase_column_names=uppercase_column_names,
        )
    
    def list_templates(self) -> List[str]:
        """
        列出所有可用的模板名称
        
        Returns:
            模板名称列表
        """
        if not self.templates_dir.exists():
            return []
        
        templates = []
        for file_path in self.templates_dir.glob("*.yaml"):
            template_name = file_path.stem
            templates.append(template_name)
        
        return sorted(templates)
    
    def template_exists(self, name: str) -> bool:
        """
        检查模板是否存在
        
        Args:
            name: 模板名称
            
        Returns:
            如果模板存在返回 True，否则返回 False
        """
        template_path = self.templates_dir / f"{name}.yaml"
        return template_path.exists()

