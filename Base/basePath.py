"""
@Author  : 谢胜强
@Time    : 2026/5/5 18:34
@Desc    : 文件路径统一封装管理（企业级）
            功能：全局路径定义、自动创建所有目录、跨平台兼容
            适配：UI/接口/客户端/报告全模块路径管理
"""
import os


class BasePath:
    # 项目根目录：当前文件往上退两级
    # 因为 BasePath 通常在 Base/basePath.py，退一级到 Base，再退一级到项目根
    # 如果以后文件位置变了，这里要跟着改
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 配置文件
    CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, "Config", "配置文件.ini")

    # 数据目录
    DATA_PATH = os.path.join(PROJECT_ROOT, "Data")
    DATA_ELEMENT_PATH = os.path.join(DATA_PATH, "DataElement")
    DATA_DRIVER_PATH = os.path.join(DATA_PATH, "DataDriver")
    DATA_TEMP_PATH = os.path.join(DATA_PATH, "Temp")

    # 截图路径
    SCREENSHOT_PATH = os.path.join(DATA_TEMP_PATH, "Screenshots")
    SCREENSHOT_PIC_PATH = os.path.join(SCREENSHOT_PATH, 'error_pic.png')

    # 用例配置
    TESTCASES_PATH = os.path.join(DATA_TEMP_PATH, 'testcases.yaml')
    TEMPCASES_PATH = os.path.join(DATA_TEMP_PATH, 'tempcases.yaml')

    # 驱动目录
    DRIVER_PATH = os.path.join(PROJECT_ROOT, 'Driver')

    # 日志目录
    LOG_PATH = os.path.join(PROJECT_ROOT, 'Log')

    # 页面对象
    PAGEOBJECT_PATH = os.path.join(PROJECT_ROOT, 'PageObject')

    # 测试报告目录
    REPORTS_PATH = os.path.join(PROJECT_ROOT, 'Reports')
    ALLURE_PATH = os.path.join(REPORTS_PATH, 'ALLURE')
    ALLURE_RESULT_PATH = os.path.join(ALLURE_PATH, 'Result')
    ALLURE_REPORT_PATH = os.path.join(ALLURE_PATH, 'Report')
    HTML_PATH = os.path.join(REPORTS_PATH, 'HTML')
    XML_PATH = os.path.join(REPORTS_PATH, 'XML')

    # 测试用例套件
    TEST_SUITS_PATH = os.path.join(PROJECT_ROOT, 'TestSuits')

    @staticmethod
    def create_dirs():
        """
        自动创建所有必需的目录
        框架启动时调用，省得各处写 os.makedirs 的重复代码
        之前踩过坑：日志模块初始化时 Log 目录不存在，直接抛 FileNotFoundError
        现在统一在这里创建，import 这个模块就自动执行
        """
        dir_list = [
            BasePath.DATA_PATH,
            BasePath.DATA_ELEMENT_PATH,
            BasePath.DATA_DRIVER_PATH,
            BasePath.DATA_TEMP_PATH,
            BasePath.SCREENSHOT_PATH,
            BasePath.DRIVER_PATH,
            BasePath.LOG_PATH,
            BasePath.REPORTS_PATH,
            BasePath.ALLURE_PATH,
            BasePath.ALLURE_RESULT_PATH,
            BasePath.ALLURE_REPORT_PATH,
            BasePath.HTML_PATH,
            BasePath.XML_PATH,
            BasePath.PAGEOBJECT_PATH,
            BasePath.TEST_SUITS_PATH
        ]
        for path in dir_list:
            # exist_ok=True 表示目录已存在时不抛异常，直接跳过
            os.makedirs(path, exist_ok=True)


# 模块 import 时自动创建所有目录
# 这样 Logger、ExcelHandler、截图模块等地方直接用路径就行，不用关心目录在不在
BasePath.create_dirs()

if __name__ == '__main__':
    print(BasePath.PROJECT_ROOT)
    print(BasePath.CONFIG_FILE_PATH)
    print(BasePath.DATA_PATH)
    print(BasePath.DATA_DRIVER_PATH)
    print(BasePath.DATA_ELEMENT_PATH)
    print(BasePath.DATA_TEMP_PATH)
    print(BasePath.DRIVER_PATH)
    print(BasePath.LOG_PATH)
    print(BasePath.ALLURE_PATH)
    print(BasePath.HTML_PATH)
    print(BasePath.XML_PATH)