"""
数据绘图工具

使用PyQt6实现的CSV数据可视化工具，支持：
- 选择数据文件和导出模板
- 选择要绘制的位号（checkbox）
- 绘制选中位号的曲线图
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
import matplotlib

from export_templates.template_manager import TemplateManager
from utils.logger import get_logger

# 配置matplotlib中文字体
# Windows系统常用中文字体：Microsoft YaHei（微软雅黑）、SimHei（黑体）、SimSun（宋体）
# 尝试多个字体，找到系统中可用的
_chinese_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong']
_available_font = None

# 先初始化logger（用于字体配置日志）
logger = get_logger()

try:
    # 获取系统中所有可用字体
    font_manager = matplotlib.font_manager.fontManager
    font_list = [f.name for f in font_manager.ttflist]
    
    # 查找可用的中文字体
    for font_name in _chinese_fonts:
        if font_name in font_list:
            _available_font = font_name
            break
    
    # 如果找到可用字体，配置matplotlib使用
    if _available_font:
        plt.rcParams['font.sans-serif'] = [_available_font, 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        logger.info(f"配置matplotlib使用中文字体: {_available_font}")
    else:
        # 如果没找到，尝试使用系统默认字体
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        logger.warning("未找到可用的中文字体，中文可能显示为乱码")
except Exception as e:
    logger.warning(f"配置中文字体时出错: {e}，使用默认字体")
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False


class DataPlotterWindow(QMainWindow):
    """
    数据绘图工具主窗口
    
    界面布局：
    - 顶部：数据文件选择、模板选择
    - 左侧：位号列表（checkbox + 位号名）
    - 底部：绘制按钮
    - 右侧：绘图区域
    """
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        self.setWindowTitle("数据绘图工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 数据存储
        self.data_file_path: Optional[Path] = None
        self.template_name: Optional[str] = None
        self.data_df: Optional[pd.DataFrame] = None
        self.time_column_name: str = "时间"
        
        # 模板管理器
        self.template_manager = TemplateManager()
        
        # 创建UI
        self._create_ui()
        
        # 加载模板列表
        self._load_template_list()
    
    def _create_ui(self):
        """创建UI界面"""
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局（垂直）
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        # 顶部区域：文件选择和模板选择
        top_layout = self._create_top_area()
        main_layout.addLayout(top_layout)
        
        # 中间区域：左侧列表 + 右侧绘图
        middle_layout = QHBoxLayout()
        
        # 左侧：位号列表
        left_widget = self._create_left_area()
        middle_layout.addWidget(left_widget, 1)  # 占比1
        
        # 右侧：绘图区域
        right_widget = self._create_right_area()
        middle_layout.addWidget(right_widget, 2)  # 占比2
        
        main_layout.addLayout(middle_layout, 1)  # 占比1，可伸缩
        
        # 底部：绘制按钮
        bottom_layout = self._create_bottom_area()
        main_layout.addLayout(bottom_layout)
    
    def _create_top_area(self) -> QHBoxLayout:
        """
        创建顶部区域：数据文件选择和模板选择
        
        Returns:
            顶部布局
        """
        layout = QHBoxLayout()
        
        # 数据文件选择
        file_label = QLabel("数据文件:")
        file_label.setMinimumWidth(80)
        layout.addWidget(file_label)
        
        self.file_path_label = QLabel("未选择")
        self.file_path_label.setStyleSheet("border: 1px solid gray; padding: 5px;")
        layout.addWidget(self.file_path_label, 1)
        
        self.file_select_btn = QPushButton("选择文件")
        self.file_select_btn.clicked.connect(self._select_data_file)
        layout.addWidget(self.file_select_btn)
        
        # 模板选择
        template_label = QLabel("导出模板:")
        template_label.setMinimumWidth(80)
        layout.addWidget(template_label)
        
        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(self._on_template_selected)
        layout.addWidget(self.template_combo, 1)
        
        return layout
    
    def _create_left_area(self) -> QWidget:
        """
        创建左侧区域：位号列表（checkbox + 位号名）
        
        Returns:
            左侧部件
        """
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 标题
        title_label = QLabel("位号列表")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 位号列表
        self.tag_list = QListWidget()
        layout.addWidget(self.tag_list, 1)
        
        return widget
    
    def _create_right_area(self) -> QWidget:
        """
        创建右侧区域：绘图区域
        
        Returns:
            右侧部件
        """
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 标题
        title_label = QLabel("曲线图")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Matplotlib 绘图区域
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, 1)
        
        return widget
    
    def _create_bottom_area(self) -> QHBoxLayout:
        """
        创建底部区域：绘制按钮 + 署名
        
        Returns:
            底部布局
        """
        layout = QHBoxLayout()
        
        # 占位符（左侧）
        layout.addStretch()
        
        # 绘制按钮
        self.plot_btn = QPushButton("绘制")
        self.plot_btn.setMinimumWidth(100)
        self.plot_btn.setMinimumHeight(40)
        self.plot_btn.clicked.connect(self._plot_selected_tags)
        layout.addWidget(self.plot_btn)
        
        # 占位符（中间）
        layout.addStretch()
        
        # 署名标签（右下角）
        signature_label = QLabel("designed by @yuzechao")
        signature_label.setStyleSheet("color: gray; font-size: 10px; padding: 5px;")
        layout.addWidget(signature_label)
        
        return layout
    
    def _load_template_list(self):
        """加载模板列表"""
        try:
            templates = self.template_manager.list_templates()
            self.template_combo.clear()
            self.template_combo.addItem("-- 请选择模板 --")
            for template_name in templates:
                self.template_combo.addItem(template_name)
            
            if templates:
                logger.info(f"加载了 {len(templates)} 个模板")
            else:
                logger.warning("未找到任何模板")
        except Exception as e:
            logger.error(f"加载模板列表失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"加载模板列表失败: {e}")
    
    def _select_data_file(self):
        """选择数据文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据文件",
            "",
            "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            self.data_file_path = Path(file_path)
            self.file_path_label.setText(str(self.data_file_path))
            self._load_data_file()
    
    def _load_data_file(self):
        """
        加载数据文件
        
        根据模板配置解析CSV文件，提取位号列表
        """
        if not self.data_file_path or not self.data_file_path.exists():
            return
        
        try:
            # 获取模板配置（如果已选择）
            header_rows = 1
            if self.template_name:
                try:
                    template = self.template_manager.load_template(self.template_name)
                    header_rows = template.header_rows
                    self.time_column_name = template.time_column_name
                except Exception as e:
                    logger.warning(f"加载模板配置失败，使用默认配置: {e}")
            
            # 读取CSV文件
            # 如果header_rows=2，使用MultiIndex读取
            if header_rows == 2:
                # 双行标题：第一行是列名，第二行是描述
                self.data_df = pd.read_csv(
                    self.data_file_path,
                    encoding="utf-8",
                    header=[0, 1],  # 使用前两行作为标题
                    skipinitialspace=True
                )
                # 获取第一层列名（实际列名）
                self.data_df.columns = self.data_df.columns.get_level_values(0)
            else:
                # 单行标题
                self.data_df = pd.read_csv(
                    self.data_file_path,
                    encoding="utf-8",
                    header=0,
                    skipinitialspace=True
                )
            
            # 如果没有从模板获取时间列名，尝试从CSV文件第一行获取
            if not self.time_column_name or self.time_column_name not in self.data_df.columns:
                # 读取第一行获取时间列名
                with self.data_file_path.open("r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    first_row = next(reader)
                    if first_row:
                        self.time_column_name = first_row[0]
            
            # 获取位号列表（排除时间列）
            tag_columns = [col for col in self.data_df.columns if col != self.time_column_name]
            
            # 更新位号列表
            self.tag_list.clear()
            for tag in tag_columns:
                item = QListWidgetItem(tag)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.tag_list.addItem(item)
            
            logger.info(f"加载数据文件成功: {len(tag_columns)} 个位号, header_rows={header_rows}")
            
        except Exception as e:
            logger.error(f"加载数据文件失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"加载数据文件失败: {e}")
            self.data_df = None
    
    def _on_template_selected(self, template_name: str):
        """
        模板选择事件处理
        
        Args:
            template_name: 选中的模板名称
        """
        if template_name == "-- 请选择模板 --":
            self.template_name = None
            return
        
        self.template_name = template_name
        logger.info(f"选择模板: {self.template_name}")
        
        # 如果已加载数据文件，重新加载以应用模板配置
        if self.data_file_path:
            self._load_data_file()
    
    def _plot_selected_tags(self):
        """绘制选中的位号曲线"""
        if self.data_df is None:
            QMessageBox.warning(self, "警告", "请先选择数据文件")
            return
        
        # 获取选中的位号
        selected_tags = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_tags.append(item.text())
        
        if not selected_tags:
            QMessageBox.warning(self, "警告", "请至少选择一个位号")
            return
        
        try:
            # 清空绘图区域
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # 获取时间列数据
            time_data = self.data_df[self.time_column_name]
            
            # 转换时间格式（如果是字符串）
            if time_data.dtype == 'object':
                # 尝试解析时间字符串
                try:
                    # 尝试多种时间格式
                    time_data = pd.to_datetime(time_data, format='%Y-%m-%d %H:%M:%S', errors='coerce')
                    if time_data.isna().any():
                        # 如果解析失败，尝试其他格式
                        time_data = pd.to_datetime(self.data_df[self.time_column_name], errors='coerce')
                except Exception:
                    # 如果都失败，使用索引作为x轴
                    time_data = range(len(self.data_df))
            
            # 绘制每个选中的位号
            for tag in selected_tags:
                if tag in self.data_df.columns:
                    values = pd.to_numeric(self.data_df[tag], errors='coerce')
                    ax.plot(time_data, values, label=tag, linewidth=1.5)
            
            # 设置图表属性
            # 使用FontProperties显式指定字体，确保中文正常显示
            if _available_font:
                font_prop = FontProperties(family=_available_font, size=12)
                title_font_prop = FontProperties(family=_available_font, size=14, weight='bold')
                legend_font_prop = FontProperties(family=_available_font, size=10)
            else:
                font_prop = FontProperties(size=12)
                title_font_prop = FontProperties(size=14, weight='bold')
                legend_font_prop = FontProperties(size=10)
            
            ax.set_xlabel(self.time_column_name, fontproperties=font_prop)
            ax.set_ylabel("数值", fontproperties=font_prop)
            ax.set_title("位号曲线图", fontproperties=title_font_prop)
            ax.legend(loc='best', prop=legend_font_prop)
            ax.grid(True, alpha=0.3)
            
            # 自动调整布局
            self.figure.tight_layout()
            
            # 刷新画布
            self.canvas.draw()
            
            logger.info(f"绘制成功: {len(selected_tags)} 个位号")
            
        except Exception as e:
            logger.error(f"绘制失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"绘制失败: {e}")


def run_plotter():
    """
    运行绘图工具
    
    入口函数，使用函数参数方式传参（符合项目规范）
    """
    app = QApplication([])
    window = DataPlotterWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run_plotter()

