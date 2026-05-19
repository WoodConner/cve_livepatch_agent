#!/usr/bin/env python3
"""
QEMU 虚拟机管理模块
负责创建、启动、管理和与 Anolis OS 虚拟机交互
"""

import os
import subprocess
import time
import socket
import paramiko
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json

logger = logging.getLogger(__name__)


class QEMUManager:
    """QEMU 虚拟机管理器"""

    def __init__(self, config: Dict):
        """
        初始化 QEMU 管理器

        Args:
            config: QEMU 配置字典
        """
        self.config = config
        self.vm_name = config.get('vm_name', 'anolis-livepatch')
        self.image_path = config.get('image_path', 'qemu/images/anolis.qcow2')
        self.memory = config.get('memory', '4G')
        self.cpus = config.get('cpus', 4)
        self.ssh_port = config.get('ssh_port', 2222)
        self.ssh_user = config.get('ssh_user', 'root')
        self.ssh_password = config.get('ssh_password', 'anolis')
        self.ssh_key_path = config.get('ssh_key_path', 'qemu/ssh_keys/id_rsa')

        self.qemu_process = None
        self.ssh_client = None

    def create_vm_image(self, base_iso: str, size: str = '20G') -> bool:
        """
        创建虚拟机镜像

        Args:
            base_iso: Anolis OS ISO 镜像路径
            size: 磁盘大小

        Returns:
            是否创建成功
        """
        try:
            logger.info(f"创建虚拟机镜像: {self.image_path}")

            # 创建目录
            os.makedirs(os.path.dirname(self.image_path), exist_ok=True)

            # 创建 qcow2 镜像
            cmd = [
                'qemu-img', 'create',
                '-f', 'qcow2',
                self.image_path,
                size
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"创建镜像失败: {result.stderr}")
                return False

            logger.info("虚拟机镜像创建成功")
            return True

        except Exception as e:
            logger.error(f"创建虚拟机镜像异常: {e}")
            return False

    def start_vm(self, headless: bool = True) -> bool:
        """
        启动虚拟机

        Args:
            headless: 是否无头模式运行

        Returns:
            是否启动成功
        """
        try:
            logger.info(f"启动虚拟机: {self.vm_name}")

            # 构建 QEMU 命令
            cmd = [
                'qemu-system-x86_64',
                '-name', self.vm_name,
                '-m', self.memory,
                '-smp', str(self.cpus),
                '-hda', self.image_path,
                '-net', 'nic',
                '-net', f'user,hostfwd=tcp::{self.ssh_port}-:22',
                '-enable-kvm',  # 启用 KVM 加速
            ]

            if headless:
                cmd.extend(['-nographic', '-serial', 'mon:stdio'])
            else:
                cmd.extend(['-vga', 'std'])

            # 启动 QEMU 进程
            self.qemu_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )

            logger.info(f"QEMU 进程已启动 (PID: {self.qemu_process.pid})")

            # 等待虚拟机启动
            if not self._wait_for_ssh(timeout=120):
                logger.error("虚拟机启动超时")
                self.stop_vm()
                return False

            logger.info("虚拟机启动成功")
            return True

        except Exception as e:
            logger.error(f"启动虚拟机异常: {e}")
            return False

    def stop_vm(self) -> bool:
        """
        停止虚拟机

        Returns:
            是否停止成功
        """
        try:
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None

            if self.qemu_process:
                logger.info("停止虚拟机...")
                self.qemu_process.terminate()
                self.qemu_process.wait(timeout=30)
                self.qemu_process = None
                logger.info("虚拟机已停止")

            return True

        except Exception as e:
            logger.error(f"停止虚拟机异常: {e}")
            if self.qemu_process:
                self.qemu_process.kill()
            return False

    def _wait_for_ssh(self, timeout: int = 120) -> bool:
        """
        等待 SSH 服务可用

        Args:
            timeout: 超时时间（秒）

        Returns:
            SSH 是否可用
        """
        logger.info(f"等待 SSH 服务启动 (端口 {self.ssh_port})...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', self.ssh_port))
                sock.close()

                if result == 0:
                    # 端口开放，尝试 SSH 连接
                    time.sleep(2)  # 等待 SSH 服务完全就绪
                    if self._connect_ssh():
                        return True
            except:
                pass

            time.sleep(2)

        return False

    def _connect_ssh(self) -> bool:
        """
        建立 SSH 连接

        Returns:
            是否连接成功
        """
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 尝试使用密钥认证
            if os.path.exists(self.ssh_key_path):
                self.ssh_client.connect(
                    'localhost',
                    port=self.ssh_port,
                    username=self.ssh_user,
                    key_filename=self.ssh_key_path,
                    timeout=10
                )
            else:
                # 使用密码认证
                self.ssh_client.connect(
                    'localhost',
                    port=self.ssh_port,
                    username=self.ssh_user,
                    password=self.ssh_password,
                    timeout=10
                )

            logger.info("SSH 连接建立成功")
            return True

        except Exception as e:
            logger.debug(f"SSH 连接失败: {e}")
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
            return False

    def execute_command(self, command: str, timeout: int = 300) -> Tuple[int, str, str]:
        """
        在虚拟机中执行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            (返回码, 标准输出, 标准错误)
        """
        if not self.ssh_client:
            if not self._connect_ssh():
                return (-1, "", "SSH 连接未建立")

        try:
            logger.debug(f"执行命令: {command}")
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)

            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8', errors='ignore')
            stderr_text = stderr.read().decode('utf-8', errors='ignore')

            return (exit_code, stdout_text, stderr_text)

        except Exception as e:
            logger.error(f"执行命令异常: {e}")
            return (-1, "", str(e))

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        上传文件到虚拟机

        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径

        Returns:
            是否上传成功
        """
        if not self.ssh_client:
            if not self._connect_ssh():
                return False

        try:
            logger.info(f"上传文件: {local_path} -> {remote_path}")

            sftp = self.ssh_client.open_sftp()

            # 创建远程目录
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                try:
                    sftp.stat(remote_dir)
                except:
                    self.execute_command(f"mkdir -p {remote_dir}")

            sftp.put(local_path, remote_path)
            sftp.close()

            logger.info("文件上传成功")
            return True

        except Exception as e:
            logger.error(f"上传文件异常: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        从虚拟机下载文件

        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径

        Returns:
            是否下载成功
        """
        if not self.ssh_client:
            if not self._connect_ssh():
                return False

        try:
            logger.info(f"下载文件: {remote_path} -> {local_path}")

            # 创建本地目录
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            sftp = self.ssh_client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()

            logger.info("文件下载成功")
            return True

        except Exception as e:
            logger.error(f"下载文件异常: {e}")
            return False

    def setup_kernel_build_env(self, kernel_src_path: str) -> bool:
        """
        设置内核构建环境

        Args:
            kernel_src_path: 内核源码路径

        Returns:
            是否设置成功
        """
        try:
            logger.info("设置内核构建环境...")

            # 安装必要的构建工具
            commands = [
                "yum install -y gcc make elfutils-libelf-devel openssl-devel",
                "yum install -y rpm-build rpmdevtools",
                "yum install -y git wget curl",
            ]

            for cmd in commands:
                exit_code, stdout, stderr = self.execute_command(cmd)
                if exit_code != 0:
                    logger.error(f"命令执行失败: {cmd}\n{stderr}")
                    return False

            logger.info("内核构建环境设置成功")
            return True

        except Exception as e:
            logger.error(f"设置内核构建环境异常: {e}")
            return False

    def install_kpatch(self) -> bool:
        """
        安装 kpatch 工具

        Returns:
            是否安装成功
        """
        try:
            logger.info("安装 kpatch 工具...")

            commands = [
                # 安装依赖
                "yum install -y gcc make elfutils-libelf-devel",
                "yum install -y ccache",

                # 克隆 kpatch 仓库
                "cd /root && git clone https://github.com/dynup/kpatch.git || true",
                "cd /root/kpatch && git pull",

                # 编译安装
                "cd /root/kpatch && make",
                "cd /root/kpatch && make install",
            ]

            for cmd in commands:
                exit_code, stdout, stderr = self.execute_command(cmd, timeout=600)
                if exit_code != 0 and "already exists" not in stderr:
                    logger.error(f"命令执行失败: {cmd}\n{stderr}")
                    return False

            # 验证安装
            exit_code, stdout, stderr = self.execute_command("kpatch-build --version")
            if exit_code == 0:
                logger.info(f"kpatch 安装成功: {stdout.strip()}")
                return True
            else:
                logger.error("kpatch 安装验证失败")
                return False

        except Exception as e:
            logger.error(f"安装 kpatch 异常: {e}")
            return False

    def build_livepatch(self, patch_path: str, kernel_src: str, output_dir: str) -> Tuple[bool, str]:
        """
        构建热补丁

        Args:
            patch_path: 补丁文件路径（虚拟机内）
            kernel_src: 内核源码路径（虚拟机内）
            output_dir: 输出目录（虚拟机内）

        Returns:
            (是否成功, 构建日志)
        """
        try:
            logger.info(f"构建热补丁: {patch_path}")

            # 构建命令
            cmd = f"cd {output_dir} && kpatch-build -s {kernel_src} {patch_path}"

            exit_code, stdout, stderr = self.execute_command(cmd, timeout=1800)

            build_log = f"=== STDOUT ===\n{stdout}\n\n=== STDERR ===\n{stderr}"

            if exit_code == 0:
                logger.info("热补丁构建成功")
                return (True, build_log)
            else:
                logger.warning(f"热补丁构建失败 (exit code: {exit_code})")
                return (False, build_log)

        except Exception as e:
            logger.error(f"构建热补丁异常: {e}")
            return (False, str(e))

    def load_livepatch(self, module_path: str) -> Tuple[bool, str]:
        """
        加载热补丁模块

        Args:
            module_path: 模块路径（虚拟机内）

        Returns:
            (是否成功, 输出信息)
        """
        try:
            logger.info(f"加载热补丁: {module_path}")

            cmd = f"kpatch load {module_path}"
            exit_code, stdout, stderr = self.execute_command(cmd)

            output = f"{stdout}\n{stderr}"

            if exit_code == 0:
                logger.info("热补丁加载成功")
                return (True, output)
            else:
                logger.error(f"热补丁加载失败: {output}")
                return (False, output)

        except Exception as e:
            logger.error(f"加载热补丁异常: {e}")
            return (False, str(e))

    def unload_livepatch(self, module_name: str) -> Tuple[bool, str]:
        """
        卸载热补丁模块

        Args:
            module_name: 模块名称

        Returns:
            (是否成功, 输出信息)
        """
        try:
            logger.info(f"卸载热补丁: {module_name}")

            cmd = f"kpatch unload {module_name}"
            exit_code, stdout, stderr = self.execute_command(cmd)

            output = f"{stdout}\n{stderr}"

            if exit_code == 0:
                logger.info("热补丁卸载成功")
                return (True, output)
            else:
                logger.error(f"热补丁卸载失败: {output}")
                return (False, output)

        except Exception as e:
            logger.error(f"卸载热补丁异常: {e}")
            return (False, str(e))

    def list_livepatches(self) -> List[str]:
        """
        列出已加载的热补丁

        Returns:
            热补丁列表
        """
        try:
            cmd = "kpatch list"
            exit_code, stdout, stderr = self.execute_command(cmd)

            if exit_code == 0:
                patches = [line.strip() for line in stdout.split('\n') if line.strip()]
                return patches
            else:
                return []

        except Exception as e:
            logger.error(f"列出热补丁异常: {e}")
            return []

    def get_vm_status(self) -> Dict:
        """
        获取虚拟机状态

        Returns:
            状态字典
        """
        status = {
            'running': self.qemu_process is not None and self.qemu_process.poll() is None,
            'ssh_connected': self.ssh_client is not None,
            'pid': self.qemu_process.pid if self.qemu_process else None,
        }

        if status['ssh_connected']:
            # 获取系统信息
            exit_code, stdout, _ = self.execute_command("uname -r")
            if exit_code == 0:
                status['kernel_version'] = stdout.strip()

            exit_code, stdout, _ = self.execute_command("uptime")
            if exit_code == 0:
                status['uptime'] = stdout.strip()

        return status


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    config = {
        'vm_name': 'test-anolis',
        'image_path': '/tmp/test-anolis.qcow2',
        'memory': '2G',
        'cpus': 2,
        'ssh_port': 2222,
        'ssh_user': 'root',
        'ssh_password': 'anolis',
    }

    manager = QEMUManager(config)
    print(f"QEMU Manager 初始化成功: {manager.vm_name}")
