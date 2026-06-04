"""
@Author  : 谢胜强
@Time    : 2026/5/9 12:33
@Desc    : 客户端自动化GUI版主入口（优化版）
"""
import os
import sys
import ctypes
import multiprocessing
import subprocess
import shutil
from contextlib import contextmanager

# 这里退三级，因为 runClient.py 通常放在 Client/Run/ 之类的深层目录
# 而项目根目录还要再往上退一级，所以比 run.py 多退一级
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
sys.path.append(os.path.join(PROJECT_ROOT, "Base"))

import pytest
from Base.baseContainer import GlobalManager
from Base.baseSendEmail import HandleEmail
from Base.baseGuiRun import run_case_selector
from Base.basePath import BasePath as BP
from Base.utils import read_config_ini, file_all_delete
from Base.baseYaml import YamlHandler as YH
from Base.baseLogger import Logger

logger = Logger("runClient.py").get_logger()
config = read_config_ini(BP.CONFIG_FILE_PATH)
gm = GlobalManager()
gm.set_value('CONFIG_INFO', config)
run_config = gm.get_value('CONFIG_INFO')['项目运行配置']
run_config["TEST_PROJECT"] = run_config["TEST_PROJECT"].strip()
run_config["IS_EMAIL"] = run_config["IS_EMAIL"].strip().lower()

ALLURE_BIN = r"D:\Allure\allure-2.42.0\bin"
ALLURE_CMD = os.path.join(ALLURE_BIN, "allure.bat")

def _ensure_allure_in_path() -> None:
    """将 Allure 路径注入当前进程环境变量"""
    current_path = os.environ.get("PATH", "")
    if ALLURE_BIN not in current_path:
        os.environ["PATH"] = ALLURE_BIN + os.pathsep + current_path

# 用例收集时 pytest 会打印大量收集信息到控制台，干扰 GUI 界面
# 这个上下文管理器把 stdout/stderr 重定向到空设备，让收集过程完全静默
# 收集完再恢复，不影响后续正常的日志输出
@contextmanager
def output_to_null():
    with open(os.devnull, 'w', encoding='utf-8') as dev_null:
        saved_stdout, saved_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = dev_null, dev_null
        try:
            yield
        finally:
            sys.stdout, sys.stderr = saved_stdout, saved_stderr

# 用例收集单独跑一个进程，是因为 pytest 的用例收集会修改全局状态（比如导入模块、注册 fixture）
# 如果在主进程里收集，再启动 GUI 选择器，可能会导致模块重复导入或者 fixture 冲突
# 而且收集过程可能很慢，放子进程里不会阻塞 GUI 的响应
def run_collect_testcase(result_flag):
    with output_to_null():
        try:
            test_project_path = os.path.join(BP.TEST_SUITS_PATH, run_config['TEST_PROJECT'])
            res = pytest.main(['-s', '-q', '--co', test_project_path])
            # result_flag 是 multiprocessing 的共享变量，子进程设置后主进程能读到
            result_flag.value = (res == 0)
        except Exception as e:
            logger.error(f"❌ 用例收集失败：{str(e)}")
            result_flag.value = False

def _build_allure_report(result_path: str, report_path: str) -> bool:
    """生成 Allure HTML 报告"""
    _ensure_allure_in_path()

    if not os.path.exists(ALLURE_CMD):
        logger.error(f"❌ Allure 命令行工具不存在：{ALLURE_CMD}")
        return False

    try:
        result = subprocess.run(
            [ALLURE_CMD, "generate", result_path, "-o", report_path, "--clean"],
            capture_output=True, text=True, check=True
        )
        logger.info(f"✅ Allure报告生成完成：{report_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Allure 报告生成失败：\n{e.stderr}")
        return False
    except FileNotFoundError:
        logger.error(f"❌ 无法调用 Allure，请确认已安装并配置路径：{ALLURE_CMD}")
        return False

def _build_html_report(test_cases, html_path: str):
    """生成 HTML 报告"""
    pytest.main(['-v', f'--html={html_path}', '--self-contained-html', *test_cases])
    logger.info(f"✅ HTML报告生成完成：{html_path}")

def _build_xml_report(test_cases, xml_path: str):
    """生成 XML 报告"""
    pytest.main(['-v', f'--junitxml={xml_path}', *test_cases])
    logger.info(f"✅ XML报告生成完成：{xml_path}")

def _create_allure_viewer_bat(report_path: str) -> None:
    """
    在 Allure 报告目录生成"双击查看报告.bat"
    原理：启动 Edge/Chrome 并带上 --allow-file-access-from-files 参数，
          解除浏览器对本地 file:// 协议访问子目录 JSON 的限制
    """
    bat_content = r'''@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 Allure 报告查看器...
echo.

if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    set "BROWSER=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
) else if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    set "BROWSER=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
) else if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else (
    echo 未检测到 Edge 或 Chrome 浏览器，请安装后重试。
    pause
    exit /b 1
)

set "TEMP_PROFILE=%TEMP%\allure_report_%RANDOM%"
mkdir "%TEMP_PROFILE%" 2>nul

start "" "%BROWSER%" --allow-file-access-from-files --user-data-dir="%TEMP_PROFILE%" --no-first-run --no-default-browser-check "%~dp0index.html"

echo.
echo 报告已打开，关闭浏览器窗口即可。
echo 请勿删除本文件夹内的其他文件，否则报告无法正常显示。
timeout /t 3 >nul
'''
    bat_path = os.path.join(report_path, "双击查看报告.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    logger.info(f"✅ 报告查看器已生成：{bat_path}")

def _zip_allure_report(report_path: str) -> str:
    """压缩整个 Allure 报告文件夹"""
    for item in os.listdir(report_path):
        if item.lower().endswith('.zip'):
            old_zip = os.path.join(report_path, item)
            try:
                os.remove(old_zip)
                logger.info(f"🧹 清理报告目录内旧压缩包：{old_zip}")
            except Exception as e:
                logger.warning(f"⚠️ 清理旧压缩包失败：{e}")

    zip_base = os.path.join(os.path.dirname(report_path), "allure_report")
    if os.path.exists(zip_base + ".zip"):
        os.remove(zip_base + ".zip")

    zip_path = shutil.make_archive(zip_base, 'zip', report_path)
    logger.info(f"✅ 报告压缩包已生成：{zip_path}")
    return zip_path

def _send_report_email(report_type: str):
    """发送测试报告邮件"""
    if run_config.get("IS_EMAIL", "").lower() != "yes":
        return
    try:
        email_handler = HandleEmail()
        email_text = '本邮件由系统自动发出，无需回复！\n各位同事，大家好，以下为本次测试报告!'
        email_handler.send_public_email(text=email_text, filetype=report_type)
        logger.info("📧 测试报告邮件发送成功")
    except Exception as e:
        logger.error(f"📧 邮件发送失败：{str(e)}")

def run_main():
    try:
        case_data = YH(BP.TESTCASES_PATH).read_yaml()
        if not case_data:
            logger.warning("⚠️ 未选择任何测试用例，程序退出")
            return

        # pytest 的 nodeid 格式要求用正斜杠，Windows 默认反斜杠会解析失败
        # 比如 "TestSuits\project01\test_login.py" 要转成 "TestSuits/project01/test_login.py"
        # 否则 pytest 认不出这个路径，直接报 "module not found"
        test_case_list = []
        for module_path, case_names in case_data.items():
            module_path = module_path.replace("\\", "/")
            for case_name in case_names:
                # 拼接完整的 pytest nodeid：文件路径::函数名
                full_case_path = f"{BP.PROJECT_ROOT}/{module_path}::{case_name}"
                test_case_list.append(full_case_path)

        logger.info(f"🚀 开始执行选中用例，共 {len(test_case_list)} 条")
        report_type = run_config['REPORT_TYPE'].upper()

        if report_type == 'ALLURE':
            pytest.main(['-v', f'--alluredir={BP.ALLURE_RESULT_PATH}', *test_case_list])

            if not _build_allure_report(BP.ALLURE_RESULT_PATH, BP.ALLURE_REPORT_PATH):
                return

            # 只有发邮件时才打包，本地看报告直接打开 index.html 就行
            if run_config.get("IS_EMAIL", "").strip().lower() == "yes":
                _create_allure_viewer_bat(BP.ALLURE_REPORT_PATH)
                _zip_allure_report(BP.ALLURE_REPORT_PATH)
            else:
                # 清理旧文件，防止用户误以为有 zip 可以发
                old_bat = os.path.join(BP.ALLURE_REPORT_PATH, "双击查看报告.bat")
                old_zip = os.path.join(os.path.dirname(BP.ALLURE_REPORT_PATH), "allure_report.zip")
                for f in [old_bat, old_zip]:
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                            logger.info(f"🧹 未发邮件，清理旧文件：{f}")
                        except Exception:
                            pass

            file_all_delete(BP.ALLURE_RESULT_PATH)

        elif report_type == 'HTML':
            html_report = os.path.join(BP.HTML_PATH, 'auto_reports.html')
            _build_html_report(test_case_list, html_report)

        elif report_type == 'XML':
            xml_report = os.path.join(BP.XML_PATH, 'auto_reports.xml')
            _build_xml_report(test_case_list, xml_report)

        else:
            logger.error(f"❌ 不支持的报告类型：{report_type}")
            return

        _send_report_email(report_type)
        logger.info("🎉 自动化测试执行完毕！")

    except FileNotFoundError:
        # 这个 FileNotFoundError 只可能是 TESTCASES_PATH（用例选择文件）不存在
        # 因为用户没选过用例，或者选择器没正常退出
        # 此时降级为跑全量用例，而不是直接报错退出
        # 注意：这里不能捕获太宽泛，否则会误吞 Allure 生成失败的异常
        logger.warning("⚠️ 未找到用例选择文件，执行项目全量用例")
        test_project_path = os.path.join(BP.TEST_SUITS_PATH, run_config['TEST_PROJECT'])
        html_report = os.path.join(BP.HTML_PATH, 'auto_reports.html')
        pytest.main(['-v', f'--html={html_report}', '--self-contained-html', test_project_path])

    except Exception as e:
        logger.error(f"💥 用例执行异常：{str(e)}", exc_info=True)

def run_app(target_func, *args):
    app = multiprocessing.Process(target=target_func, args=args)
    app.start()
    app.join()

if __name__ == "__main__":
    with multiprocessing.Manager() as manager:
        collect_result = manager.Value(ctypes.c_bool, False)

        logger.info("🔍 正在收集测试用例，请稍候...")
        run_app(run_collect_testcase, collect_result)

        if not collect_result.value:
            logger.error("❌ 用例收集失败，程序退出")
            sys.exit(1)

        logger.info("✅ 用例收集完成，启动用例选择器")
        run_app(run_case_selector)

        run_main()