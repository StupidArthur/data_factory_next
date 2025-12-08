"""
文档获取辅助模块

提供统一的接口，从 programs 和 functions 获取算法和函数的文档信息。
用于网页展示，避免在前端硬编码。
"""

from typing import Dict, List, Optional, Any
from core.instance import InstanceRegistry
from functions.function_docs import get_function_doc_metadata


class ProgramDocInfo:
    """程序文档信息"""
    
    def __init__(self, name: str, chinese_name: str, doc: str, params_table: str):
        """
        初始化程序文档信息。
        
        Args:
            name: 英文名称
            chinese_name: 中文名称
            doc: 详细文档（markdown格式）
            params_table: 参数列表表格（markdown格式）
        """
        self.name = name
        self.chinese_name = chinese_name
        self.doc = doc
        self.params_table = params_table
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式，便于JSON序列化"""
        return {
            "name": self.name,
            "chinese_name": self.chinese_name,
            "doc": self.doc,
            "params_table": self.params_table
        }


class FunctionDocInfo:
    """函数文档信息"""
    
    def __init__(self, name: str, chinese_name: str, doc: str, params_table: str):
        """
        初始化函数文档信息。
        
        Args:
            name: 函数名称
            chinese_name: 中文名称
            doc: 详细文档（markdown格式）
            params_table: 参数列表表格（markdown格式）
        """
        self.name = name
        self.chinese_name = chinese_name
        self.doc = doc
        self.params_table = params_table
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式，便于JSON序列化"""
        return {
            "name": self.name,
            "chinese_name": self.chinese_name,
            "doc": self.doc,
            "params_table": self.params_table
        }


class DocHelper:
    """
    文档获取辅助类
    
    提供统一的接口，从 programs 和 functions 获取文档信息。
    """
    
    @staticmethod
    def get_program_list() -> List[str]:
        """
        获取所有已注册的程序（算法和模型）名称列表。
        
        Returns:
            程序名称列表（大写格式，如 ["PID", "SINE_WAVE"]）
        """
        algorithms = InstanceRegistry.list_algorithms()
        models = InstanceRegistry.list_models()
        # 合并并去重
        all_programs = sorted(set(algorithms + models))
        return all_programs
    
    @staticmethod
    def get_function_list() -> List[str]:
        """
        获取所有已注册的函数名称列表。
        
        Returns:
            函数名称列表（如 ["abs", "sqrt", "sin"]）
        """
        return InstanceRegistry.list_functions()
    
    @staticmethod
    def get_program_doc(program_name: str) -> Optional[ProgramDocInfo]:
        """
        获取指定程序的文档信息。
        
        Args:
            program_name: 程序名称（不区分大小写，如 "PID", "sine_wave"）
        
        Returns:
            ProgramDocInfo 对象，如果程序不存在或没有文档信息则返回 None
        """
        # 先尝试作为算法查找
        program_class = InstanceRegistry.get_algorithm(program_name)
        if not program_class:
            # 再尝试作为模型查找
            program_class = InstanceRegistry.get_model(program_name)
        
        if not program_class:
            return None
        
        # 检查是否有文档属性
        name = getattr(program_class, "name", "")
        chinese_name = getattr(program_class, "chinese_name", "")
        doc = getattr(program_class, "doc", "")
        params_table = getattr(program_class, "params_table", "")
        
        # 如果没有任何文档信息，返回 None
        if not name and not chinese_name:
            return None
        
        return ProgramDocInfo(
            name=name or program_name.lower(),
            chinese_name=chinese_name or program_name,
            doc=doc,
            params_table=params_table
        )
    
    @staticmethod
    def get_function_doc(function_name: str) -> Optional[FunctionDocInfo]:
        """
        获取指定函数的文档信息。
        
        Args:
            function_name: 函数名称（如 "abs", "sqrt"）
        
        Returns:
            FunctionDocInfo 对象，如果函数不存在或没有文档信息则返回 None
        """
        func = InstanceRegistry.get_function(function_name)
        if not func:
            return None
        
        # 先尝试从函数对象的 __doc_metadata__ 属性获取（适用于自定义函数）
        doc_metadata = getattr(func, "__doc_metadata__", None)
        
        # 如果函数对象上没有，尝试从全局字典中获取（适用于内置函数）
        if not doc_metadata:
            doc_metadata = get_function_doc_metadata(function_name)
        
        if doc_metadata:
            # 函数有文档元数据
            return FunctionDocInfo(
                name=doc_metadata.get("name", function_name),
                chinese_name=doc_metadata.get("chinese_name", function_name),
                doc=doc_metadata.get("doc", ""),
                params_table=doc_metadata.get("params_table", "")
            )
        
        # 如果没有文档元数据，返回 None（要求必须提供）
        return None
    
    @staticmethod
    def get_all_program_docs() -> Dict[str, ProgramDocInfo]:
        """
        获取所有程序的文档信息。
        
        Returns:
            字典，键为程序名称（大写），值为 ProgramDocInfo 对象
        """
        result = {}
        program_list = DocHelper.get_program_list()
        for program_name in program_list:
            doc_info = DocHelper.get_program_doc(program_name)
            if doc_info:
                result[program_name] = doc_info
        return result
    
    @staticmethod
    def get_all_function_docs() -> Dict[str, FunctionDocInfo]:
        """
        获取所有函数的文档信息。
        
        Returns:
            字典，键为函数名称，值为 FunctionDocInfo 对象
        """
        result = {}
        function_list = DocHelper.get_function_list()
        for function_name in function_list:
            doc_info = DocHelper.get_function_doc(function_name)
            if doc_info:
                result[function_name] = doc_info
        return result

