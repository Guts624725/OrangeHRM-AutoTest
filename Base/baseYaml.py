"""
@Author  : 谢胜强
@Time    : 2026/5/6 13:49
@Desc    : YAML 读写封装（企业级通用）
            功能：安全读写、自动创建文件、支持数据追加、框架日志集成
            适配：自动化框架元素数据、用例配置、数据驱动
"""
import os
import yaml
from typing import Dict, Any, Optional

from Base.baseLogger import Logger
logger = Logger("baseYaml.py").getLogger()


class YamlHandler:
    def __init__(self, file_path: str):
        self.file_path = file_path
        # 文件不存在时自动创建空 YAML，避免调用方每次都要判断文件在不在
        # 用 yaml.dump({}) 而不是直接写 ""，因为空字符串用 yaml.load 会返回 None
        # 后面 read_yaml 里如果读到 None，还要额外处理成 {}，不如初始化时就写个空字典
        if not os.path.exists(self.file_path):
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    yaml.dump({}, stream=f, allow_unicode=True)
                logger.info(f"YAML文件不存在，已自动创建：{self.file_path}")
            except Exception as e:
                logger.error(f"创建YAML文件失败：{e}")

    def read_yaml(self) -> Optional[Dict[str, Any] | list]:
        """
        读取 YAML 文件
        :return: 字典/列表，读取失败返回 None
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                # FullLoader 是安全加载器，不会执行 YAML 里的任意代码
                # 之前用 Loader=yaml.Loader 有安全风险，如果 YAML 被注入恶意代码会直接执行
                content = yaml.load(f, Loader=yaml.FullLoader)
            # 空文件返回空字典，调用方可以直接 content.get("key")，不用先判断是不是 None
            return content if content is not None else {}
        except Exception as e:
            logger.error(f"YAML读取失败：{self.file_path}，错误信息：{str(e)}")
            return None

    def write_yaml(self, data: Any, append: bool = False) -> bool:
        """
        写入 YAML 文件
        :param data: 要写入的数据
        :param append: True=合并追加 / False=覆盖写入
        :return: 写入结果
        """
        try:
            # YAML 本身没有追加模式，所以 append=True 其实是"先读出来，合并，再覆盖写"
            # 和 Excel 的 append 不一样，这里不是文件级别的追加，是数据级别的合并
            if append:
                old_data = self.read_yaml()
                if isinstance(old_data, list) and isinstance(data, list):
                    new_data = old_data + data
                elif isinstance(old_data, dict) and isinstance(data, dict):
                    new_data = {**old_data, **data}
                else:
                    # 类型不一致时（比如旧数据是 dict，新数据是 list），直接覆盖，不强行合并
                    new_data = data
            else:
                new_data = data

            with open(self.file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    data=new_data,
                    stream=f,
                    allow_unicode=True,
                    sort_keys=False,  # 保持 key 的原始顺序，不然 dump 后会按字母排序
                    default_flow_style=False  # 多行格式，方便人工查看和调试
                )

            logger.info(f"YAML写入成功：{self.file_path}")
            return True

        except Exception as e:
            logger.error(f"YAML写入失败：{self.file_path}，错误信息：{str(e)}")
            return False


if __name__ == '__main__':
    yaml_path = r"E:\develop\PythonProject\PythonProject\TestFramework_po\Data\DataDriver\YamlDriver\project01_auto_test\Yaml数据驱动-登录.yaml"
    ya = YamlHandler(yaml_path)

    read_data = ya.read_yaml()
    print("读取数据：", read_data)