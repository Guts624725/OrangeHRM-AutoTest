"""
@Author  : 谢胜强
@Time    : 2026/5/7 16:59
@Desc    : 邮件发送封装（企业级通用）
            功能：支持文本/HTML/附件（HTML/Allure/XML报告）、SSL加密发送
            适配：自动化测试报告邮件推送，对接框架日志/路径
"""
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from ast import literal_eval

from Base.basePath import BasePath as BP
from Base.utils import read_config_ini, make_zip
from Base.baseLogger import Logger

logger = Logger("baseEmail.py").getLogger()


class HandleEmail(object):
    """邮件发送工具类（自动化测试报告专用）"""

    def __init__(self):
        config = read_config_ini(BP.CONFIG_FILE_PATH)
        email_config = config["邮件发送配置"]

        self.host = email_config["host"]
        self.port = int(email_config["port"])
        self.sender = email_config["sender"]
        self.send_email = email_config["send_email"]
        # 收件人列表用 literal_eval 解析，比 eval 安全
        # 之前配置里写 ["a@qq.com", "b@qq.com"]，用 eval 直接执行字符串，如果配置被注入恶意代码就完了
        # literal_eval 只解析字面量（列表、字典、字符串等），不会执行代码
        self.receiver = literal_eval(email_config["receiver"])
        self.pwd = email_config["pwd"]
        self.subject = email_config["subject"]

    def add_text(self, text: str) -> MIMEText:
        """添加纯文本内容"""
        return MIMEText(text, "plain", "utf-8")

    def add_html_text(self, html: str) -> MIMEText:
        """添加HTML内容"""
        # MIME 类型必须是 "html" 而不是 "plain"，不然邮件客户端会把 HTML 标签当成纯文本显示
        # 之前踩过坑：收到的邮件里直接显示 <table><tr>... 这种原始标签
        return MIMEText(html, "html", "utf-8")

    def add_accessory(self, filepath: str) -> MIMEText | None:
        """
        添加附件（图片/txt/pdf/zip/html）
        """
        if not os.path.exists(filepath):
            # 报告文件可能生成失败，这里不要抛异常，跳过附件继续发邮件
            # 至少能让收件人知道测试跑完了，哪怕附件没附上
            logger.error(f"附件不存在：{filepath}，跳过添加")
            return None

        # 用 with 读取，确保文件句柄及时关闭
        # 之前直接 open 没 close，Windows 下文件会被占用，后续删除/覆盖报告文件时报 Permission denied
        with open(filepath, "rb") as f:
            res = MIMEText(f.read(), "base64", "utf-8")

        filename = os.path.basename(filepath)
        res.add_header("Content-Disposition", "attachment", filename=filename)
        return res

    def add_subject_attach(self, attach_info: tuple, send_date: str = None) -> MIMEMultipart:
        """组装邮件：主题、发件人、收件人、附件"""
        msg = MIMEMultipart('mixed')
        msg['Subject'] = self.subject
        msg["From"] = formataddr((self.sender, self.send_email))
        msg['To'] = ";".join(self.receiver)
        msg['Date'] = send_date or datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

        for item in attach_info:
            if item:
                msg.attach(item)
        return msg

    def send_email_oper(self, msg: MIMEMultipart):
        """执行邮件发送（SSL加密）"""
        smtp = None
        try:
            # 大多数邮箱（QQ、163、企业微信）都要求 SSL 加密，端口通常是 465
            # 如果这里用 SMTP() 而不是 SMTP_SSL()，QQ 邮箱会直接拒绝连接
            smtp = smtplib.SMTP_SSL(self.host, self.port)
            smtp.login(self.send_email, self.pwd)
            smtp.sendmail(self.send_email, self.receiver, msg.as_string())
            logger.info(f"✅ 邮件发送成功！发件人：{self.send_email}，收件人：{self.receiver}")
        except Exception as e:
            logger.error(f"❌ 邮件发送失败：{str(e)}")
        finally:
            # smtp 对象可能创建失败（比如网络不通），所以先判断是不是 None 再 quit
            if smtp:
                smtp.quit()

    def send_public_email(self, send_date=None, text='', html='', filetype='HTML'):
        """
        通用邮件发送入口（对接自动化报告）
        :param filetype: HTML/ALLURE/XML 三种报告类型
        """
        attach_list = []
        attach_list.append(self.add_text(text=text))
        if html:
            attach_list.append(self.add_html_text(html=html))

        file_attach = None
        if filetype == "ALLURE":
            # Allure 报告是一个文件夹，邮件附件不能传文件夹，必须先压缩成 zip
            # 压缩路径固定放在 ALLURE_REPORT_PATH 下，方便收件人下载后解压直接看
            zip_path = os.path.join(BP.ALLURE_REPORT_PATH, 'allure.zip')
            make_zip(BP.ALLURE_REPORT_PATH, zip_path)
            file_attach = self.add_accessory(zip_path)
        elif filetype == "HTML":
            file_attach = self.add_accessory(os.path.join(BP.HTML_PATH, 'auto_reports.html'))
        elif filetype == "XML":
            file_attach = self.add_accessory(os.path.join(BP.XML_PATH, 'auto_reports.xml'))

        if file_attach:
            attach_list.append(file_attach)

        msg = self.add_subject_attach(attach_info=tuple(attach_list), send_date=send_date)
        self.send_email_oper(msg)


if __name__ == '__main__':
    test_text = '本邮件由系统自动发出,无需回复!\n各位同事,大家好,以下为本次测试报告!'
    HandleEmail().send_public_email(text=test_text, html="", filetype='HTML')