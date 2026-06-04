"""
@Author  : 谢胜强
@Time    : 2026/5/14 16:43
@Desc    : 将登录页面前置,以便测试其他功能
"""
import pytest

from PageObject.ohrm_test.web_login_page import LoginPage

@pytest.fixture(scope="function")
def info_login():
    log = LoginPage(username="admin", password="Keepmoving624.")
    log.login()

@pytest.fixture(scope="function")
def info_login1():
    log = LoginPage(username="lisisi", password="Keepmoving624.")
    log.login()

