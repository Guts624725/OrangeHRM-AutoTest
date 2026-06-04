"""
@Author  : 谢胜强
@Time  : 2025/5/5 22:36
@Desc    : 日志管理封装（企业级通用）
"""
import logging
import os
import time
from typing import Optional
from Base.basePath import BasePath as BP

# 日志目录不存在就自动创建，避免 FileHandler 初始化时报目录不存在
os.makedirs(BP.LOG_PATH, exist_ok=True)

# 配置直接写死在这里，不读任何外部配置文件
# 之前 read_config_ini 里也用 Logger 打日志，结果 Logger 初始化又要读配置，死循环了
# 干脆把日志相关的配置内聚在这里，彻底切断递归
LOG_CONFIG = {
    "level": "INFO",
    "formatter": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "stream_handler_level": "INFO",
    "file_handler_level": "DEBUG"
}

# 按小时切分日志文件，方便排查问题的时候定位时间段
# 如果按天切，一天跑几百条用例，日志文件会很大，打开很卡
log_filename = time.strftime("%Y%m%d_%H", time.localtime()) + ".log"
log_file_path = os.path.join(BP.LOG_PATH, log_filename)


class Logger(object):
    def __init__(self, name: Optional[str] = None):
        self.logger_name = name or __name__
        self.logger = logging.getLogger(self.logger_name)

        # 关掉 propagate，不然日志会冒泡到根 logger
        # 如果根 logger 也有 handler，同一条日志会在控制台打印两次，文件里也会写两次
        self.logger.propagate = False
        self.logger.setLevel(LOG_CONFIG["level"].upper())

        # 同一个 logger_name 的 handler 只加一次
        # 之前踩过坑：每次 new Logger() 都 addHandler，跑完一批用例控制台输出几十行重复的日志
        if not self.logger.handlers:
            self._add_handlers()

    def _add_handlers(self):
        formatter = logging.Formatter(LOG_CONFIG["formatter"])

        # 控制台只打 INFO 及以上，避免 DEBUG 刷屏
        # 文件里打 DEBUG，排查问题的时候翻文件能看到更细的信息
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(LOG_CONFIG["stream_handler_level"].upper())
        stream_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
        file_handler.setLevel(LOG_CONFIG["file_handler_level"].upper())
        file_handler.setFormatter(formatter)

        self.logger.addHandler(stream_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger

    # 旧代码里有些地方调的是 getLogger，保留兼容，省得全局替换
    def getLogger(self) -> logging.Logger:
        return self.get_logger()


if __name__ == '__main__':
    logger = Logger("baseLogger.py").getLogger()
    logger.debug("调试日志")
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")