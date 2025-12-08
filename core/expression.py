"""
表达式节点（按周期执行）

支持 DSL 表达式的解析和执行：
- 四则混合运算、小括号
- 方法调用：instance.execute(...)
- 属性访问：instance.attribute
- 函数调用：abs(), sqrt() 等
- 历史数据访问：variable[-N] 或 instance.attribute[-N]
- 赋值表达式：variable = expression（用于 Variable 类型）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional

import ast

from .variable import VariableStore
from .instance import InstanceRegistry


class ExpressionError(Exception):
    """表达式执行相关错误。"""


@dataclass
class ExpressionConfig:
    """
    表达式节点配置。

    Attributes:
        name: 节点名称（变量名或实例名），如 "v1" 或 "pid1"。
        expression: 表达式字符串，例如：
                   - "pid1.execute(pv=tank1.level, sv=sin1.out)"
                   - "non_sense_3 = non_sense_1[-30] + 2 * non_sense_2"
    """

    name: str
    expression: str


class ExpressionEvaluator:
    """
    表达式求值器。

    支持：
    - 四则运算、括号
    - 方法调用（带关键字参数）
    - 属性访问
    - 函数调用
    - 历史数据访问（通过下标）
    - 赋值表达式
    """

    def __init__(
        self,
        vars_store: VariableStore,
        instances: Dict[str, Any],
    ) -> None:
        """
        初始化表达式求值器。

        Args:
            vars_store: 变量存储
            instances: 实例字典 {实例名: 实例对象}
        """
        self._vars = vars_store
        self._instances = instances

    def evaluate(self, expression: str) -> float:
        """
        执行表达式，返回数值结果。

        Args:
            expression: 表达式字符串

        Returns:
            计算结果（浮点数）
        """
        try:
            # 解析表达式
            tree = ast.parse(expression, mode="eval")
            
            # 转换AST：将直接使用实例名的情况转换为 .out 属性访问
            # 但只在 Name 节点上转换，不在 Attribute 节点上转换（避免重复转换）
            tree = self._transform_instance_names(tree)
            
            # 验证 AST
            self._validate_ast(tree.body)
            
            # 提取所有变量名（不在 instances 中的名称）
            variable_names = self._extract_variable_names(tree.body)
            
            # 构建执行环境
            env = self._build_env(variable_names)
            
            # 编译并执行
            compiled = compile(tree, filename="<expression>", mode="eval")
            value = eval(compiled, {"__builtins__": {}}, env)
            
            return float(value)
        except SyntaxError as exc:
            raise ExpressionError(f"表达式语法错误: {expression}, 错误: {exc}") from exc
        except NameError as exc:
            raise ExpressionError(f"表达式变量未定义: {expression}, 错误: {exc}") from exc
        except TypeError as exc:
            raise ExpressionError(f"表达式类型错误: {expression}, 错误: {exc}") from exc
        except ZeroDivisionError as exc:
            raise ExpressionError(f"表达式除零错误: {expression}, 错误: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ExpressionError(f"表达式执行失败: {expression}, 错误: {exc}") from exc

    def _transform_instance_names(self, tree: ast.AST) -> ast.AST:
        """
        转换AST：将直接使用实例名的情况转换为 .out 属性访问。
        
        例如：non_sense_1[-30] -> non_sense_1.out[-30]
              sqrt(non_sense_2) -> sqrt(non_sense_2.out)
        
        注意：只在以下情况下转换：
        - Name节点且名称在instances中
        - 且不是方法调用（如 instance.execute()）
        - 且不是属性访问（如 instance.attr）
        
        Args:
            tree: AST树
            
        Returns:
            转换后的AST树
        """
        class InstanceNameTransformer(ast.NodeTransformer):
            """
            AST 节点转换器：将直接使用实例名的情况转换为 .out 属性访问。
            
            转换规则：
            1. 如果遇到 Name 节点，且名称在 instances 中，且不是函数名，且不在属性访问中
               则转换为 Attribute 节点（instance_name.out）
            2. 如果遇到 Attribute 节点，标记 _in_attribute=True，避免重复转换
            3. 如果遇到 Call 节点（方法调用），不转换，但递归处理参数
            """
            def __init__(self, instances: Dict[str, Any]) -> None:
                self.instances = instances
                self._in_attribute = False  # 标记是否在属性访问中，避免重复转换
            
            def visit_Name(self, node: ast.Name) -> ast.AST:
                """
                处理 Name 节点（变量名或实例名）。
                
                转换逻辑：
                - 如果名称在 instances 中，且不是函数名，且不在属性访问中
                - 则转换为 instance_name.out 的 Attribute 节点
                """
                if node.id in self.instances and not self._in_attribute:
                    # 检查是否是函数名（函数名不需要转换）
                    func = InstanceRegistry.get_function(node.id)
                    if func is None:
                        # 转换为 instance_name.out
                        # 注意：需要设置 lineno 和 col_offset，否则 compile 会失败
                        new_name = ast.Name(id=node.id, ctx=ast.Load())
                        new_name.lineno = getattr(node, 'lineno', 1)
                        new_name.col_offset = getattr(node, 'col_offset', 0)
                        
                        new_attr = ast.Attribute(
                            value=new_name,
                            attr="out",
                            ctx=ast.Load()
                        )
                        new_attr.lineno = getattr(node, 'lineno', 1)
                        new_attr.col_offset = getattr(node, 'col_offset', 0)
                        return new_attr
                return node
            
            def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
                """
                处理 Attribute 节点（属性访问）。
                
                如果已经是属性访问（如 instance.attr），标记状态避免重复转换，
                然后递归处理子节点。
                """
                # 如果已经是属性访问，标记状态，然后递归处理
                # 如果 value 是 Name 且在 instances 中，说明已经是 instance.attr 的形式，不需要转换
                old_in_attribute = self._in_attribute
                self._in_attribute = True
                try:
                    # 递归处理子节点
                    self.generic_visit(node)
                    return node
                finally:
                    self._in_attribute = old_in_attribute
            
            def visit_Call(self, node: ast.Call) -> ast.AST:
                """
                处理 Call 节点（方法调用或函数调用）。
                
                方法调用（如 instance.execute()）不需要转换，
                但需要递归处理参数，因为参数中可能包含需要转换的实例名。
                """
                # 方法调用（如 instance.execute()）不需要转换
                # 但需要递归处理参数
                self.generic_visit(node)
                return node
        
        transformer = InstanceNameTransformer(self._instances)
        return transformer.visit(tree)
    
    def _extract_variable_names(self, node: ast.AST) -> set[str]:
        """
        提取表达式中的所有变量名（不在 instances 中的名称）。

        Args:
            node: AST 节点

        Returns:
            变量名集合
        """
        variable_names: set[str] = set()
        instances = self._instances

        class VariableNameVisitor(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                # 如果名称不在 instances 中，且不是函数名，则认为是变量
                if node.id not in instances:
                    # 检查是否是函数名
                    func = InstanceRegistry.get_function(node.id)
                    if func is None:
                        variable_names.add(node.id)

        visitor = VariableNameVisitor()
        visitor.visit(node)

        return variable_names

    def _build_env(self, variable_names: set[str]) -> Dict[str, Any]:
        """
        构造表达式执行环境。

        Args:
            variable_names: 变量名集合

        Returns:
            环境字典，包含：
            - 实例代理对象（支持属性访问和历史数据访问）
            - 无状态函数（从 InstanceRegistry 获取）
            - 变量访问器（支持历史数据访问）
        """
        env: Dict[str, Any] = {}

        # 添加实例代理（支持属性访问和历史数据访问）
        for instance_name, instance in self._instances.items():
            env[instance_name] = InstanceProxy(instance_name, instance, self._vars)

        # 添加无状态函数
        for func_name in InstanceRegistry.list_functions():
            func = InstanceRegistry.get_function(func_name)
            if func:
                env[func_name] = func

        # 添加变量访问器（支持历史数据访问）
        for var_name in variable_names:
            env[var_name] = VariableAccessor(var_name, self._vars)

        return env

    @staticmethod
    def _validate_ast(node: ast.AST) -> None:
        """
        验证 AST 节点是否允许。

        允许的节点类型：
        - Expression, BinOp, UnaryOp（运算）
        - Call（函数调用和方法调用，支持关键字参数）
        - Attribute（属性访问）
        - Subscript（历史数据访问）
        - Name, Constant, Num（名称、常量）
        - Assign（赋值表达式，用于 Variable 类型）
        """
        if isinstance(node, ast.Expression):
            ExpressionEvaluator._validate_ast(node.body)
        elif isinstance(node, ast.BinOp):
            ExpressionEvaluator._validate_ast(node.left)
            ExpressionEvaluator._validate_ast(node.right)
        elif isinstance(node, ast.UnaryOp):
            ExpressionEvaluator._validate_ast(node.operand)
        elif isinstance(node, ast.Call):
            # 允许函数调用和方法调用
            ExpressionEvaluator._validate_ast(node.func)
            for arg in node.args:
                ExpressionEvaluator._validate_ast(arg)
            # 允许关键字参数（用于方法调用）
            for keyword in node.keywords:
                ExpressionEvaluator._validate_ast(keyword.value)
        elif isinstance(node, ast.Attribute):
            # 允许属性访问
            ExpressionEvaluator._validate_ast(node.value)
        elif isinstance(node, ast.Subscript):
            # 允许历史数据访问
            ExpressionEvaluator._validate_ast(node.value)
            # slice 可能是 Index、Constant、UnaryOp 等
            if isinstance(node.slice, ast.Index):
                ExpressionEvaluator._validate_ast(node.slice.value)
            elif isinstance(node.slice, (ast.Constant, ast.Num)):
                pass  # 常量，允许
            elif isinstance(node.slice, ast.UnaryOp):
                ExpressionEvaluator._validate_ast(node.slice)
            else:
                ExpressionEvaluator._validate_ast(node.slice)
        elif isinstance(node, ast.Name):
            # 允许名称引用
            pass
        elif isinstance(node, ast.Constant):
            # 允许常量
            pass
        elif isinstance(node, ast.Num):  # 兼容旧版本
            pass
        elif isinstance(node, ast.Assign):
            # 允许赋值表达式（用于 Variable 类型）
            for target in node.targets:
                ExpressionEvaluator._validate_ast(target)
            ExpressionEvaluator._validate_ast(node.value)
        else:
            raise ExpressionError(f"不允许的 AST 节点类型: {type(node).__name__}")


class InstanceProxy:
    """
    实例代理对象。

    用于在表达式中访问实例属性和调用方法。
    支持：
    - instance.attribute（当前值）
    - instance.attribute[-N]（历史值）
    - instance.execute(...)（方法调用）
    """

    def __init__(self, instance_name: str, instance: Any, vars_store: VariableStore) -> None:
        """
        初始化实例代理。

        Args:
            instance_name: 实例名称（如 "pid1"）
            instance: 实例对象
            vars_store: 变量存储
        """
        self._instance_name = instance_name
        self._instance = instance
        self._vars = vars_store

    def __getattr__(self, name: str) -> AttributeProxy:
        """
        获取属性代理。

        例如：pid1.mv -> AttributeProxy("pid1", "mv", ...)
        """
        return AttributeProxy(self._instance_name, name, self._instance, self._vars)

    def execute(self, **kwargs: Any) -> None:
        """
        调用实例的 execute 方法。

        例如：pid1.execute(pv=tank1.level, sv=sin1.out)
        """
        self._instance.execute(**kwargs)


class AttributeProxy:
    """
    属性代理对象。

    支持：
    - 当前值访问：float(proxy) 或直接使用
    - 历史值访问：proxy[-N]
    """

    def __init__(
        self,
        instance_name: str,
        attr_name: str,
        instance: Any,
        vars_store: VariableStore,
    ) -> None:
        """
        初始化属性代理。

        Args:
            instance_name: 实例名称（如 "pid1"）
            attr_name: 属性名称（如 "mv"）
            instance: 实例对象
            vars_store: 变量存储
        """
        self._instance_name = instance_name
        self._attr_name = attr_name
        self._instance = instance
        self._vars = vars_store
        self._var_key = f"{instance_name}.{attr_name}"

    def __float__(self) -> float:
        """
        获取当前值（转换为浮点数）。

        优先从 VariableStore 获取（可能已更新），
        否则从实例属性获取。
        """
        # 优先从 VariableStore 获取
        value = self._vars.get(self._var_key)
        if value is not None:
            return float(value)
        # 否则从实例属性获取
        return float(getattr(self._instance, self._attr_name, 0.0))
    
    def __int__(self) -> int:
        """转换为整数。"""
        return int(float(self))
    
    def __complex__(self) -> complex:
        """转换为复数。"""
        return complex(float(self))

    def __getitem__(self, lag_steps: int) -> float:
        """
        获取历史值。

        Args:
            lag_steps: 滞后步数（负数，如 -30 表示 30 步之前）

        Returns:
            历史值
        """
        # 转换为正数
        if lag_steps < 0:
            lag_steps = -lag_steps
        return float(self._vars.get_with_lag(self._var_key, lag_steps, 0.0))

    # 数值运算支持
    def __add__(self, other: Any) -> float:
        return float(self) + float(other)

    def __radd__(self, other: Any) -> float:
        return float(other) + float(self)

    def __mul__(self, other: Any) -> float:
        return float(self) * float(other)

    def __rmul__(self, other: Any) -> float:
        return float(other) * float(self)

    def __sub__(self, other: Any) -> float:
        return float(self) - float(other)

    def __rsub__(self, other: Any) -> float:
        return float(other) - float(self)

    def __truediv__(self, other: Any) -> float:
        return float(self) / float(other)

    def __rtruediv__(self, other: Any) -> float:
        return float(other) / float(self)
    
    def __lt__(self, other: Any) -> bool:
        return float(self) < float(other)
    
    def __le__(self, other: Any) -> bool:
        return float(self) <= float(other)
    
    def __gt__(self, other: Any) -> bool:
        return float(self) > float(other)
    
    def __ge__(self, other: Any) -> bool:
        return float(self) >= float(other)
    
    def __eq__(self, other: Any) -> bool:
        return float(self) == float(other)
    
    def __ne__(self, other: Any) -> bool:
        return float(self) != float(other)

    def __repr__(self) -> str:
        """字符串表示（用于调试）。"""
        return f"<AttributeProxy {self._var_key}={float(self)}>"


class VariableAccessor:
    """
    变量访问器。

    支持：
    - 当前值访问：float(accessor)
    - 历史值访问：accessor[-N]
    """

    def __init__(self, var_name: str, vars_store: VariableStore) -> None:
        """
        初始化变量访问器。

        Args:
            var_name: 变量名称
            vars_store: 变量存储
        """
        self._var_name = var_name
        self._vars = vars_store

    def __float__(self) -> float:
        """获取当前值。"""
        return float(self._vars.get(self._var_name, 0.0))

    def __getitem__(self, lag_steps: int) -> float:
        """
        获取历史值。

        Args:
            lag_steps: 滞后步数（负数，如 -30 表示 30 步之前）
        """
        if lag_steps < 0:
            lag_steps = -lag_steps
        return float(self._vars.get_with_lag(self._var_name, lag_steps, 0.0))

    # 数值运算支持
    def __add__(self, other: Any) -> float:
        return float(self) + float(other)

    def __radd__(self, other: Any) -> float:
        return float(other) + float(self)

    def __mul__(self, other: Any) -> float:
        return float(self) * float(other)

    def __rmul__(self, other: Any) -> float:
        return float(other) * float(self)

    def __sub__(self, other: Any) -> float:
        return float(self) - float(other)

    def __rsub__(self, other: Any) -> float:
        return float(other) - float(self)

    def __truediv__(self, other: Any) -> float:
        return float(self) / float(other)

    def __rtruediv__(self, other: Any) -> float:
        return float(other) / float(self)

    def __repr__(self) -> str:
        """字符串表示（用于调试）。"""
        return f"<VariableAccessor {self._var_name}={float(self)}>"


class ExpressionNode:
    """
    表达式节点（用于 Variable 类型）。

    每个周期执行一次表达式计算，结果写入 VariableStore。
    """

    def __init__(
        self,
        config: ExpressionConfig,
        instances: Dict[str, Any],
    ) -> None:
        """
        初始化表达式节点。

        Args:
            config: 表达式配置
            instances: 实例字典
        """
        self.config = config
        self._instances = instances

    @property
    def name(self) -> str:
        """节点名称（输出变量名）。"""
        return self.config.name

    def step(self, vars_store: VariableStore) -> float:
        """
        执行一个周期计算。

        支持赋值表达式：variable_name = expression
        如果表达式是赋值，则提取右侧表达式执行。

        Args:
            vars_store: 变量存储

        Returns:
            当前周期计算得到的值
        """
        # 创建求值器（传入 vars_store）
        evaluator = ExpressionEvaluator(vars_store, self._instances)
        
        # 检查是否是赋值表达式
        # 赋值表达式需要使用 mode="exec" 解析
        try:
            # 先尝试用 exec 模式解析（支持赋值）
            tree = ast.parse(self.config.expression, mode="exec")
            if isinstance(tree.body[0], ast.Assign):
                # 赋值表达式：提取右侧表达式
                # 使用 ast.unparse 或手动构建表达式字符串
                if hasattr(ast, "unparse"):
                    # Python 3.9+
                    expr_str = ast.unparse(tree.body[0].value)
                else:
                    # 兼容旧版本：手动提取
                    # 这里简化处理，假设表达式格式为 "var = expr"
                    parts = self.config.expression.split("=", 1)
                    if len(parts) == 2:
                        expr_str = parts[1].strip()
                    else:
                        expr_str = self.config.expression
                value = evaluator.evaluate(expr_str)
            else:
                # 普通语句，尝试用 eval 模式解析
                value = evaluator.evaluate(self.config.expression)
        except SyntaxError:
            # 如果不是赋值表达式，尝试用 eval 模式解析
            try:
                value = evaluator.evaluate(self.config.expression)
            except SyntaxError:
                # 如果还是失败，说明表达式格式有问题
                raise ExpressionError(f"表达式格式错误: {self.config.expression}")
        
        # 写入变量存储
        vars_store.set(self.name, value)
        
        return value


class AlgorithmNode:
    """
    算法节点（用于算法/模型类型）。

    每个周期调用实例的 execute 方法。
    """

    def __init__(
        self,
        instance: Any,
        expression: str,
        stored_attributes: list[str],
        instance_name: str,
        instances: Dict[str, Any],
    ) -> None:
        """
        初始化算法节点。

        Args:
            instance: 算法/模型实例
            expression: 表达式字符串（方法调用表达式）
            stored_attributes: 需要存储的属性列表
            instance_name: 实例名称
            instances: 所有实例字典（用于解析参数）
        """
        self._instance = instance
        self._expression = expression
        self._stored_attributes = stored_attributes
        self._instance_name = instance_name
        self._instances = instances
        
        # 解析表达式，提取方法调用的参数
        self._parsed_args = self._parse_expression(expression)

    def _parse_expression(self, expression: str) -> Dict[str, str]:
        """
        解析表达式，提取方法调用的关键字参数。

        例如：pid1.execute(pv=tank1.level, sv=sin1.out)
        返回：{"pv": "tank1.level", "sv": "sin1.out"}

        解析逻辑：
        1. 使用 ast.parse 解析表达式为 AST
        2. 验证根节点是 Call 节点（方法调用）
        3. 遍历关键字参数，将参数值转换为字符串表达式
        4. 支持多种 AST 节点类型：Name、Attribute、Subscript、Constant 等

        Args:
            expression: 表达式字符串（必须是方法调用格式）

        Returns:
            参数字典 {参数名: 参数表达式字符串}

        Raises:
            ExpressionError: 如果表达式解析失败或不是方法调用
        """
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ExpressionError(f"表达式解析失败: {expression}, 错误: {e}") from e

        if not isinstance(tree.body, ast.Call):
            raise ExpressionError(f"表达式必须是方法调用: {expression}")

        args: Dict[str, str] = {}
        for keyword in tree.body.keywords:
            # 将参数值转换为字符串（用于后续解析）
            if hasattr(ast, "unparse"):
                # Python 3.9+
                param_expr = ast.unparse(keyword.value)
            else:
                # 兼容旧版本：手动构建表达式字符串
                # 这里简化处理，对于简单情况可以工作
                # 对于复杂表达式，建议使用 Python 3.9+
                if isinstance(keyword.value, ast.Name):
                    # 变量名：直接使用 id
                    param_expr = keyword.value.id
                elif isinstance(keyword.value, ast.Attribute):
                    # 属性访问：instance.attr
                    if isinstance(keyword.value.value, ast.Name):
                        param_expr = f"{keyword.value.value.id}.{keyword.value.attr}"
                    else:
                        # 复杂情况，使用 repr 作为后备
                        param_expr = repr(keyword.value.value)
                elif isinstance(keyword.value, ast.Subscript):
                    # 历史数据访问：v1[-30] 或 tank1.level[-30]
                    if isinstance(keyword.value.value, ast.Name):
                        base = keyword.value.value.id
                    elif isinstance(keyword.value.value, ast.Attribute):
                        base = f"{keyword.value.value.value.id}.{keyword.value.value.attr}"
                    else:
                        base = repr(keyword.value.value)
                    
                    # 处理 slice（支持负数索引，如 [-30]）
                    if isinstance(keyword.value.slice, ast.UnaryOp) and isinstance(keyword.value.slice.op, ast.USub):
                        if isinstance(keyword.value.slice.operand, ast.Constant):
                            lag = keyword.value.slice.operand.value
                        elif isinstance(keyword.value.slice.operand, ast.Num):
                            lag = keyword.value.slice.operand.n
                        else:
                            lag = "?"
                        param_expr = f"{base}[-{lag}]"
                    else:
                        param_expr = f"{base}[{repr(keyword.value.slice)}]"
                elif isinstance(keyword.value, ast.Constant):
                    # 常量：直接转换为字符串
                    param_expr = str(keyword.value.value)
                elif isinstance(keyword.value, ast.Num):
                    # 数字（兼容旧版本）
                    param_expr = str(keyword.value.n)
                else:
                    # 复杂情况，使用 repr 作为后备
                    param_expr = repr(keyword.value)
            args[keyword.arg] = param_expr

        return args

    def step(self, vars_store: VariableStore) -> None:
        """
        执行一个周期。

        Args:
            vars_store: 变量存储
        """
        # 解析参数值（支持属性访问和历史数据访问）
        evaluator = ExpressionEvaluator(vars_store, self._instances)
        resolved_args: Dict[str, float] = {}
        
        for param_name, param_expr in self._parsed_args.items():
            value = evaluator.evaluate(param_expr)
            resolved_args[param_name] = value

        # 调用 execute 方法
        self._instance.execute(**resolved_args)

        # 存储需要存储的属性
        for attr_name in self._stored_attributes:
            if hasattr(self._instance, attr_name):
                value = getattr(self._instance, attr_name)
                # 使用 instance_name.attribute_name 作为存储键
                vars_store.set(f"{self._instance_name}.{attr_name}", value)
