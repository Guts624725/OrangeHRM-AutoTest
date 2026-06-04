"""
@Author  : 谢胜强
@Time    : 2026/5/9 13:27
@Desc    : SSH远程连接Shell封装（企业级）
            功能：远程执行命令、文件上传/下载、SFTP操作、日志集成
            适配：自动化测试远程服务器操作、日志收集、文件传输
"""
import paramiko
from typing import Optional, List

from Base.baseLogger import Logger

logger = Logger("baseSSH.py").getLogger()


class SSH:
    """SSH远程连接工具类，支持命令执行、SFTP上传下载"""

    def __init__(self, ip: str, username: str, password: str, port: int = 22):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.timeout = 10  # 10秒超时够用了，SSH 命令通常很快，如果 10 秒都没响应大概率是网络不通或命令卡死

    def shell_cmd(self, cmd: str) -> Optional[List[str]]:
        """
        远程执行Shell命令
        :param cmd: 要执行的命令
        :return: 执行结果列表，失败返回None
        """
        ssh: Optional[paramiko.SSHClient] = None
        try:
            ssh = paramiko.SSHClient()
            # 自动接受未知主机的密钥，第一次连不会弹确认
            # 测试环境用这个方便，不用手动去 ~/.ssh/known_hosts 里加
            # 但生产环境建议改成 RejectPolicy 或者先手动把密钥加好，防止中间人攻击
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.ip,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout
            )
            logger.info(f"✅ 远程服务器[{self.ip}]连接成功，执行命令：{cmd}")

            # exec_command 返回三个流：stdin（输入）、stdout（输出）、stderr（错误）
            # 有些命令会把"警告"信息写到 stderr，但返回码是 0，不算失败
            # 所以这里 stdout 和 stderr 都读，但分开处理：stdout 当结果，stderr 只打日志
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()

            if error:
                logger.warning(f"⚠️ 命令执行错误：{error}")

            # 按行分割，方便调用方直接遍历处理
            result = output.split('\n') if output else []
            logger.info(f"📤 命令执行完成，返回结果：{len(result)} 行")
            return result

        except Exception as e:
            logger.error(f"❌ 远程执行命令失败：{str(e)}，服务器[{self.ip}]")
            return None

        finally:
            # SSH 连接底层是 TCP，不关的话会占用服务器端的连接数
            # 特别是批量跑用例时，如果每个用例都连一次 SSH 不关，几十次后服务器就拒绝连接了
            if ssh:
                ssh.close()
                logger.info(f"🔌 已断开与[{self.ip}]的SSH连接")

    def shell_upload(self, localpath: str, remotepath: str) -> bool:
        """
        SFTP上传文件到远程服务器
        """
        transport: Optional[paramiko.Transport] = None
        try:
            # SFTP 是基于 SSH 的文件传输协议，paramiko 里通过 Transport 建立底层连接
            # 也可以从 SSHClient 对象里 open_sftp()，但那样需要先建 SSHClient 再转 SFTP
            # 直接用 Transport 更轻量，上传下载不需要 exec_command 的能力
            transport = paramiko.Transport((self.ip, self.port))
            transport.connect(username=self.username, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)

            sftp.put(localpath, remotepath)
            logger.info(f"✅ 文件上传成功：本地[{localpath}] → 远程[{remotepath}]")
            return True

        except Exception as e:
            logger.error(f"❌ 文件上传失败：{str(e)}，本地[{localpath}]")
            return False

        finally:
            if transport:
                transport.close()

    def shell_download(self, localpath: str, remotepath: str) -> bool:
        """
        SFTP从远程服务器下载文件
        """
        transport: Optional[paramiko.Transport] = None
        try:
            transport = paramiko.Transport((self.ip, self.port))
            transport.connect(username=self.username, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)

            sftp.get(remotepath, localpath)
            logger.info(f"✅ 文件下载成功：远程[{remotepath}] → 本地[{localpath}]")
            return True

        except Exception as e:
            logger.error(f"❌ 文件下载失败：{str(e)}，远程[{remotepath}]")
            return False

        finally:
            if transport:
                transport.close()


if __name__ == '__main__':
    ssh = SSH("192.168.1.100", "root", "123456")
    print(ssh.shell_cmd("ls -l"))
    # ssh.shell_upload("test.txt", "/root/test.txt")