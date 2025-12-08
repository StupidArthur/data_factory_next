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

# 默认描述
DEFAULT_TIME_DESCRIPTION = "时间戳"
DEFAULT_PARAM_DESCRIPTION = "某工业数据"


@dataclass
class ExportTemplate:
    """
    导出模板配置
    
    Attributes:
        name: 模板名称（如 moban_1, moban_2）
        time_column_name: 时间列名称（严格区分大小写，如 timeStamp 或 Timestamp）
        time_format: 时间格式字符串（如 "%Y/%m/%d %H:%M:%S" 或 "%Y-%m-%d %H:%M:%S"）
        columns: 要导出的位号名列表（按顺序）
        column_descriptions: 位号描述列表（与 columns 对应，空字符串则使用默认描述）
        header_rows: 标题行数（1 或 2）
        filter_sampled_only: 是否只导出 need_sample=True 的数据
    """
    
    name: str
    time_column_name: str = "timeStamp"
    time_format: str = "%Y/%m/%d %H:%M:%S"
    columns: List[str] = field(default_factory=list)
    column_descriptions: List[str] = field(default_factory=list)
    header_rows: int = 1
    filter_sampled_only: bool = False
    
    def __post_init__(self) -> None:
        """验证配置有效性"""
        if self.header_rows not in [1, 2]:
            raise ValueError(f"header_rows must be 1 or 2, got {self.header_rows}")
        
        if self.header_rows == 2 and len(self.column_descriptions) != len(self.columns):
            # 如果配置了双行标题，但描述数量不匹配，自动补齐
            if len(self.column_descriptions) < len(self.columns):
                # 补齐默认描述
                self.column_descriptions.extend(
                    [""] * (len(self.columns) - len(self.column_descriptions))
                )
        
        # 确保时间列名称严格区分大小写
        if self.time_column_name not in ["timeStamp", "Timestamp"]:
            logger.warning(
                "time_column_name should be 'timeStamp' or 'Timestamp', got '%s'",
                self.time_column_name
            )
    
    def get_column_description(self, index: int) -> str:
        """
        获取指定索引的列描述
        
        Args:
            index: 列索引（不包括时间列）
            
        Returns:
            列描述，如果为空字符串则返回默认描述
        """
        if index >= len(self.column_descriptions):
            return DEFAULT_PARAM_DESCRIPTION
        
        desc = self.column_descriptions[index]
        return desc if desc else DEFAULT_PARAM_DESCRIPTION


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
            
            logger.info("模板加载成功: name=%s, columns=%d", name, len(template.columns))
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
        columns = data.get("columns", [])
        column_descriptions = data.get("column_descriptions", [])
        header_rows = data.get("header_rows", 1)
        filter_sampled_only = data.get("filter_sampled_only", False)
        
        # 验证 columns 是列表
        if not isinstance(columns, list):
            raise ValueError(f"columns must be a list, got {type(columns)}")
        
        # 验证 column_descriptions 是列表
        if not isinstance(column_descriptions, list):
            raise ValueError(f"column_descriptions must be a list, got {type(column_descriptions)}")
        
        return ExportTemplate(
            name=name,
            time_column_name=time_column_name,
            time_format=time_format,
            columns=columns,
            column_descriptions=column_descriptions,
            header_rows=header_rows,
            filter_sampled_only=filter_sampled_only,
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

