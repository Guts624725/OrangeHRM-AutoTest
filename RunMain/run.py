"""
@Author  : 谢胜强
@Time    : 2026/5/8 22:39
@Desc    : 自动化测试框架主运行入口（非GUI版）
"""
import os
import sys
import subprocess
import shutil

# 把项目根目录加到 sys.path，不然 import Base.xxx 会报 ModuleNotFound
# 这里往上退两级，因为 run.py 通常在项目根目录下，__file__ 是 run.py 的绝对路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from Base.basePath import BasePath as BP
from Base.utils import read_config_ini, file_all_delete
from Base.baseContainer import GlobalManager
from Base.baseSendEmail import HandleEmail
from Base.baseLogger import Logger

logger = Logger("run.py").getLogger()
config = read_config_ini(BP.CONFIG_FILE_PATH)
gm = GlobalManager()

# 把配置和驱动路径存到全局变量，方便后续模块（比如数据驱动、页面对象）直接取
# 不用每个模块都自己读一次配置文件，省 IO 也保证配置一致性
gm.set_value("CONFIG_INFO", config)
data_driver_type = config["项目运行配置"]["DATA_DRIVER_TYPE"]
data_driver_path = os.path.join(BP.DATA_DRIVER_PATH, data_driver_type)
gm.set_value("DATA_DRIVER_PATH", data_driver_path)
run_config = config["项目运行配置"]

# Allure 命令行工具的固定路径，目前写死在 D 盘
# 如果换电脑或者 Allure 升级了版本，这里要手动改
# 后续可以考虑从配置文件里读，或者从环境变量 ALLURE_HOME 取
ALLURE_BIN = r"D:\Allure\allure-2.42.0\bin"
ALLURE_CMD = os.path.join(ALLURE_BIN, "allure.bat")


def _ensure_allure_in_path() -> None:
    """临时把 Allure 加到当前进程的 PATH 环境变量"""
    current_path = os.environ.get("PATH", "")
    if ALLURE_BIN not in current_path:
        # os.environ 只影响当前进程，不会改系统环境变量
        # 所以每次运行都要调一次，但这样比让用户手动配 PATH 省事
        os.environ["PATH"] = ALLURE_BIN + os.pathsep + current_path


def _clean_old_reports() -> None:
    """清理上一轮测试留下的报告文件"""
    paths = [BP.ALLURE_RESULT_PATH, BP.ALLURE_REPORT_PATH, BP.HTML_PATH, BP.XML_PATH]
    for path in paths:
        try:
            file_all_delete(path)
        except Exception as e:
            # 目录不存在或者权限问题时不阻断，打个 warning 继续
            logger.warning(f"⚠️ 清理旧报告时跳过 {path}：{e}")
    logger.info("🧹 旧报告清理完成")


def _build_allure_report(result_path: str, report_path: str) -> bool:
    """调用 Allure CLI 生成静态 HTML 报告"""
    _ensure_allure_in_path()

    if not os.path.exists(ALLURE_CMD):
        logger.error(f"❌ Allure 命令行工具不存在：{ALLURE_CMD}")
        return False

    try:
        # capture_output=True 把 stdout/stderr 捕获到 Python 里，不直接打印到控制台
        # check=True 表示命令返回非 0 时自动抛 CalledProcessError
        subprocess.run(
            [ALLURE_CMD, "generate", result_path, "-o", report_path, "--clean"],
            capture_output=True, text=True, check=True
        )
        logger.info(f"✅ Allure报告生成成功：{report_path}")
        return True
    except subprocess.CalledProcessError as e:
        # Allure 生成失败通常是因为 result 目录里的数据格式不对（比如 pytest 没跑完就中断了）
        logger.error(f"❌ Allure 报告生成失败：\n{e.stderr}")
        return False
    except FileNotFoundError:
        # 虽然前面判断了 ALLURE_CMD 存在，但 subprocess 还是可能找不到（比如权限问题）
        logger.error(f"❌ 无法调用 Allure，请确认已安装：{ALLURE_CMD}")
        return False


def _create_allure_viewer_bat(report_path: str) -> None:
    """
    生成一个 bat 脚本，双击就能用浏览器打开 Allure 报告
    Allure 报告是静态 HTML，直接双击 index.html 会因为浏览器的 CORS 策略加载不出数据
    这个脚本用 --allow-file-access-from-files 参数启动浏览器，绕过本地文件访问限制
    """
    bat_content = r'''@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 Allure 报告查看器...

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

echo 报告已打开，关闭浏览器即可。
timeout /t 3 >nul
'''
    bat_path = os.path.join(report_path, "双击查看报告.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    logger.info(f"✅ 报告查看器已生成：{bat_path}")


def _zip_allure_report(report_path: str) -> str:
    """把 Allure 报告压缩成 zip，方便邮件发送"""
    # 先清理旧的 zip，避免邮件附件越来越大
    for item in os.listdir(report_path):
        if item.lower().endswith('.zip'):
            old_zip = os.path.join(report_path, item)
            try:
                os.remove(old_zip)
            except Exception:
                pass

    # shutil.make_archive 如果目标文件已存在会报错，所以先删
    zip_base = os.path.join(os.path.dirname(report_path), "allure_report")
    if os.path.exists(zip_base + ".zip"):
        os.remove(zip_base + ".zip")

    zip_path = shutil.make_archive(zip_base, 'zip', report_path)
    logger.info(f"✅ 报告压缩包已生成：{zip_path}")
    return zip_path


def _send_email(report_type: str) -> None:
    """根据配置决定是否发送测试报告邮件"""
    if run_config.get("IS_EMAIL", "").strip().lower() != "yes":
        return
    try:
        email = HandleEmail()
        email_text = "本邮件由系统自动发出,无需回复!\n各位同事,大家好,以下为本次测试报告!"
        email.send_public_email(text=email_text, filetype=report_type)
        logger.info("📧 测试报告邮件发送成功")
    except Exception as e:
        logger.error(f"📧 邮件发送失败：{str(e)}")


def run_main():
    try:
        test_project = run_config["TEST_PROJECT"].strip()
        test_case_path = os.path.join(BP.TEST_SUITS_PATH, test_project)

        if not os.path.exists(test_case_path):
            logger.error(f"❌ 测试用例目录不存在：{test_case_path}")
            return

        logger.info(f"🚀 开始执行自动化测试，项目：{test_project}")
        logger.info(f"📊 报告类型：{run_config['REPORT_TYPE']}")

        _clean_old_reports()

        report_type = run_config["REPORT_TYPE"].upper()

        if report_type == "ALLURE":
            # pytest 在函数内部 import，避免模块加载时就依赖 pytest
            # 这样即使没装 pytest，框架也能启动（只是跑不了用例）
            import pytest
            pytest.main(["-v", f"--alluredir={BP.ALLURE_RESULT_PATH}", test_case_path])

            if not _build_allure_report(BP.ALLURE_RESULT_PATH, BP.ALLURE_REPORT_PATH):
                return

            # 只有发邮件的时候才生成 bat 和 zip，因为邮件附件需要 zip
            # 如果不发邮件，本地直接看 Allure 报告就行，不需要这些额外文件
            if run_config.get("IS_EMAIL", "").strip().lower() == "yes":
                _create_allure_viewer_bat(BP.ALLURE_REPORT_PATH)
                _zip_allure_report(BP.ALLURE_REPORT_PATH)
            else:
                # 不发邮件时清理上次残留的 bat 和 zip，保持目录干净
                old_bat = os.path.join(BP.ALLURE_REPORT_PATH, "双击查看报告.bat")
                old_zip = os.path.join(os.path.dirname(BP.ALLURE_REPORT_PATH), "allure_report.zip")
                for f in [old_bat, old_zip]:
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                            logger.info(f"🧹 未发邮件，清理旧文件：{f}")
                        except Exception:
                            pass

            # 生成完静态报告后，result 目录（原始 JSON 数据）就可以删了
            # 留着占空间，而且下次跑会重复生成
            file_all_delete(BP.ALLURE_RESULT_PATH)
            logger.info(f"✅ Allure报告生成成功：{BP.ALLURE_REPORT_PATH}")

        elif report_type == "HTML":
            import pytest
            html_report = os.path.join(BP.HTML_PATH, "auto_reports.html")
            # --self-contained-html 把 CSS/JS 都内联到 HTML 里，单文件就能看，不用依赖外部资源
            pytest.main(["-v", f"--html={html_report}", "--self-contained-html", test_case_path])
            logger.info(f"✅ HTML报告生成成功：{html_report}")

        elif report_type == "XML":
            import pytest
            xml_report = os.path.join(BP.XML_PATH, "auto_reports.xml")
            pytest.main(["-v", f"--junitxml={xml_report}", test_case_path])
            logger.info(f"✅ XML报告生成成功：{xml_report}")

            # XML 是机器读的，顺便转成 HTML 方便人看
            try:
                html_report = os.path.join(BP.XML_PATH, "auto_reports.html")
                subprocess.run(["junit2html", xml_report, html_report], check=True, capture_output=True)
                logger.info(f"✅ XML转HTML成功：{html_report}")
            except FileNotFoundError:
                # junit2html 是可选依赖，没装就跳过，不影响主流程
                logger.warning("⚠️ 未安装junit2html，执行：pip install junit2html")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ XML转HTML失败：{e}")

        else:
            logger.error(f"❌ 不支持的报告类型：{report_type}")
            return

        _send_email(report_type)
        logger.info("🎉 自动化测试执行完成！")

    except Exception as e:
        # exc_info=True 保留完整堆栈，框架级异常必须看堆栈才能定位
        logger.error(f"💥 框架运行异常：{str(e)}", exc_info=True)
        raise


if __name__ == '__main__':
    run_main()