"""
@Author  : 谢胜强
@Time    : 2026/5/9 12:25
@Desc    : PyQt5 树形组件展示/选择自动化测试用例
            功能：用例树形展示、父子联动勾选、全选/取消、导出选中用例
            适配：Pytest自动化框架用例选择
"""
import sys
from typing import Dict, Any
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
                             QWidget, QVBoxLayout, QScrollArea, QToolBar, QAction)
from PyQt5.QtCore import Qt
from Base.baseYaml import YamlHandler as YH
from Base.basePath import BasePath as BP
from Base.baseLogger import Logger

logger = Logger("caseSelector.py").getLogger()


class MainWindow(QMainWindow):
    def __init__(self, case_data: Dict[str, Any]):
        super().__init__()
        self.case_data = case_data
        self.root_items = []  # 存储根节点，后面全选/取消全选要用
        self.setWindowTitle('自动化测试用例执行程序')
        self.resize(650, 850)
        self.center_window()

        self.init_tool_bar()
        self.init_ui()
        self.init_tree_widget()

        self.statusBar().showMessage("就绪：请选择要执行的测试用例")

    def center_window(self):
        """窗口屏幕居中"""
        screen_rect = QApplication.primaryScreen().geometry()
        window_rect = self.geometry()
        x = (screen_rect.width() - window_rect.width()) // 2
        y = (screen_rect.height() - window_rect.height()) // 2
        self.move(x, y)

    def init_tool_bar(self):
        """初始化顶部工具栏"""
        tool_bar = QToolBar('用例操作')
        self.addToolBar(tool_bar)

        self.btn_submit = QAction('提交选中用例', self)
        self.btn_select_all = QAction('全选用例', self)
        self.btn_cancel_all = QAction('取消全选', self)

        self.btn_submit.triggered.connect(self.export_selected_cases)
        self.btn_select_all.triggered.connect(self.select_all)
        self.btn_cancel_all.triggered.connect(self.select_all_cancel)

        tool_bar.addActions([self.btn_submit, self.btn_select_all, self.btn_cancel_all])

    def init_ui(self):
        """初始化主界面布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['用例模块/名称', '用例函数'])
        self.tree.setColumnWidth(0, 420)
        self.tree.setAlternatingRowColors(True)

        # 默认展开所有节点，省得用户一层层手动点
        self.tree.expandAll()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.tree)

        main_layout.addWidget(scroll)

    def init_tree_widget(self):
        """初始化树形用例数据"""
        if not self.case_data:
            logger.warning("用例数据为空，请先收集用例！")
            return

        for module_key, module_info in self.case_data.items():
            # 根节点是模块名，comment 字段存的是模块描述
            root_node = QTreeWidgetItem(self.tree)
            root_node.setText(0, module_info.get('comment', '未命名模块'))
            root_node.setCheckState(0, Qt.Checked)
            self.root_items.append((root_node, module_key))

            # 子节点是具体用例，跳过 comment 这个特殊键
            for case_func, case_name in module_info.items():
                if case_func == "comment":
                    continue
                child_node = QTreeWidgetItem(root_node)
                child_node.setText(0, case_name)
                child_node.setText(1, case_func)
                child_node.setCheckState(0, Qt.Checked)

        # itemChanged 信号只能绑一次
        # 如果绑多次，setCheckState 会触发 itemChanged，itemChanged 里又调 setCheckState，死循环
        # 之前踩过坑：在循环里每次创建子节点都绑一次信号，勾选时直接卡死
        self.tree.itemChanged.connect(self.on_tree_item_changed)

    def on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        """
        树形节点勾选联动（父子节点同步）
        目前只做了父节点→子节点的同步，子节点变化不会反向影响父节点
        如果以后需要半选状态（子节点部分勾选），得再补逻辑
        """
        if column != 0:
            return

        # 判断是不是父节点：有子节点的就是父节点
        child_count = item.childCount()
        if child_count > 0:
            check_state = item.checkState(0)
            for i in range(child_count):
                item.child(i).setCheckState(0, check_state)

    def select_all(self):
        """全选所有用例模块"""
        # 直接改父节点的勾选状态，子节点会通过 itemChanged 信号自动同步
        for item, _ in self.root_items:
            item.setCheckState(0, Qt.Checked)
        self.statusBar().showMessage("已全选所有用例")

    def select_all_cancel(self):
        """取消全选"""
        for item, _ in self.root_items:
            item.setCheckState(0, Qt.Unchecked)
        self.statusBar().showMessage("已取消所有用例选择")

    def export_selected_cases(self):
        """导出选中的用例到YAML文件"""
        selected_cases = {}

        for root_item, module_key in self.root_items:
            case_func_list = []
            for i in range(root_item.childCount()):
                child = root_item.child(i)
                if child.checkState(0) == Qt.Checked:
                    # text(1) 存的是函数名，后面 pytest 执行时直接 import 这个函数
                    case_func_list.append(child.text(1))

            # 空模块不写入，避免 YAML 里出现一堆空列表
            if case_func_list:
                selected_cases[module_key] = case_func_list

        # 直接覆盖写入，不是追加
        # 每次重新选择用例，之前的选择结果就作废了
        YH(BP.TESTCASES_PATH).write_yaml(selected_cases)
        logger.info(f"用例导出成功：{BP.TESTCASES_PATH}")
        self.statusBar().showMessage(f"成功导出 {len(selected_cases)} 个模块的用例！")


def run_case_selector():
    """启动用例选择工具（主入口）"""
    try:
        # 用例数据是 pytest --co 收集后生成的临时文件
        # 如果还没收集就直接启动选择器，会报 FileNotFoundError
        case_data = YH(BP.TEMPCASES_PATH).read_yaml()
        app = QApplication(sys.argv)
        window = MainWindow(case_data)
        window.show()
        # sys.exit 确保 Qt 事件循环结束后进程真正退出，不会挂后台
        sys.exit(app.exec_())
    except FileNotFoundError:
        logger.error(f"用例临时文件不存在：{BP.TEMPCASES_PATH}，请先运行pytest --co收集用例！")
    except Exception as e:
        logger.error(f"用例选择器启动失败：{str(e)}")


if __name__ == "__main__":
    run_case_selector()