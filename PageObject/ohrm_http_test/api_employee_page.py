"""
@Author  : 谢胜强
@Time    : 2026/5/29 22:54
@Desc    : OrangeHRM 员工模块接口封装
"""

from Base.baseAutoHttp import ApiBase


"""员工基础操作：新增、查询"""
class Employee(ApiBase):

    def __init__(self, session, url):
        # 这里传 session 和 base_url 进来，而不是在基类里统一管
        # 是因为员工模块的接口需要登录态，session 由登录流程创建后注入
        # 如果每个业务类都自己 new 一个 session，cookie 就断了
        super().__init__("03查询员工页面")
        self.session = session
        self.base_url = url

    def add_employee(self, firstName, lastName, employeeId):
        """
        新增员工
        注意：这个接口直接用了 self.session.post，没走 request_base
        原因是新增员工需要自定义 headers（Referer、Origin 校验），而 YAML 配置里不方便写动态 headers
        后续可以考虑把 headers 也放到 YAML 里，或者基类支持动态 header 注入
        """
        url = f"{self.base_url}/web/index.php/api/v2/pim/employees"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/web/index.php/pim/addEmployee",
        }
        change_data = {
            "firstName": firstName,
            "middleName": "",
            "lastName": lastName,
            "empPicture": None,
            "employeeId": employeeId
        }
        resp = self.session.post(url=url, headers=headers, json=change_data)
        return resp

    def get_employee_list(self):
        """
        查询员工列表
        先 get 页面再调接口，是因为 OrangeHRM 有些接口需要前端先渲染页面拿到某些 token
        或者单纯为了模拟真实浏览行为，让后端认为这是一个正常用户操作
        """
        self.session.get(f"{self.base_url}/web/index.php/pim/viewEmployeeList")
        return self.request_base("select_employee", change_data=None)

    def select_query_employee(self, employeeId):
        """查询指定员工"""
        change_data = {
            "employeeId": employeeId,
            "base_url": self.base_url
        }
        return self.request_base("select_query", change_data=change_data)


"""编辑员工"""
class UpdateEmployee(ApiBase):

    def __init__(self, session, url):
        super().__init__("04更新员工")
        self.session = session
        self.base_url = url

    def update_employee(self, firstName, lastName, employeeId):
        change_data = {
            "firstName": firstName,
            "lastName": lastName,
            "employeeId": employeeId,
            "base_url": self.base_url
        }
        return self.request_base("update_employee", change_data)


"""删除员工"""
class DeleteEmployee(ApiBase):

    def __init__(self, session, url):
        super().__init__("05删除员工")
        self.session = session
        self.base_url = url

    def delete_employee(self, employeeId):
        """
        删除指定员工
        这里直接传 json={"ids": [employeeId]}，而不是用 change_data 模板替换
        因为 delete 接口的 payload 结构是 {"ids": [123]}，YAML 模板替换不好处理列表嵌套
        如果硬要在 YAML 里写 {"ids": [${employeeId}]}，Template.safe_substitute 会把整个列表当成字符串处理
        所以直接传 json 更靠谱
        """
        # change_data = {"ids": [employeeId]}  # 这种方式在 YAML 里不好配，弃用
        change_data ={
            "base_url" : self.base_url,
        }
        return self.request_base("delete_employee", change_data , json={"ids": [employeeId]})


"""未登录场景：验证鉴权拦截"""
class LoginOutEmployee(ApiBase):

    def __init__(self,url):
        super().__init__("06未登录访问员工接口")
        self.base_url = url

    def login_out_employee(self,):
        """
        未登录状态下访问员工接口
        allow_redirects=False 必须加，否则 302 跳转到登录页后返回 200
        用例里判断的是 401/403，如果被重定向成 200，断言就失效了
        """

        change_data = {
            "base_url": self.base_url,
        }
        return self.request_base("employee",change_data ,  allow_redirects=False)


"""非管理员账号：验证权限控制"""
class EmployeeLogin(ApiBase):

    def __init__(self, session,url):
        super().__init__("07非管理员登录")
        self.session = session
        self.base_url = url

    def employee_login(self, firstName, lastName, employeeId):
        """
        非管理员账号尝试操作员工
        预期应该是 403 禁止访问，用来验证 RBAC 权限模型是否生效
        """
        change_data = {
            "firstName": firstName,
            "lastName": lastName,
            "employeeId": employeeId,
            "base_url": self.base_url
        }
        return self.request_base("employee_login", change_data=change_data)