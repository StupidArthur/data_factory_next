"""
实例类型注册表

本模块只负责「类型注册」，不承载具体程序逻辑：
- InstanceRegistry：统一管理 {类型字符串 -> Python 类} 的映射。

后续真正的 PID、Tank 等实现会放在独立的 programs 包中，
通过 InstanceRegistry 进行注册。

注意：BaseProgram 基类已移至 programs.base 模块。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

# 导入 BaseProgram 用于类型提示（延迟导入避免循环依赖）
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from data_next.programs.base import BaseProgram

P = TypeVar("P", bound="BaseProgram")


class InstanceRegistry:
    """
    实例类型注册表。

    - algorithms：控制算法（PID 等）
    - models：物理模型（水箱、阀门等）
    - functions：无状态函数（abs、sqrt 等）

    所有注册/获取都通过类方法完成，便于在不同模块中统一使用。

    注意：算法和模型都继承自 BaseProgram，但为了保持向后兼容，
    仍然使用 register_algorithm 和 register_model 分别注册。
    """

    _algorithms: Dict[str, Type[Any]] = {}
    _models: Dict[str, Type[Any]] = {}
    _functions: Dict[str, Callable[..., Any]] = {}

    # ---- 算法注册/获取 -------------------------------------------------
    @classmethod
    def register_algorithm(cls, name: str, algorithm_class: Type[P]) -> None:
        """
        注册算法类型。

        Args:
            name: 类型名称（不区分大小写），例如 "PID"。
            algorithm_class: 继承自 BaseProgram 的类。
        """
        cls._algorithms[name.upper()] = algorithm_class

    @classmethod
    def get_algorithm(cls, name: str) -> Optional[Type[Any]]:
        """根据类型名称获取算法类，找不到时返回 None。"""
        return cls._algorithms.get(name.upper())

    # ---- 模型注册/获取 -------------------------------------------------
    @classmethod
    def register_model(cls, name: str, model_class: Type[P]) -> None:
        """
        注册模型类型。

        Args:
            name: 类型名称（不区分大小写），例如 "CYLINDRICAL_TANK"。
            model_class: 继承自 BaseProgram 的类。
        """
        cls._models[name.upper()] = model_class

    @classmethod
    def get_model(cls, name: str) -> Optional[Type[Any]]:
        """根据类型名称获取模型类，找不到时返回 None。"""
        return cls._models.get(name.upper())

    # ---- 无状态函数注册/获取 -------------------------------------------
    @classmethod
    def register_function(cls, name: str, func: Callable[..., Any]) -> None:
        """
        注册无状态函数。

        这些函数可以直接在 Variable 表达式中调用，例如 abs、sqrt 等。
        """
        cls._functions[name] = func

    @classmethod
    def get_function(cls, name: str) -> Optional[Callable[..., Any]]:
        """根据名称获取无状态函数，找不到时返回 None。"""
        return cls._functions.get(name)

    @classmethod
    def list_algorithms(cls) -> List[str]:
        """返回已注册的算法类型名称列表。"""
        return sorted(cls._algorithms.keys())

    @classmethod
    def list_models(cls) -> List[str]:
        """返回已注册的模型类型名称列表。"""
        return sorted(cls._models.keys())

    @classmethod
    def list_functions(cls) -> List[str]:
        """返回已注册的无状态函数名称列表。"""
        return sorted(cls._functions.keys())


