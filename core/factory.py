"""
实例工厂

负责：
- 根据 ProgramItem 创建算法/模型实例
- 管理实例的生命周期
"""

from __future__ import annotations

from typing import Any, Dict

from .instance import InstanceRegistry
from .parser import ProgramItem


class InstanceFactory:
    """
    实例工厂。

    根据 ProgramItem 的类型和 init_args 创建对应的程序实例（算法/模型）。
    """

    def __init__(self, cycle_time: float) -> None:
        """
        初始化工厂。

        Args:
            cycle_time: 控制器周期（秒），会注入到所有创建的实例中
        """
        self.cycle_time = cycle_time
        self._instances: Dict[str, Any] = {}

    def create_instance(self, item: ProgramItem) -> Any:
        """
        创建实例。

        Args:
            item: 程序项配置

        Returns:
            创建的实例对象（继承自 BaseProgram）

        Raises:
            ValueError: 如果类型未注册或类型为 Variable
        """
        if item.name in self._instances:
            return self._instances[item.name]

        if item.type.upper() == "VARIABLE":
            raise ValueError(f"Variable 类型不需要创建实例: {item.name}")

        # 查找算法或模型类
        algorithm_class = InstanceRegistry.get_algorithm(item.type)
        model_class = InstanceRegistry.get_model(item.type)

        instance: Any = None

        if algorithm_class:
            instance = algorithm_class(cycle_time=self.cycle_time, **item.init_args)
        elif model_class:
            instance = model_class(cycle_time=self.cycle_time, **item.init_args)
        else:
            raise ValueError(
                f"未知的类型: {item.type} (name={item.name})。"
                f"已注册的算法: {InstanceRegistry.list_algorithms()}, "
                f"已注册的模型: {InstanceRegistry.list_models()}"
            )

        self._instances[item.name] = instance
        return instance

    def get_instance(self, name: str) -> Any | None:
        """
        获取已创建的实例。

        Args:
            name: 实例名称

        Returns:
            实例对象，如果不存在则返回 None
        """
        return self._instances.get(name)

    def list_instances(self) -> list[str]:
        """返回所有已创建的实例名称列表。"""
        return sorted(self._instances.keys())

