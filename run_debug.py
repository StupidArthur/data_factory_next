"""
运行debug_display的包装脚本

确保相对导入可以正常工作。
通过修改 sys.modules 和设置正确的包结构来解决相对导入问题。
"""

import sys
import pathlib
import types
import importlib.util

# 获取项目根目录
project_root = pathlib.Path(__file__).parent.resolve()
package_name = project_root.name

# 将项目根目录添加到 Python 路径
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 创建一个虚拟的包模块，使相对导入可以工作
if package_name not in sys.modules:
    package_module = types.ModuleType(package_name)
    sys.modules[package_name] = package_module
    package_module.__path__ = [str(project_root)]
    package_module.__file__ = str(project_root / "__init__.py")
    package_module.__package__ = package_name

# 预先创建子模块，使相对导入可以工作
# 关键：需要确保子模块知道它们的父包，这样相对导入才能工作
for submodule_name in ["core", "utils", "programs", "functions"]:
    full_name = f"{package_name}.{submodule_name}"
    
    # 创建完整包名的模块
    if full_name not in sys.modules:
        submodule = types.ModuleType(full_name)
        sys.modules[full_name] = submodule
        submodule.__package__ = full_name
        submodule.__path__ = [str(project_root / submodule_name)]
        submodule.__file__ = str(project_root / submodule_name / "__init__.py")
        # 将子模块添加到父包
        setattr(package_module, submodule_name, submodule)
    
    # 同时注册短名称，但指向同一个模块对象
    # 这样当使用短名称导入时，模块仍然知道它的完整包名
    if submodule_name not in sys.modules:
        sys.modules[submodule_name] = sys.modules[full_name]

# 设置当前模块的包名
sys.modules[__name__].__package__ = package_name

# 现在可以导入模块了
if __name__ == "__main__":
    # 直接导入 debug_display（此时包结构已经设置好）
    import debug_display
    debug_display.debug_display()

