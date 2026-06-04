"""
@Author  : 谢胜强
@Time    : 2026/5/9 13:13
@Desc    : 数据库增删改查封装（企业级）
            支持：MySQL / Sqlite3、防SQL注入、事务安全、框架日志集成
            适配：自动化测试数据构造、结果校验、配置自动读取
"""
import pymysql
import sqlite3
from typing import Optional, List, Dict, Any

from Base.baseLogger import Logger
from Base.basePath import BasePath as BP
from Base.utils import read_config_ini

logger = Logger("baseDB.py").getLogger()
config = read_config_ini(BP.CONFIG_FILE_PATH)
DB_CONFIG = config["数据库连接配置"]


class MysqlHelp:
    """MySQL数据库封装（防SQL注入、事务安全、自动管理连接）"""

    def __init__(self,
                 host: Optional[str] = None,
                 user: Optional[str] = None,
                 passwd: Optional[str] = None,
                 port: Optional[int] = None,
                 database: Optional[str] = None):
        # 支持手动传参覆盖配置文件，方便临时连别的库做数据对比
        # 比如主库查用户数据，从库查日志数据，传不同 host 就行
        self.host = host or DB_CONFIG["host"]
        self.user = user or DB_CONFIG["user"]
        self.passwd = passwd or DB_CONFIG["passwd"]
        self.port = port or int(DB_CONFIG["port"])
        self.db = database or DB_CONFIG["database"]
        self.connection: Optional[pymysql.Connection] = None

    def create_connection(self) -> None:
        """创建数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.passwd,
                port=self.port,
                database=self.db,
                charset='utf8mb4',
                # DictCursor 让查询结果返回字典列表，而不是元组列表
                # 用 res[0]["username"] 比 res[0][3] 直观多了，不容易因为字段顺序变了就取错值
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("✅ MySQL 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ MySQL 连接失败：{str(e)}")
            raise

    # 顶部已经 import 了 pymysql，这里不需要再 import
    def mysql_db_select(self, sql: str, params: Optional[tuple] = None) -> Optional[List[Dict]]:
        try:
            self.create_connection()

            # 这里又显式指定了 DictCursor，其实 create_connection 里已经配过了
            # 但重复指定也不影响，留个备注以后可以优化掉
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                result_set = cursor.fetchall()

            return result_set if result_set else []

        except Exception as e:
            return None

        finally:
            # 查询完立刻关闭，别占着连接池不放
            # 自动化用例通常执行很快，不需要长连接
            if self.connection:
                self.connection.close()
                self.connection = None

    def mysql_db_operate(self, sql: str, params: Optional[tuple] = None) -> bool:
        """
        增删改数据库操作（防SQL注入、事务回滚）
        :param sql: 执行SQL
        :param params: 参数元组
        :return: 执行结果
        """
        try:
            self.create_connection()
            with self.connection.cursor() as cursor:
                # 用 %s 占位符 + params 元组，pymysql 会自动转义，防止 SQL 注入
                # 千万别用 f-string 或者字符串拼接 SQL，测试数据里如果带单引号直接报错
                cursor.execute(sql, params)
            self.connection.commit()
            logger.info("✅ MySQL 执行成功，事务已提交")
            return True
        except Exception as e:
            if self.connection:
                # 出异常必须回滚，不然脏数据会留在库里，影响后续用例
                self.connection.rollback()
                logger.warning(f"🔄 MySQL 事务已回滚，错误：{str(e)}")
            logger.error(f"❌ MySQL 执行错误：{str(e)}，SQL：{sql}")
            return False
        finally:
            if self.connection:
                self.connection.close()
                logger.info("🔌 MySQL 连接已关闭")


class Sqlite3Tools:
    """Sqlite3数据库封装（字典返回、事务安全）"""

    def __init__(self, database: Optional[str] = None):
        self.database = database
        self.connection: Optional[sqlite3.Connection] = None

    def dict_factory(self, cursor: sqlite3.Cursor, row: tuple) -> Dict:
        """字典格式返回结果"""
        # sqlite3 默认返回元组，通过 row_factory 改成字典
        # 和 pymysql 的 DictCursor 一个道理，方便按字段名取值
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def create_connection(self) -> None:
        """创建SQLite连接"""
        try:
            self.connection = sqlite3.connect(self.database)
            self.connection.row_factory = self.dict_factory
            logger.info("✅ SQLite3 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ SQLite3 连接失败：{str(e)}")
            raise

    def sqlite3_db_select(self, sql: str, params: Optional[tuple] = None) -> Optional[List[Dict]]:
        """SQLite查询操作"""
        try:
            self.create_connection()
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            result_set = cursor.fetchall()
            logger.info(f"📊 SQLite3 查询成功，影响行数：{len(result_set)}")
            return result_set
        except Exception as e:
            logger.error(f"❌ SQLite3 查询错误：{str(e)}，SQL：{sql}")
            return None
        finally:
            # sqlite3 是文件型数据库，用完就关，避免文件锁占用
            # 特别是并发跑用例时，连接没关会导致下一个用例打不开数据库
            if self.connection:
                self.connection.close()
                logger.info("🔌 SQLite3 连接已关闭")

    def sqlite3_db_operate(self, sql: str, params: Optional[tuple] = None) -> bool:
        """SQLite增删改操作"""
        try:
            self.create_connection()
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            self.connection.commit()
            logger.info("✅ SQLite3 执行成功，事务已提交")
            return True
        except Exception as e:
            if self.connection:
                self.connection.rollback()
                logger.warning(f"🔄 SQLite3 事务已回滚，错误：{str(e)}")
            logger.error(f"❌ SQLite3 执行错误：{str(e)}，SQL：{sql}")
            return False
        finally:
            if self.connection:
                self.connection.close()
                logger.info("🔌 SQLite3 连接已关闭")


if __name__ == '__main__':
    db = MysqlHelp()
    res = db.mysql_db_select("SELECT * FROM table WHERE id = %s", (1,))
    print(res)
    db.mysql_db_operate("INSERT INTO table(name) VALUES (%s)", ("test",))