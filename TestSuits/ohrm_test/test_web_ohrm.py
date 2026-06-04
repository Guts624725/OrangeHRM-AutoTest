"""
@Author  : 谢胜强
@Time    : 2026/5/13 15:58
@Desc    : OrangeHRM Web自动化测试用例
"""

import pytest

from Base.baseData import DataDriver
from Base.baseLogger import Logger

# 页面对象
from PageObject.ohrm_test.web_login_page import LoginPage
from PageObject.ohrm_test.web_upworker_page import UpWorker, UpdateBirth, AssertWorker, SelWorker, DelChect, Vacation, \
    Punch, Create

logger = Logger("test_web_ohrm.py").get_logger()


"""web自动化-OrangerHRM-登录功能模块"""
class TestCase01:
    """web自动化-OrangerHRM-登录功能模块"""

    @pytest.mark.parametrize("case_data", DataDriver().get_case_data("01登录功能"))
    def test_login_case01(self, driver, case_data):
        # 1. 初始化登录页面
        lp = LoginPage(case_data["username"], case_data["password"])
        # 2. 执行登录
        lp.login()
        # 3. 执行断言
        lp.assert_login_ok(case_data["flag"])
        logger.info(f"✅ 登录用例执行完成，断言标识：{case_data['flag']}")


"""web自动化-OrangerHRM-PIM员工管理模块"""
class TestCase02:

    """添加/校验员工信息（正向+负向用例）"""
    @pytest.mark.parametrize("case_data", DataDriver().get_case_data("02修改员工信息功能"))
    def test_update_case01(self, driver, info_login, case_data):
        """添加/校验员工信息（正向+负向用例）"""
        logger.info("========== 开始执行【添加员工信息】用例 ==========")

        # 初始化员工添加类
        uw = UpWorker(
            firename=case_data["FireName"],
            lastname=case_data["LastName"],
            worker_id=case_data["ID"]
        )
        # 执行添加
        uw.add_worker()
        # 初始化断言类
        ass = AssertWorker()
        # 执行断言
        ass.assert_up_flag(flag=case_data["flag"])
        logger.info("✅ 【添加员工信息】用例执行完成")

    """编辑员工生日信息"""
    def test_update_case02(self, driver, info_login):
        """编辑员工生日信息"""
        logger.info("========== 开始执行【修改员工生日】用例 ==========")
        # 初始化生日修改类
        ub = UpdateBirth()
        # 执行修改
        ub.test_select_birth_date(sel_name="Shengqiang", birth_date="1995-01-01")
        # 断言类实例化
        ass = AssertWorker()
        # 执行断言
        ass.assert_up_flag("3")
        logger.info("✅ 【修改员工生日】用例执行完成")

    """添加新员工输入已经存在的识别号"""
    def test_addexist_case03(self, driver, info_login):
        """添加新员工输入已经存在的识别号"""
        ub = UpdateBirth()
        ub.add_existing("202501")
        ass = AssertWorker()
        ass.assert_up_flag("4")
        logger.info("✅ 【添加新员工输入已经存在的识别号】用例执行完成")

    """搜索员工姓名"""
    def test_selectname_case04(self, driver, info_login):
        """搜索员工姓名"""
        # 断言初始化
        ass = AssertWorker()
        # SelWorker初始化
        sl = SelWorker()
        # 执行只输入Xie查询
        sl.sel_worker("Xie")
        ass.assert_up_flag("5")
        logger.info("✅ 【搜索员工】用例执行完成")

    """搜索员工id"""
    def test_selectid_case05(self, driver, info_login):
        """搜索员工id"""
        # 断言初始化
        ass = AssertWorker()
        # SelWorker初始化
        sl = SelWorker()
        sl.sel_userid("202501")
        ass.assert_up_flag("6")
        logger.info("✅ 【搜索员工的识别号】用例执行完成")

    """勾选指定员工进行删除"""
    def test_delworker_case06(self, driver, info_login):
        """勾选指定员工进行删除"""
        # 断言初始化
        ass = AssertWorker()
        dell = DelChect()
        # dell.delchect(["0086","0087"])
        dell.delchect(["金刚"])
        ass.assert_up_flag("7")
        logger.info("✅ 【勾选指定员工删除】用例执行完成")


"""web自动化-OrangerHRM-Leave员工请假模块"""
class TestCase03:

    """
        员工申请假期
        员工假期不足
    """
    def test_vacation_case01(self, driver, info_login1):
        va = Vacation()
        va.ask_for_leave(starttime="2026-06-10", endtime="2026-06-12",comments="家庭假期")
        ass = AssertWorker()
        # ass.assert_up_flag("8")
        # logger.info("✅ 【员工申请请假】用例执行完成")
        ass.assert_up_flag("11")
        logger.info("✅ 【员工假期余额不足】用例执行完成")

    """管理员批准假期"""
    def test_vacation_case02(self, driver, info_login):
        va = Vacation()
        va.approved_holiday(selname="四四 李")
        ass = AssertWorker()
        ass.assert_up_flag("9")
        logger.info("✅ 【管理员批准假期】用例执行完成")

    """管理员拒绝请假"""
    def test_vacation_case03(self, driver, info_login):
        va = Vacation()
        va.refuse_holiday(selname="四四 李")
        ass = AssertWorker()
        ass.assert_up_flag("10")
        logger.info("✅ 【管理员拒绝批准假期】用例执行完成")

"""web自动化-OrangerHRM-Time员工打卡模块"""
class TestCase04:

    def test_gowork_case01(self, driver, info_login1):
        pun = Punch()
        pun.gowork()
        ass = AssertWorker()
        ass.assert_up_flag("12")
        logger.info("✅ 【员工上班打卡】用例执行完成")

    def test_offwork_case02(self, driver, info_login1):
        pun = Punch()
        pun.offwork()
        ass = AssertWorker()
        ass.assert_up_flag("13")
        logger.info("✅ 【员工下班打卡】用例执行完成")

"""web自动化-OrangerHRM-Admin创建员工模块"""
class TestCase05:

    """创建新用户并分配角色"""
    def test_create_case01(self,driver, info_login):
        cr = Create()
        cr.create(role='ESS',state='启用',name='三',username='testuser',password='Test@1234JJ')
        ass = AssertWorker()
        ass.assert_up_flag("14")
        logger.info("✅ 【管理员创建用户】用例执行完成")


    """禁用用户后登录验证"""
    def test_create_case02(self,driver, info_login):
        cr = Create()
        # cr.update_verify(state="禁用",name= "三",username="testuser",password="Test@1234JJ",logout="登出")
        cr.update_verify(state="禁用",name= "三")
        ass = AssertWorker()
        ass.assert_up_flag("15")
        logger.info("✅ 【管理员禁用用户】用例执行完成")

    def test_verify(self,driver):
        from PageObject.ohrm_test.web_login_page import LoginPage

        LoginPage(username="testuser",password="Test@1234JJ").login()
        ass = AssertWorker()
        ass.assert_up_flag("16")
        logger.info("✅ 【管理员禁用用户】用例执行完成")






