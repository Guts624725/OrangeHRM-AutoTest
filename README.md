# OrangeHRM 自动化测试实战项目

基于开源 **OrangeHRM 5.x** 系统，独立搭建的 **Web UI + HTTP 接口** 自动化测试框架。

&gt; **项目性质**：个人实战项目，按企业级测试标准设计与实现。

---

## 🚀 技术栈

| 层级 | 技术 |
|------|------|
| 编程语言 | Python 3.10+ |
| 接口自动化 | Requests + Pytest |
| Web UI 自动化 | Selenium + PageObject |
| 数据驱动 | YAML 配置化 |
| 数据库断言 | PyMySQL (DictCursor) |
| 持续集成 | Jenkins |
| 测试报告 | Allure |
| 抓包分析 | Fiddler |

---

## 📁 项目结构

```text
OrangeHRM-AutoTest/
├── README.md
├── requirements.txt
├── Jenkinsfile                     # Jenkins Pipeline 配置
├── config/
│   ├── config.ini                  # 环境配置（已脱敏）
│   └── yaml/                       # 接口 YAML 配置
│       ├── 01登录页面接口信息.yaml
│       ├── 03查询员工页面.yaml
│       ├── 04更新员工.yaml
│       └── 05删除员工.yaml
├── base/                           # 通用封装层
│   ├── baseAutoHttp.py             # HTTP 请求基类（ApiBase）
│   ├── baseData.py                 # YAML 数据驱动读取
│   ├── baseDB.py                   # MySQL 数据库操作
│   └── baseLogger.py               # 日志封装
├── api/                            # 接口页面对象层
│   ├── api_login_page.py           # 登录接口（含 Token 提取）
│   └── api_employee_page.py        # 员工 CRUD 接口
├── page/                           # Web UI 页面对象层
│   └── web_employee_page.py        # PIM 模块 PO
├── test/                           # 测试用例层
│   ├── conftest.py                 # Pytest Session 级 fixture（登录前置）
│   ├── test_http_ohrm.py           # 接口测试用例
│   └── test_web_ohrm.py            # Web UI 测试用例
└── utils/                          # 工具类
```
---

## 💡 核心能力展示

### 🔐 认证与会话管理
- 从登录页 HTML 正则提取 `_token`，并处理 `&quot;` 实体编码，解决 Symfony 后端校验失败问题。
- 登录 POST 后手动跟随 `302` 重定向至 Dashboard，确保服务端 Session 上下文真正建立，避免后续请求 `401 Session expired`。

### 🛡️ 鉴权与安全测试
- **未登录访问**：API 返回 `401`，页面跳转返回 `302` + `Location` 头。
- **Token 异常**：覆盖 Token 缺失、过期、跨会话复用、错误格式等场景。
- **越权测试**：普通员工（ESS）Session 调用管理员接口，验证后端返回 `403 Forbidden`。

### 🔄 数据库闭环验证
- 封装 **PyMySQL** 查询类，支持 `DictCursor` 字典化返回。
- **新增**后查 `hs_hr_employee` 表，确认 `emp_number` 主键存在。
- **删除**后再次查询，断言返回空列表，确保物理删除生效。

### 📊 YAML 数据驱动
- 接口的 URL、Method、Headers、Params 全部抽离至 YAML 文件。
- 通过 `Template` 动态替换 `$变量`，实现配置与代码分离。

---

## ⚙️ 运行方式

### 1. 安装依赖
```bash
pip install -r requirements.txt
```
### 2. 配置环境
修改 config/config.ini 中的 TEST_URL、数据库连接及登录账号（本地运行需填入真实值）
### 3. 执行测试
```bash
# 运行全部用例
pytest TestSuits/ -v

# 生成 Allure 报告
pytest TestSuits/ --alluredir=./allure-results
allure serve ./allure-results
```

## 🔄 持续集成（CI）
本项目已接入 Jenkins，代码 Push 后通过 Webhook 自动触发构建，执行测试并在 Jenkins 内生成 Allure 报告
* 触发方式：Git Push / Pull Request / 定时构建
* 构建状态：Jenkins 构建状态（由 Jenkins 的 Build Badge 插件或描述提供）
* 测试报告：通过 Allure Jenkins Plugin 直接在构建页面查看趋势图与详情

## 🔒 脱敏说明
本项目为学习演示用途，配置文件中的账号、密码、Cookie 等敏感信息已脱敏（显示为 ******）
本地运行前，请在 config/config.ini 中替换为真实环境参数

## 📧 联系方式
如有问题或建议，欢迎联系：
邮箱：511227621@qq.com

---


