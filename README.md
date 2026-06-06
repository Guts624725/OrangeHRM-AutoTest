# OrangeHRM 自动化测试实战项目

基于 **OrangeHRM 5.x** 系统，独立搭建的 **Web UI + HTTP 接口** 自动化测试框架。

&gt; **项目性质**：个人实战项目，按企业级测试标准设计与实现。

---

## 🚀 技术栈

| 层级 | 技术                    |
|------|-----------------------|
| 编程语言 | Python 3.13+          |
| 接口自动化 | Requests + Pytest     |
| Web UI 自动化 | Selenium + PageObject |
| 数据驱动 | YAML 配置化              |
| 数据库断言 | PyMySQL (DictCursor)  |
| 持续集成 | Jenkins + Gitee             |
| 测试报告 | Allure                |
| 抓包分析 | Fiddler               |
| 容器化 | Docker (Jenkins)      |

---

## 📁 项目结构

```text
OrangeHRM-AutoTest/
├── README.md
├── requirements.txt
├── Jenkinsfile                     # Jenkins Pipeline 配置（Gitee 触发）
├── .gitignore                      # 敏感文件与日志忽略规则
├── Config/
│   ├── 配置文件.ini                # 本地环境配置（已加入 .gitignore，不上传）
│   └── 配置文件.ini.template       # 配置模板（脱敏，含占位符说明）
├── Base/                           # 通用封装层
│   ├── baseAutoHttp.py             # HTTP 请求基类（ApiBase）
│   ├── baseAutoWeb.py              # Web UI 自动化基类
│   ├── baseData.py                 # YAML / Excel 数据驱动读取
│   ├── baseDB.py                   # MySQL 数据库操作封装
│   ├── baseLogger.py               # 日志封装
│   └── baseUtils.py                # 通用工具类
├── Data/                           # 测试数据与 YAML 接口配置
│   ├── YamlDriver/                 # YAML 数据驱动文件
│   │   ├── 01登录接口.yaml
│   │   ├── 03查询员工.yaml
│   │   ├── 04更新员工.yaml
│   │   └── 05删除员工.yaml
│   └── ExcelDriver/                # Excel 数据驱动文件
├── ExtTools/                       # 扩展工具
│   └── dbbase.py                   # 数据库辅助类
├── PageObject/                     # 页面对象层
│   ├── ohrm_http_test/             # 接口测试 PO
│   │   ├── api_login_page.py
│   │   └── api_employee_page.py
│   └── ohrm_test/                  # Web UI 测试 PO
├── RunMain/                        # 测试执行入口
│   ├── run.py                      # 主运行脚本（Allure + Pytest）
│   └── runClient.py                # 客户端测试入口
├── TestSuits/                      # 测试用例层
│   ├── conftest.py                 # Pytest Session 级 fixture（登录前置）
│   ├── ohrm_http_test/             # 接口测试用例
│   │   └── test_http_ohrm.py
│   └── ohrm_test/                  # Web UI 测试用例
├── Reports/                        # 测试报告输出
│   ├── ALLURE/                     # Allure 原始结果与 HTML 报告
│   ├── HTML/                       # Pytest HTML 报告
│   └── XML/                        # JUnit XML 报告
└── Log/                            # 运行日志（已加入 .gitignore，不上传）
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
- 更新后再次查询，断言字段值已变更
- **删除**后再次查询，断言返回空列表，确保物理删除生效。

### 📊 YAML 数据驱动
- 接口的 URL、Method、Headers、Params 全部抽离至 YAML 文件。
- 通过 ${变量} 动态替换，实现配置与代码分离
- 支持运行时注入 base_url，适配本地与 CI 环境

---

## ⚙️ 运行方式

### 1. 安装依赖
```bash
pip install -r requirements.txt
```
### 2. 配置环境
- 复制 Config/配置文件.ini.template 为 Config/配置文件.ini
- 填入真实的 测试 URL、数据库连接、邮箱授权码、登录账号密码
### 3. 执行测试
```bash
# 运行全部接口测试
python RunMain/run.py

# 或直接用 pytest
pytest TestSuits/ohrm_http_test/ -v --alluredir=Reports/ALLURE/Result

# 查看 Allure 报告
allure serve Reports/ALLURE/Result
```

## 🔄 持续集成（CI）
本项目已接入 Jenkins + Gitee，代码 Push 后自动触发构建

| 配置项 | 说明                    |
|------|-----------------------|
| 代码托管 | Gitee          |
| CI 工具	 | Jenkins (Docker 部署)     |
| 触发方式 | 手动构建 / 轮询 SCM |
| 构建流程 | 拉取代码 → 注入配置 → 安装依赖 → 运行测试 → 生成 Allure 报告              |
| 报告查看 | Jenkins 构建页面直接查看 Allure 趋势图与用例详情  |


## 🔒 脱敏说明
- 配置文件：Config/配置文件.ini 已加入 .gitignore，不会提交到仓库
- 日志目录：Log/ 已加入 .gitignore，运行日志不上传
- 敏感信息：仓库中所有密码、授权码、Token 均使用 ${占位符} 或 ****** 脱敏
- 本地运行：请复制模板文件并填入真实参数，切勿将真实配置 push 到远程

## 📧 联系方式
如有问题或建议，欢迎联系：
邮箱：511227621@qq.com

---


