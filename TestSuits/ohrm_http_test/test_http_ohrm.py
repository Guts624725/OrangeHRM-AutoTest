"""
@Author  : 谢胜强
@Time    : 2026/5/28 16:27
@Desc    : 
"""

import pytest

from Base.baseData import DataDriver
from Base.baseLogger import Logger
from Base.utils import read_config_ini
from Base.basePath import BasePath as BP
from PageObject.ohrm_http_test.api_employee_page import Employee, UpdateEmployee, DeleteEmployee, LoginOutEmployee, \
    EmployeeLogin
from PageObject.ohrm_http_test.api_login_page import LoginPage01, LoginPage02, LoginPage03, LoginPage04, LoginPage05

lg = Logger("test_web_ohrm.py").getLogger()


config = read_config_ini(BP.CONFIG_FILE_PATH)
username = config["login"]["username"]
password = config["login"]["password"]


"""登录模块"""
class TestCase01:

    """管理员正常登录"""
    def test_login_case01(self):
        log = LoginPage01()
        log.login(username, password)
        lg.info("【管理员正常登录】用例执行成功")

    """未携带CSRF令牌"""
    def test_login_case02(self):
        log = LoginPage02()
        log.login(username, password)
        lg.info("【未携带CSRF令牌】用例执行成功")

    """
    1.携带过期CSRF令牌
    2.跨会话使用Token
    """
    def test_login_case03(self):
        log = LoginPage03()
        log.login(username, password)
        lg.info("【携带过期CSRF令牌】用例执行成功")

    """携带错误格式Token"""
    def test_login_case04(self):
        log = LoginPage04()
        log.login(username, password)
        lg.info("【携带错误格式Token】用例执行成功")

    """
    1.错误用户名/密码
    2.用户名为空
    3.密码为空
    """
    @pytest.mark.parametrize("test_case",DataDriver().get_case_data("01登录接口"))
    def test_login_case05(self, test_case):
        log = LoginPage05()
        log.login(test_case["username"], test_case["password"])
        lg.info(f"【{test_case['test_name']}】用例执行成功")


"""员工管理"""
class TestEmployee:

    """新增员工 - 正向"""
    def test_employee01(self, login_session, db_help):
        session, url = login_session
        employee = Employee(session, url)
        emp = employee.add_employee("zz", "ss", "1009")
        assert emp.status_code == 200, f"断言失败，状态码是{emp.status_code}"

        sql = "SELECT emp_firstname, emp_lastname, emp_number FROM hs_hr_employee WHERE emp_number = %s"
        # 🔥 关键：提取系统生成的 empNumber
        emp_number = emp.json()["data"]["empNumber"]
        print(f"系统生成的 empNumber: {emp_number}")
        result = db_help.mysql_db_select(sql, (emp_number,))
        assert result is not None, "所查询为空"
        assert result[0]["emp_firstname"] == "zx", f"firstname是{result[0]["emp_firstname"]}"
        lg.info("☑️数据库校验成功")

    """
        新增员工 - 缺少必填字段
        新增员工-员工ID已存在
    """
    @pytest.mark.parametrize("case_data",DataDriver().get_case_data("02添加员工接口"))
    def test_employee02(self, login_session,case_data):
        session, url = login_session
        employee = Employee(session, url)
        emp = employee.add_employee(case_data["firstName"], case_data["lastName"], case_data["employeeId"])
        if case_data["title"] == "新增员工-缺少必填字段":
            assert emp.status_code == 422,f"断言失败，状态码是{emp.status_code}"
            assert "Invalid" in emp.text,"断言失败：未返回错误凭据提示"
        elif case_data["title"] == "新增员工-员工ID已存在":
            assert emp.status_code == 422, f"断言失败，状态码是{emp.status_code}"
            assert "Invalid Parameter" in emp.text,"断言失败：未返回错误凭据提示"


    """查询员工列表"""
    def test_employee03(self, login_session):
        session, url = login_session
        employee = Employee(session, url)

        emp_list = employee.get_employee_list()
        assert emp_list.status_code == 200, f"断言失败，状态码是{emp_list.status_code}"

        data = emp_list.json()
        assert "data" in data, "断言失败：缺少 data 字段"

        employees = data["data"]
        assert isinstance(employees, list), "断言失败：data 不是数组"
        assert len(employees) > 0, "断言失败：员工列表为空"

        # 验证第一条数据格式
        first = employees[0]
        assert "empNumber" in first, "断言失败：缺少 empNumber"
        assert "employeeId" in first, "断言失败：缺少 employeeId"

        lg.info(f"☑️ 查询员工列表成功，返回 {len(employees)} 条")

    """查询指定员工"""
    @pytest.mark.parametrize("case_employeeId",DataDriver().get_case_data("03指定查询"))
    def test_employee04(self, login_session,case_employeeId):
        session, url = login_session
        employee = Employee(session, url)
        resp = employee.select_query_employee(case_employeeId["employeeId"])
        data = resp.json()
        assert resp.status_code == 200, f"实际状态码是{resp.status_code}"
        if case_employeeId["id"] == 1:
            emp = data["data"][0]
            assert emp["firstName"] == "John",f"查询的第一个姓名是{emp['firstName']}"
            assert emp["lastName"] == "Doe",f"查询的{emp['lastName']}"
        elif case_employeeId["id"] == 2:
            assert data["data"] == [] ,"内容不为空，查询错误"
        lg.info("☑️【指定查询用例】执行完毕")


    """编辑指定员工"""
    def test_employee05(self, login_session, db_help):
        session, url = login_session
        employee = UpdateEmployee(session, url)
        sql1 = "SELECT emp_firstname, emp_lastname FROM hs_hr_employee WHERE employee_id = %s"
        result1 = db_help.mysql_db_select(sql1,("1001",))
        lastname1 = result1[0]["emp_lastname"]
        employee.update_employee("John", "Doe","1001")
        sql2 = "UPDATE hs_hr_employee SET emp_lastname = %s WHERE employee_id = %s"
        result2 = db_help.mysql_db_operate(sql2,("Doe","1001"))
        result1 = db_help.mysql_db_select(sql1, ("1001",))
        lastname2 = result1[0]["emp_lastname"]
        assert lastname1 != lastname2 and lastname2 == "Doe",f"断言失败lastname={lastname2}"
        lg.info("☑️【编辑已存在员工】用例执行成功")


    """删除员工"""
    @pytest.mark.parametrize("delete_case",DataDriver().get_case_data("04删除员工"))
    def test_employee06(self, login_session, db_help, delete_case):
        session, url = login_session
        employee1 = Employee(session, url)
        employee = DeleteEmployee(session, url)
        data = employee1.select_query_employee(delete_case["employee_id"])
        assert data.status_code == 200, f"查不到employee_id:{delete_case['employee_id']}的员工"
        sql = "SELECT emp_firstname, emp_lastname, emp_number FROM hs_hr_employee WHERE employee_id = %s"
        result = db_help.mysql_db_select(sql,(delete_case["employee_id"],))

        if delete_case["title"] == "删除存在员工":
            id = result[0]["emp_number"]
            employee.delete_employee(id)
            data = employee1.select_query_employee(delete_case["employee_id"])
            assert data.status_code == 200, "查询异常，查到了已经删除的员工"
            result1 = db_help.mysql_db_select(sql, (delete_case["employee_id"],))
            assert result1 == [], "删除失败"

        elif delete_case["title"] == "删除不存在员工":
            assert result == [],"查询异常，数据库不该有该员工"

        lg.info("☑️【删除员工】用例执行成功")


    """未登录访问员工接口"""
    def test_employee07(self):

        base_url = config["项目运行配置"]["TEST_URL"]

        logout = LoginOutEmployee(base_url)
        resp = logout.login_out_employee()
        # 断言1：状态码 302
        assert resp.status_code == 302, f"断言失败：状态码应为302，实际是{resp.status_code}"

        # 断言2：响应头 Location 包含登录页地址
        location = resp.headers.get('Location', '')

        assert 'auth/login' in location or 'login' in location, f"断言失败：未跳转到登录页，Location: {location}"


    """非管理员账号操作员工"""
    def test_employee08(self,employee_login_session):
        session,url  = employee_login_session
        employee = EmployeeLogin(session,url)
        resp = employee.employee_login("cc","dd","1010")
        assert resp.status_code == 403,"断言失败，没有添加员工功能操作成功"
        assert "Unauthorized" in resp.text
        lg.info("☑️【非管理员账号操作员工】用例执行成功")