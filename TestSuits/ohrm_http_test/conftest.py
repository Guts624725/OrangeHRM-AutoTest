"""
@Author  : 谢胜强
@Time    : 2026/5/29 22:55
@Desc    : 
"""
import pytest
import requests
from Base.baseLogger import Logger
from Base.utils import read_config_ini
from Base.basePath import BasePath as BP
from ExtTools.dbbase import MysqlHelp


config = read_config_ini(BP.CONFIG_FILE_PATH)
url = config["项目运行配置"]["TEST_URL"].rstrip('/')

lg = Logger("conftest").get_logger()

from TestSuits.ohrm_http_test.entry import login_as
"""管理员登录"""
@pytest.fixture(scope="session", name="login_session")
def login():
    print("\n✅ 【全局前置】管理员登录中...")
    session = requests.Session()
    # 🔥 调用通用登录
    # login_as(session, url, "admin", "Keepmoving624.")
    login_as(
        session,
        url,
        username=config.get("login", "username", fallback="admin"),
        password=config.get("login", "password", fallback="******")
    )
    print("✅ 登录成功，session 已准备好")
    yield session, url
    print("\n✅ 所有用例执行完毕，会话关闭")

"""非管理员登录"""
@pytest.fixture(scope="session", name="employee_login_session")
def employee_login():
    print("\n✅ 【全局前置】管理员登录中...")
    session = requests.Session()
    # 🔥 调用通用登录
    login_as(
        session,
        url,
        "kkkkk",
        password=config.get("login", "password", fallback="******")
    )
    print("✅ 登录成功，session 已准备好")
    yield session,url
    print("\n✅ 所有用例执行完毕，会话关闭")

@pytest.fixture(scope="session")
def db_help():
    db = MysqlHelp()
    db.create_connection()
    lg.info("✅ conftest: 获取数据库连接（MysqlHelp）")
    yield db

    if db.connection and not getattr(db.connection, '_closed', False):
        db.connection.close()
        lg.info("🔌 conftest: 数据库连接已关闭")


