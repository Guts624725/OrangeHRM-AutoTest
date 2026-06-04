"""
@Author  : 谢胜强
@Time    : 2026/5/8 15:40
@Desc    : 接口自动化通用基类
            全平台通用：HTTP/HTTPS、RESTful、表单、JSON、文件上传
            支持会话保持、数据驱动、统一日志、异常处理
"""
from urllib.parse import urljoin
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from typing import Optional, Dict, Any

from Base.baseData import DataBase
from Base.baseLogger import Logger

# 关掉 SSL 警告，不然控制台会被 InsecureRequestWarning 刷屏
# 测试环境证书通常不是自签就是过期的，开着这个日志没法看
# 注意：生产环境建议把 verify 改成 True
urllib3.disable_warnings(InsecureRequestWarning)
logger = Logger("baseAutoHttp.py").getLogger()


class ApiBase(DataBase):
    """接口自动化通用基类（适配所有系统）"""

    def __init__(self, yamlName: str):
        super().__init__(yamlName)
        self.yamlName = yamlName

        # session 必须是实例属性，不能放类属性里
        # 之前踩过坑：多个用例共享同一个 session，cookie 互相污染，登录态串了
        self.session = requests.Session()

        self.timeout = 15
        self.verify = False

    def request_base(self, apiName: str, change_data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        通用接口请求方法（企业级标准）
        :param apiName: YAML中的接口名称
        :param change_data: 动态替换参数
        :param kwargs: 动态覆盖参数（优先级最高）
        :return: 响应对象
        """
        logger.info(f"【{self.yamlName}:{apiName}】接口调用开始")

        try:
            yaml_data: Dict[str, Any] = self.get_element_data(change_data)[apiName]
            logger.debug(f"接口原始配置: {yaml_data}")

            # 用 urljoin 拼接，比字符串拼接靠谱
            # 能自动处理 base_url 末尾有没有斜杠、接口路径开头有没有斜杠的问题
            base_url = self.run_config["TEST_URL"]
            yaml_data["url"] = urljoin(base_url, yaml_data["url"])

            # kwargs 优先级高于 YAML，方便用例里临时改参数
            # 比如 YAML 里 timeout 是 5 秒，某个接口特别慢，用例里直接传 timeout=30 就能覆盖
            req_data = {**yaml_data, **kwargs}

            # 请求日志打全点，出问题时不用翻 YAML 文件，看日志就能复盘
            logger.info(f"请求方式: {req_data['method'].upper()}")
            logger.info(f"请求地址: {req_data['url']}")
            logger.info(f"请求头: {req_data.get('headers', {})}")
            logger.info(f"请求参数: params={req_data.get('params')} | data={req_data.get('data')} | json={req_data.get('json')}")

            res = self.session.request(
                **req_data,
                timeout=self.timeout,
                verify=self.verify
            )

            logger.info(f"响应状态码: {res.status_code}")
            logger.info(f"响应耗时: {res.elapsed.total_seconds()}s")

            # 先尝试按 JSON 打印，失败再降级为文本
            # 后端偶尔抽风返回 HTML（比如 Nginx 502 页面），直接 .json() 会抛异常
            try:
                logger.info(f"响应JSON: {res.json()}")
            except Exception:
                logger.info(f"响应文本: {res.text}")

            logger.info(f"【{self.yamlName}:{apiName}】接口调用结束\n")
            return res

        except Exception as e:
            # 这里 raise 出去，让 pytest/unittest 去捕获，用例能正常标记为失败
            # 日志里带 exc_info=True，堆栈信息保留完整，排查时不用复现
            logger.error(f"【{apiName}】接口请求失败: {str(e)}", exc_info=True)
            raise

    def close_session(self):
        """关闭会话，释放连接池资源"""
        self.session.close()
        logger.info("接口会话已关闭")


if __name__ == '__main__':
    api = ApiBase("接口元素信息-登录")
    api.request_base("home_api")