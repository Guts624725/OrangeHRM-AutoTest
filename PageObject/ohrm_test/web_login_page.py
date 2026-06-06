"""
@Author  : 谢胜强
@Time    : 2026/5/13 00:57
@Desc    : 登录页面业务封装
"""
import time
from Base.baseAutoWeb import WebBase
from Base.baseLogger import Logger
from Base.basePath import BasePath as BP
from Base.utils import read_config_ini
from Base.baseContainer import GlobalManager

# 🔥 修复：Logger标准方法名 get_logger()
logger = Logger("01登录页面接口信息.yaml").get_logger()

class LoginPage(WebBase):
    """登录页面业务类"""
    def __init__(self, username, password):
        # 初始化父类，传入元素配置文件名称
        super().__init__("01登录页面元素信息")
        self.username = username
        self.password = password

    def login(self):
        """登录业务方法"""
        logger.info("========== 开始执行 OrangeHRM 登录操作 ==========")
        # 获取测试地址并打开
        test_url = read_config_ini(BP.CONFIG_FILE_PATH)["项目运行配置"]["TEST_URL"]
        self.get_url(test_url)

        time.sleep(2)
        # 输入用户名
        self.click("login/username")
        self.clear("login/username")
        self.sendKeys("login/username", self.username)
        time.sleep(1)

        # 输入密码
        self.click("login/password")
        self.clear("login/password")
        self.sendKeys("login/password", self.password)
        time.sleep(1)

        # 点击登录按钮
        self.click("login/loginbtn")
        logger.info("========== OrangeHRM 登录操作执行完成 ==========")

    def logout(self):
        """登出业务方法"""
        self.click("header/user_dropdown")
        time.sleep(3)
        self.click("header/logout_link")
        time.sleep(1)
        logger.info("========== 账号登出成功 ==========")

    def assert_login_ok(self, flag):
        """登录结果断言
        :param flag: 1-登录成功 2-密码错误 3-空账号密码 4-小写密码 5-cookie自动登录 6-会话超时 7-登出安全校验
        """
        if flag == "1":
            # 登录成功断言
            val = self.get_text("login/yibiao")
            admval = self.get_text("login/adminname")
            assert val == "仪表盘", f"【断言失败】期望页面：仪表盘，实际：{val}"
            assert admval == "谢 安", f"【断言失败】期望管理员：谢 安，实际：{admval}"
            logger.info("✅ 登录成功断言通过")

        elif flag == "2":
            # 密码错误：保留用户名，清空密码
            error_text = self.get_text("login/error")
            password_val = self.findElement("login/password").get_attribute("value")
            assert "Invalid credentials" in error_text, f"【断言失败】错误信息：{error_text}"
            assert "auth/login" in self.driver.current_url, f"【断言失败】未在登录页"
            assert password_val == "", "【断言失败】密码未清空"
            logger.info("✅ 密码错误断言通过")

        elif flag == "3":
            # 空账号密码断言
            userval = self.username
            pwdval = self.password
            needval = self.get_text("login/need")
            assert userval == "", f"【断言失败】用户名不为空：{userval}"
            assert pwdval == "", f"【断言失败】密码不为空：{pwdval}"
            assert needval == "需要", f"【断言失败】提示信息错误：{needval}"
            logger.info("✅ 空账号密码断言通过")

        elif flag == "4":
            # 小写密码错误断言
            error_text = self.get_text("login/error")
            assert "Invalid credentials" in error_text, f"【断言失败】错误信息：{error_text}"
            logger.info("✅ 小写密码错误断言通过")

        elif flag == "5":
            # Cookie自动登录断言
            assert self.get_text("login/yibiao") == "仪表盘", "❌ Cookie注入自动登录失败"
            logger.info("✅ Cookie自动登录断言通过")

        elif flag == "6":
            # 会话超时断言
            error_text = self.get_text("login/session_error")
            assert error_text, "❌ 未找到会话超时提示"
            assert "session" in error_text.lower(), f"❌ 会话提示错误：{error_text}"
            logger.info("✅ 会话超时断言通过")

        elif flag == "7":
            # 登出后安全断言
            current_url = self.driver.current_url
            assert "login" in current_url, f"❌ 登出后未跳转登录页：{current_url}"
            logger.info("✅ 登出后安全断言通过")

        else:
            logger.error(f"❌ 不支持的断言类型：{flag}")
            raise ValueError(f"不支持的断言标识：{flag}")


if __name__ == '__main__':
    # 🔥 修复：框架统一驱动管理，删除硬编码路径
    from selenium import webdriver
    # 初始化浏览器驱动（自动匹配版本，无需指定exe路径）
    driver = webdriver.Chrome()
    # 存入全局管理器，供父类调用
    GlobalManager().set_value("driver", driver)
    # 执行登录
    login = LoginPage("admin", "Keepmoving624.")
    login.login()