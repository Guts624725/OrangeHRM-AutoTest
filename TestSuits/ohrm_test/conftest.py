"""
@Author  : 谢胜强
@Time    : 2026/5/14 16:43
@Desc    : 将登录页面前置,以便测试其他功能
"""
import pytest

from PageObject.ohrm_test.web_login_page import LoginPage
from Base.utils import read_config_ini
from Base.basePath import BasePath as BP

config = read_config_ini(BP.CONFIG_FILE_PATH)

@pytest.fixture(scope="function")
def info_login():
    log = LoginPage(
        username=config.get("login", "username", fallback="admin"),
        password=config.get("login", "password", fallback="******")
    )
    log.login()

@pytest.fixture(scope="function")
def info_login1():
    log = LoginPage(
        username="lisisi",
        password=config.get("login", "password", fallback="******")
    )
    log.login()

