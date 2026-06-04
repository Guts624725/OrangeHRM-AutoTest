"""
@Author  : 谢胜强
@Time    : 2026/5/31 20:30
@Desc    : 
"""
import re
import html as html_module
import requests


def login_as(session: requests.Session, url: str, username: str, password: str):
    """
    通用登录：admin 或普通员工都能用
    返回登录后的 session（已激活，可直接调用 API）
    """
    # 1. GET 登录页（获取 token + 初始 Cookie）
    login_page_url = f"{url}/web/index.php/auth/login"
    resp_page = session.get(login_page_url)

    # 提取 token（兼容 &quot; 转义）
    token_match = re.search(r':token="([^"]+)"', resp_page.text)
    if not token_match:
        raise Exception("未提取到 _token")

    csrf_token = token_match.group(1)
    csrf_token = html_module.unescape(csrf_token).replace('"', '').strip()

    # 2. POST 登录
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": login_page_url,
        "Origin": url,
    }
    data = {
        "_token": csrf_token,
        "username": username,
        "password": password
    }

    resp = session.post(
        f"{url}/web/index.php/auth/validate",
        headers=headers,
        data=data,
        allow_redirects=False
    )

    # 3. 跟随 302 到 Dashboard，激活 Session
    if resp.status_code == 302:
        location = resp.headers.get('Location')
        session.get(location, headers={"Referer": login_page_url})
    else:
        raise Exception(f"登录失败，状态码：{resp.status_code}，响应：{resp.text[:200]}")

    return session