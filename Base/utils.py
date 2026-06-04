"""
@Author  : 谢胜强
@Time    : 2026/5/5 19:17
@Desc    : 通用工具函数封装
            功能：配置文件读取、文件夹压缩、文件清空、异常处理、日志集成
            适配：全自动化框架工具调用
"""
import os
import zipfile
import configparser
from typing import Optional


def read_config_ini(config_file_path: str) -> Optional[configparser.ConfigParser]:
    """读取 ini 配置文件"""
    # Logger 延迟导入，放在函数内部而不是文件顶部
    # 因为 baseLogger.py 里引用了 BasePath，而 BasePath 又在这个 utils 模块里被引用
    # 如果顶部 import Logger，Python 解析 import 链时会形成循环导入，直接报错
    # 延迟到函数执行时才 import，此时模块已经加载完毕，循环问题自然化解
    from Base.baseLogger import Logger
    logger = Logger("baseUtils.py").get_logger()

    try:
        config = configparser.ConfigParser()
        config.read(config_file_path, encoding='utf-8')
        logger.info(f"配置文件读取成功：{config_file_path}")
        return config
    except FileNotFoundError:
        logger.error(f"配置文件不存在：{config_file_path}")
        return None
    except Exception as e:
        logger.error(f"配置文件读取失败：{str(e)}")
        return None


def make_zip(local_path: str, zip_name: str) -> Optional[str]:
    """
    递归压缩文件夹为 ZIP 包
    :param local_path: 要压缩的文件夹路径
    :param zip_name: 压缩包保存路径+名称
    :return: 压缩包路径 / None
    """
    from Base.baseLogger import Logger
    logger = Logger("baseUtils.py").get_logger()

    if not os.path.isdir(local_path):
        logger.error(f"待压缩目录不存在：{local_path}")
        return None

    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 截取 pre_len 是为了让压缩包里的路径是相对路径
            # 如果不截，zip 里会存 E:\project\Reports\ALLURE\Report\... 这种绝对路径
            # 收件人解压后也要在 E 盘找，非常不友好
            pre_len = len(os.path.dirname(local_path))
            for parent, _, filenames in os.walk(local_path):
                for filename in filenames:
                    file_full_path = os.path.join(parent, filename)
                    arcname = file_full_path[pre_len:].strip(os.path.sep)
                    zipf.write(file_full_path, arcname)

        logger.info(f"文件夹压缩成功：{zip_name}")
        return zip_name
    except Exception as e:
        logger.error(f"文件夹压缩失败：{str(e)}")
        return None


def file_all_delete(path: str) -> None:
    """
    清空指定目录下的所有文件（仅删除文件，保留目录）
    :param path: 目标文件夹路径
    """
    from Base.baseLogger import Logger
    logger = Logger("baseUtils.py").get_logger()

    if not os.path.isdir(path):
        logger.warning(f"目录不存在，无需删除：{path}")
        return

    try:
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            # 只删文件，不碰子文件夹
            # 比如 Log 目录下可能有按小时切的日志文件，也可能有子目录（虽然目前没用到）
            # 保留目录结构，避免误删把 Log 目录本身搞没了，后续 Logger 初始化又报错
            if os.path.isfile(file_path):
                os.remove(file_path)
        logger.info(f"目录文件清空完成：{path}")
    except Exception as e:
        logger.error(f"文件删除失败：{str(e)}")


# 兼容旧代码里的调用名，不用全局替换
file_all_dele = file_all_delete

if __name__ == '__main__':
    from Base.basePath import BasePath as BP

    config = read_config_ini(BP.CONFIG_FILE_PATH)
    if config:
        print(config)
        print(type(config))
        print(config["客户端自动化配置"]["duration"])
        print(type(config["客户端自动化配置"]["duration"]))