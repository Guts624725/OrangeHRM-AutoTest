"""
@Author  : 谢胜强
@Time    : 2026/5/28 14:18
@Desc    : 完全适配你框架 OrangeHRM 5.x 接口登录（带CSRF Token）
"""
import random
import string
import requests
import re
from Base.baseAutoHttp import ApiBase
from Base.baseLogger import Logger

lg = Logger("web_login_page.py").get_logger()
BASE_URL = "http://127.0.0.1:8080"

def _extract_token(html: str) -> str:
    token_match = re.search(r':token="([^"]+)"', html)
    if not token_match:
        raise ValueError("无法从页面提取 CSRF Token")
    return token_match.group(1).replace("&quot;", "").replace('"', '').strip()


class LoginPage01(ApiBase):
    """管理员正常登录"""
    def __init__(self):
        super().__init__("01登录页面接口信息")

    def login(self, username, password):
        try:
            login_page_url = f"{BASE_URL}/web/index.php/auth/login"
            resp_page = self.session.get(login_page_url)
            csrf_token = _extract_token(resp_page.text)
            print("✅ 成功获取动态 CSRF Token：", csrf_token[:60])

            change_data = {
                "_token": csrf_token,
                "username": username,
                "password": password
            }
            res = self.request_base("login_api", change_data)

            assert "dashboard" in res.url, "断言失败：没有成功进入用户界面"
            assert res.status_code == 200, "断言失败：状态码不是200"
            assert "invalid_csrf_token" not in res.text, "断言失败：存在CSRF令牌错误"
            lg.info("【管理员正常登录】断言成功")
        finally:
            self.close_session()


class LoginPage02(ApiBase):
    """未携带CSRF令牌"""
    def __init__(self):
        super().__init__("02登录页面未携带token")

    def login(self, username, password):
        try:
            login_page_url = f"{BASE_URL}/web/index.php/auth/login"
            self.session.get(login_page_url)  # 仅获取 Cookie，不提取 Token

            change_data = {
                "username": username,
                "password": password
            }
            res = self.request_base("login_not_token_api", change_data)

            assert res.status_code == 200, f"断言失败：状态码应为200，实际为{res.status_code}"
            assert "invalid_csrf_token" in res.text, "断言失败：未返回CSRF错误"
            assert "dashboard" not in res.url, "断言失败：登录异常成功"
            lg.info("【未携带CSRF令牌】断言成功")
        finally:
            self.close_session()


class LoginPage03(ApiBase):
    """跨会话使用Token（模拟无效Token）"""
    def __init__(self):
        super().__init__("01登录页面接口信息")

    def login(self, username, password):
        # 会话A：获取 Token
        session1 = requests.Session()
        try:
            resp1 = session1.get(f"{BASE_URL}/web/index.php/auth/login")
            csrf_token = _extract_token(resp1.text)
            print(f"✅ 会话A获取Token：{csrf_token[:50]}...")
        finally:
            session1.close()

        # 会话B（self.session）：使用会话A的 Token
        try:
            self.session.get(f"{BASE_URL}/web/index.php/auth/login")
            change_data = {
                "_token": csrf_token,
                "username": username,
                "password": password
            }
            res = self.request_base("login_api", change_data)

            assert res.status_code == 200, f"断言失败：状态码应为200，实际为{res.status_code}"
            assert "invalid_csrf_token" in res.text, "断言失败：未返回CSRF错误"
            assert "dashboard" not in res.url, "断言失败：登录异常成功"
            lg.info("【跨会话使用Token】断言成功")
        finally:
            self.close_session()


class LoginPage04(ApiBase):
    """携带错误格式Token"""
    def __init__(self):
        super().__init__("01登录页面接口信息")

    def login(self, username, password):
        try:
            wrong_token = "".join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=20))
            print(f"✅ 生成错误格式Token：{wrong_token}")

            change_data = {
                "_token": wrong_token,
                "username": username,
                "password": password
            }
            res = self.request_base("login_api", change_data)

            assert res.status_code == 200, f"断言失败：状态码应为200，实际为{res.status_code}"
            assert "invalid_csrf_token" in res.text, "断言失败：未返回CSRF错误"
            assert "dashboard" not in res.url, "断言失败：登录异常成功"
            lg.info("【携带错误格式Token】断言成功")
        finally:
            self.close_session()


class LoginPage05(ApiBase):
    """错误用户名/密码/空值"""
    def __init__(self):
        super().__init__("01登录页面接口信息")

    def login(self, username, password):
        try:
            resp_page = self.session.get(f"{BASE_URL}/web/index.php/auth/login")
            csrf_token = _extract_token(resp_page.text)

            change_data = {
                "_token": csrf_token,
                "username": username,
                "password": password
            }
            res = self.request_base("login_api", change_data)

            assert res.status_code == 200, f"断言失败：状态码应为200，实际为{res.status_code}"
            assert "dashboard" not in res.url, "断言失败：登录异常成功"
            assert "Invalid credentials" in res.text, "断言失败：未返回错误凭据提示"
            lg.info(f"【{username or '空用户名'}/{password or '空密码'}】断言成功")
        finally:
            self.close_session()



if __name__ == '__main__':
    # 创建登录页面对象
    login_page = LoginPage01()

    # 调用登录方法
    res = login_page.login("admin", "Keepmoving624.")

    # ====================== 登录结果判断（核心标准） ======================
    print("\n===== 登录结果 =====")

    # 成功：URL 跳转到 dashboard（仪表盘）
    if "dashboard" in res.url:
        print("✅ ✅ ✅ 登录成功！进入仪表盘！")

    # 失败：CSRF 令牌错误（token 无效/为空）
    elif "invalid_csrf_token" in res.text:
        print("❌ 失败：CSRF 令牌错误")

    # 失败：账号或密码错误
    elif "Invalid credentials" in res.text:
        print("❌ 失败：账号密码错误")

    # 其他原因失败
    else:
        print("❌ 失败：未知原因")