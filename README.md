# OrangeHRM 自动化测试框架

基于 [OrangeHRM](https://www.orangehrm.com/) 5.x 系统，从零搭建的 **Web UI + HTTP 接口 + 桌面客户端** 三端一体化自动化测试框架。

&gt; 本项目为个人技术练习与作品展示，敏感配置已脱敏处理。

---

## 🚀 技术栈

| 层级 | 技术 |
|------|------|
| 测试框架 | Python + Pytest |
| Web UI | Selenium 4 + Page Object |
| 接口测试 | Requests + Session 状态保持 |
| 客户端测试 | PyAutoGUI + Pyperclip |
| 数据驱动 | YAML / Excel 双模式切换 |
| 数据库断言 | PyMySQL / SQLite3 |
| 报告 | Allure / HTML / XML 三模式 |
| 辅助工具 | SSH 远程执行、邮件自动推送 |

---

## 📁 项目结构

```text
OrangeHRM-AutoTest/
├── Base/          # 通用框架层（三端通用，可复用）
├── PageObject/    # Web 页面对象层（PO 模式）
├── TestSuits/     # 测试用例（正向、反向、边界、鉴权）
├── Config/        # YAML 接口配置 + 环境配置文件
├── RunMain/       # 主运行入口（GUI / 命令行）
└── Reports/       # 测试报告输出