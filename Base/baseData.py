"""
@Author  : 谢胜强
@Time    : 2026/5/6 17:04
@Desc    : 数据层通用基类
            功能：元素数据读取、YAML/Excel数据驱动、动态参数替换
            适配：Web/接口/客户端自动化，全项目通用
"""
import os
import yaml
from string import Template
from typing import Optional, Dict, Any

from Base.baseContainer import GlobalManager
from Base.baseLogger import Logger
from Base.utils import read_config_ini
from Base.basePath import BasePath as BP
from Base.baseYaml import YamlHandler as YH
from Base.baseExcel import ExcelHandler as EH

logger = Logger("baseData.py").getLogger()


def init_file_path(root_path: str) -> Dict[str, str]:
    """
    遍历文件夹，生成 【文件名(无后缀)→绝对路径】 映射
    通用遍历逻辑，支持多级子目录，无崩溃风险
    :param root_path: 根文件夹路径
    :return: 路径字典
    """
    path_map = {}
    if not os.path.isdir(root_path):
        logger.warning(f"遍历目录不存在：{root_path}")
        return path_map

    for dir_path, _, file_list in os.walk(root_path):
        for file_name in file_list:
            file_key = os.path.splitext(file_name)[0]
            full_path = os.path.join(dir_path, file_name)
            # 注意：如果不同子目录下有同名文件，后面的会覆盖前面的
            # 比如 a/login.yaml 和 b/login.yaml，最终 path_map 里只有 b/login.yaml
            # 目前项目结构里通常不会出现这种情况，但如果以后拆分子模块要注意
            path_map[file_key] = full_path
            logger.debug(f"文件映射：{file_key} -> {full_path}")
    return path_map


def is_file_exist(file_path: Optional[str], file_name: str) -> str:
    """
    通用：检查文件是否存在，不存在则抛异常
    :param file_path: 文件全路径
    :param file_name: 文件名（用于日志）
    :return: 合法路径
    """
    if not file_path or not os.path.exists(file_path):
        err_msg = f"文件不存在：{file_name}，请检查路径/配置/文件名！"
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)
    logger.debug(f"文件校验成功：{file_path}")
    return file_path


class DataBase(object):
    """元素/配置数据读取基类（通用）"""

    def __init__(self, yaml_name: Optional[str] = None):
        self.gm = GlobalManager()
        self.yaml_name = yaml_name
        self.config = read_config_ini(BP.CONFIG_FILE_PATH)
        self.run_config = self.config["项目运行配置"]
        self.auto_type = self.run_config["AUTO_TYPE"]

        # 元素文件放在项目目录下，通过 TEST_PROJECT 配置区分不同系统
        element_root = os.path.join(BP.DATA_ELEMENT_PATH, self.run_config["TEST_PROJECT"])
        file_map = init_file_path(element_root)
        self.api_path = file_map.get(self.yaml_name) if self.yaml_name else None

        # 客户端自动化（GUI）的元素是图片文件，不走 YAML 校验逻辑
        # 而且图片文件数量多，如果也校验存在性，初始化会很慢
        if self.auto_type != "CLIENT" and self.yaml_name:
            self.abs_path = is_file_exist(self.api_path, self.yaml_name)

    def get_element_data(self, change_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        读取元素数据，支持动态参数替换
        :param change_data: 动态替换字典
        :return: 解析后的数据
        """
        try:
            if change_data:
                # 用 Template 做变量替换，比如 YAML 里写 ${username}，调用时传 {"username": "admin"}
                # 用 safe_substitute 而不是 substitute，因为 YAML 里可能有些变量这次不需要替换
                # 如果用 substitute，遇到没传的变量会直接抛 KeyError，用例就崩了
                with open(self.abs_path, "r", encoding="utf-8") as f:
                    cfg_content = f.read()
                content = Template(cfg_content).safe_substitute(**change_data)
                data = yaml.load(content, Loader=yaml.FullLoader)
                logger.info(f"动态参数替换成功：{change_data}")
            else:
                # 没有替换需求时直接用 YamlHandler 读取，省一次文件 IO 的字符串操作
                data = YH(self.api_path).read_yaml()

            logger.debug(f"读取数据成功：{self.yaml_name}")
            return data
        except Exception as e:
            logger.error(f"读取元素数据失败：{self.yaml_name}，错误：{str(e)}")
            raise


class DataDriver(object):
    """数据驱动基类（YAML/Excel 通用）"""

    def __init__(self):
        self.gm = GlobalManager()
        self.config = read_config_ini(BP.CONFIG_FILE_PATH)
        self.run_config = self.config["项目运行配置"]

    def get_case_data(self, driver_name: str, sheet_name: str = "Sheet1") -> Any:
        """
        通用数据驱动获取
        :param driver_name: 驱动文件名
        :param sheet_name: Excel工作表名
        :return: 用例数据
        """
        # 通过 DATA_DRIVER_TYPE 配置切换数据源类型，不用改代码就能在 YAML 和 Excel 之间切
        # 适合不同阶段：开发时用 YAML 调接口，稳定后用 Excel 给测试人员维护用例
        data_type = self.run_config["DATA_DRIVER_TYPE"]
        project = self.run_config["TEST_PROJECT"]
        driver_root = os.path.join(BP.DATA_DRIVER_PATH, data_type, project)
        file_map = init_file_path(driver_root)
        data_path = file_map.get(driver_name)
        data_path = is_file_exist(data_path, driver_name)

        try:
            if data_type == "YamlDriver":
                data = YH(data_path).read_yaml()
            elif data_type == "ExcelDriver":
                data = EH(data_path).read_excel(sheet_name)
            else:
                raise ValueError(f"不支持的数据驱动类型：{data_type}")

            logger.info(f"数据驱动读取成功：{driver_name}")
            return data
        except Exception as e:
            logger.error(f"数据驱动读取失败：{str(e)}")
            raise


if __name__ == '__main__':
    driver = DataDriver()
    res = driver.get_case_data("Yaml数据驱动-登录")
    print(res)