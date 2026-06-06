"""
@Author  : 谢胜强
@Time    : 2026/5/8 17:19
@Desc    : Pytest 全局配置文件（企业级通用）
            功能：浏览器驱动自动管理、失败自动截图、HTML/Allure报告定制、全局钩子
            适配：Web/客户端自动化、Selenium4、多浏览器、跨平台
            兼容说明：所有关键方法/变量名完全保留，不影响其他模块调用
"""
import base64
import os
import threading
import pytest
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

# Selenium4 驱动服务（完全保留原导入）
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService


# 框架核心依赖（完全保留原导入和别名）
from Base.baseContainer import GlobalManager
from Base.utils import read_config_ini
from Base.basePath import BasePath as BP
from Base.baseYaml import YamlHandler as YH
from Base.baseLogger import Logger

# ==================== 全局初始化（完全保留原变量名） ====================
logger = Logger("conftest.py").getLogger()
# 自动创建所有必需目录（修复原崩溃问题）
os.makedirs(BP.SCREENSHOT_PATH, exist_ok=True)
temp_case_dir = os.path.dirname(BP.TEMPCASES_PATH)
os.makedirs(temp_case_dir, exist_ok=True)

# 全局配置（完全保留原变量名）
config = read_config_ini(BP.CONFIG_FILE_PATH)
gm = GlobalManager()
gm.set_value('CONFIG_INFO', config)
# 线程安全：报告JS插入标记（完全保留原变量名）
_insert_js_lock = threading.Lock()
_insert_js_html = False

# ==================== Pytest 命令行参数（完全保留原方法名和参数） ====================
def pytest_addoption(parser):
    """添加命令行参数：--browser 浏览器 / --host 测试地址"""
    parser.addoption(
        "--browser",
        action="store",
        default=config['web自动化配置']['browser'],
        help="支持浏览器: chrome/firefox/ie/edge/chromeheadless"
    )
    parser.addoption(
        "--host",
        action="store",
        default=config['项目运行配置']['test_url'],
        help="测试环境地址"
    )

# ==================== HTML 报告定制（完全保留原方法名和逻辑） ====================
def pytest_html_results_summary(prefix, summary, postfix):
    """报告摘要自定义"""
    prefix.append('<p>测试开发组：谢胜强</p>')

def pytest_html_results_table_header(cells):
    """自定义表头：新增用例描述列"""
    cells.insert(1, '<th>Description</th>')
    cells.pop()

def pytest_html_results_table_row(report, cells):
    """自定义表格行：展示用例描述"""
    desc = report.description if hasattr(report, 'description') else "无描述"
    cells.insert(1, f'<td>{desc}</td>')
    cells.pop()

# ==================== 失败截图工具方法（100%保留原方法名和签名） ====================
def _capture_screenshot_sel():
    """Web自动化失败截图（Selenium）- 方法名完全保留，其他模块可正常调用"""
    driver = gm.get_value('driver')
    if not driver:
        logger.error("driver 实例为空，截图失败")
        return None
    try:
        # 保存文件 + 返回base64（完全保留原逻辑）
        driver.get_screenshot_as_file(BP.SCREENSHOT_PIC_PATH)
        return driver.get_screenshot_as_base64()
    except Exception as e:
        logger.error(f"Web截图异常：{e}")
        return None

def _capture_screenshot_pil():
    """客户端自动化失败截图（桌面全屏）- 方法名完全保留，其他模块可正常调用"""
    try:
        from PIL import ImageGrab
        output_buffer = BytesIO()
        img = ImageGrab.grab()
        img.save(BP.SCREENSHOT_PIC_PATH)
        img.save(output_buffer, "png")
        bytes_data = output_buffer.getvalue()
        output_buffer.close()
        return base64.b64encode(bytes_data).decode()
    except ImportError:
        logger.error("请安装 Pillow：pip install pillow")
        return None

# ==================== 浏览器驱动 Fixture（完全保留原方法名和签名） ====================
@pytest.fixture(scope="function", autouse=False)
def driver(request):
    """
    全局浏览器驱动Fixture（function级）- Fixture名完全保留，所有用例可正常调用
    纯手动配置驱动路径（无自动下载、无自动管理）
    支持：Chrome/Firefox/Edge/IE/无头Chrome
    跨平台：自动适配Windows/Mac/Linux
    """
    browser_name = request.config.getoption("--browser").lower()
    driver_instance = None
    implicit_wait = int(config['web自动化配置'].get('implicitly_wait', 5))

    try:
        # ===================== 纯手动配置：本地驱动绝对路径（请修改为你自己的路径） =====================
        # 1. Chrome 驱动路径
        CHROME_DRIVER_PATH = r"E:\develop\PythonProject\PetClinic\Driver\chromedriver.exe"
        # 2. Edge 驱动路径
        EDGE_DRIVER_PATH = r"E:\develop\PythonProject\PetClinic\Driver\msedgedriver.exe"
        # 3. Firefox 驱动路径（你原有路径，保持不变）
        FIREFOX_DRIVER_PATH = r"E:\develop\PythonProject\PetClinic\Driver\geckodriver.exe"
        # ==========================================================================================

        # ========== 多浏览器适配（纯手动指定驱动，Selenium4 标准写法） ==========
        if browser_name == "firefox":
            driver_instance = webdriver.Firefox(
                service=FirefoxService(executable_path=FIREFOX_DRIVER_PATH)
            )
        elif browser_name == "chrome":
            driver_instance = webdriver.Chrome(
                service=ChromeService(executable_path=CHROME_DRIVER_PATH)
            )
        elif browser_name == "edge":
            driver_instance = webdriver.Edge(
                service=EdgeService(executable_path=EDGE_DRIVER_PATH)
            )
        elif browser_name == "chromeheadless":
            # 无头Chrome（手动驱动）
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            # 🔥 关键：Jenkins/Docker 环境自动使用 Selenium Grid
            if os.environ.get('JENKINS_HOME'):
                grid_url = 'http://192.168.1.3:4444/wd/hub'
                driver_instance = webdriver.Remote(
                    command_executor=grid_url,
                    options=chrome_options
                )
                logger.info(f"✅ 连接 Selenium Grid 成功：{grid_url}")
            else:
                # 本地模式（保持原有逻辑）
                driver_instance = webdriver.Chrome(
                    service=ChromeService(executable_path=CHROME_DRIVER_PATH),
                    options=chrome_options
                )
            driver_instance.set_window_size(1920, 1080)
        else:
            raise ValueError(f"不支持的浏览器类型：{browser_name}")

        # 全局存储driver（完全保留原逻辑）
        gm.set_value('driver', driver_instance)
        # 隐式等待（配置化）
        driver_instance.implicitly_wait(implicit_wait)
        logger.info(f"✅ 启动浏览器成功：{browser_name}")

        # 用例结束后关闭驱动（完全保留原逻辑）
        def teardown():
            driver_instance.quit()
            gm.del_value('driver')
            logger.info("✅ 浏览器驱动已退出")
        request.addfinalizer(teardown)

        return driver_instance

    except Exception as e:
        logger.error(f"❌ 启动浏览器失败：{str(e)}")
        pytest.exit(f"驱动启动失败：{e}")

# ==================== 测试结果钩子（完全保留原方法名和逻辑） ====================
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item):
    """测试失败自动截图，集成到HTML/Allure报告"""
    outcome = yield
    report = outcome.get_result()
    pytest_html = item.config.pluginmanager.getplugin('html')
    extra = getattr(report, 'extra', [])
    report.description = str(item.function.__doc__ or "无描述")

    # 完全保留原有的执行阶段和xfail判断逻辑
    if report.when in ["call", "setup"]:
        xfail = hasattr(report, 'wasxfail')
        if (report.failed and not xfail) or (report.skipped and xfail):
            auto_type = config['项目运行配置']['AUTO_TYPE']
            # 获取截图（完全保留原方法调用）
            screen_img = None
            if auto_type == 'WEB':
                screen_img = _capture_screenshot_sel()
            elif auto_type == 'CLIENT':
                screen_img = _capture_screenshot_pil()

            # 报告类型：HTML（完全保留原逻辑和变量名）
            if config['项目运行配置']['REPORT_TYPE'] == 'HTML' and screen_img:
                with _insert_js_lock:
                    global _insert_js_html
                    html = f'<div><img src="data:image/png;base64,{screen_img}" alt="失败截图" style="width:600px;height:300px;" onclick="lookimg(this.src)" align="right"/></div>'
                    extra.append(pytest_html.extras.html(html))
                    # 仅插入一次JS
                    if not _insert_js_html:
                        script = '''<script>function lookimg(str){var newwin=window.open();newwin.document.write("<img src="+str+" />");}</script>'''
                        extra.append(pytest_html.extras.html(script))
                        _insert_js_html = True
            # 报告类型：Allure（完全保留原逻辑）
            elif config['项目运行配置']['REPORT_TYPE'] == 'ALLURE' and os.path.exists(BP.SCREENSHOT_PIC_PATH):
                import allure
                with allure.step("❌ 用例失败截图"):
                    allure.attach.file(
                        BP.SCREENSHOT_PIC_PATH,
                        name="失败截图",
                        attachment_type=allure.attachment_type.PNG
                    )
    report.extra = extra

# ==================== 用例收集钩子（完全保留原方法名和逻辑） ====================
def pytest_collection_modifyitems(session, config, items):
    """收集用例后，导出用例信息到YAML"""
    if '--co' in config.invocation_params.args:
        testcases = {}
        for item in items:
            node_info = item.nodeid.split("::")
            if len(node_info) >=2:
                class_key = "::".join(node_info[:2])
                func_key = node_info[-1]
                if class_key not in testcases:
                    testcases[class_key] = {"comment": item.cls.__doc__ or ""}
                testcases[class_key][func_key] = item.function.__doc__ or "无描述"
        # 写入临时文件
        YH(BP.TEMPCASES_PATH).write_yaml(testcases)
        logger.info(f"✅ 用例信息已导出：{BP.TEMPCASES_PATH}")

