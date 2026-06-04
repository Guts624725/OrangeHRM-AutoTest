"""
@Author  : 谢胜强
@Time    : 2026/5/6 13:00
@Desc    : 全局变量管理器（单例模式）
            通用：存储driver、token、用例依赖数据等全局变量
            get方法安全取值，取不到返回None，不抛异常
"""
import threading
from Base.baseLogger import Logger

logger = Logger("globalManager.py").getLogger()

class GlobalManager(object):
    """全局变量单例管理器（线程安全 + 全框架通用）"""

    # 注意：_global_dict 是类属性，不是实例属性
    # 这意味着所有实例共享同一个字典，这正是单例想要的
    # 但如果在 __init__ 里写 self._global_dict = {}，那就变成实例属性，单例就破了
    _instance_lock = threading.Lock()
    _global_dict = {}
    _instance = None

    def __new__(cls, *args, **kwargs):
        # 双检锁：先判断一次，再加锁判断一次
        # 别觉得啰嗦，高并发跑用例的时候，不加锁可能瞬间创建出多个实例
        # 虽然 Python 有 GIL，但 __new__ 执行期间线程切换还是可能发生的
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    logger.info("全局变量管理器初始化成功")
        return cls._instance

    def set_value(self, name: str, value):
        """
        设置全局变量
        :param name: 变量名
        :param value: 变量值
        """
        self._global_dict[name] = value
        logger.debug(f"全局变量设置：{name} = {value}")

    def get_value(self, name: str, default=None):
        """
        安全获取全局变量（核心：取不到返回默认值，不报错）
        :param name: 变量名
        :param default: 取不到时的默认值，默认None
        :return: 变量值 / default
        """
        # 用 dict.get 而不是 dict[name]，因为用例里经常先判断 driver 有没有初始化
        # 如果这里抛 KeyError，每个用例都要 try-except，代码没法看
        value = self._global_dict.get(name, default)
        logger.debug(f"全局变量获取：{name} = {value}")
        return value

    def del_value(self, name: str):
        """删除指定全局变量（通用扩展）"""
        if name in self._global_dict:
            del self._global_dict[name]
            logger.debug(f"全局变量删除：{name}")

    def clear_all(self):
        """清空所有全局变量（用例结束后通用清理）"""
        # 用 warning 级别是因为这通常意味着一批用例跑完了，或者发生了严重错误需要重置环境
        # 如果每次用例结束都清，打 info 会刷屏，warning 更容易在日志里一眼看到
        self._global_dict.clear()
        logger.warning("所有全局变量已清空")

    def get_all_keys(self):
        """获取所有全局变量名（通用调试）"""
        return list(self._global_dict.keys())

    def get_all_dict(self):
        """获取完整全局字典（通用扩展）"""
        # 返回 copy，防止外部直接改内部字典，把全局状态搞乱
        return self._global_dict.copy()


if __name__ == '__main__':
    g1 = GlobalManager()
    g1.set_value("谢胜强", "176")

    g2 = GlobalManager()
    res = g2.get_value("谢胜强")
    none_res = g2.get_value("driver")
    print("获取值：", res)
    print("获取不存在的值：", none_res)