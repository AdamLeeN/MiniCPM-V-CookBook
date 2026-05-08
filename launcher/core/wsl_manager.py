"""
WSL2 管理器 - 检测/安装/管理 WSL2 环境
"""
import os
import subprocess
import time
from typing import Tuple, Optional
from pathlib import Path

from utils.logger import get_logger

logger = get_logger()


class WSLManager:
    """WSL2 管理器"""
    
    def __init__(self, distro: str = "Ubuntu"):
        self.distro = distro
        self._wsl_available = None
    
    def check_wsl_installed(self) -> bool:
        """检测 WSL2 是否已安装"""
        try:
            result = subprocess.run(
                ["wsl", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def check_wsl2_kernel(self) -> bool:
        """检测 WSL2 内核版本（区分 WSL1/WSL2）"""
        try:
            result = subprocess.run(
                ["wsl", "--status"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            output = result.stdout + result.stderr
            # WSL2 会显示 "默认版本: 2" 或 "Default Version: 2"
            return "2" in output and ("默认版本" in output or "Default Version" in output)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def list_distros(self) -> list:
        """列出已安装的 WSL 发行版"""
        try:
            result = subprocess.run(
                ["wsl", "--list", "--quiet"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                # 输出可能有特殊编码，尝试解码
                output = result.stdout
                distros = [d.strip() for d in output.split('\n') if d.strip()]
                return distros
            return []
        except Exception as e:
            logger.error(f"列出WSL发行版失败: {e}")
            return []
    
    def check_distro_installed(self, distro: str = None) -> bool:
        """检测指定发行版是否已安装"""
        if distro is None:
            distro = self.distro
        distros = self.list_distros()
        # WSL 列表输出可能包含 \x00 等特殊字符
        for d in distros:
            if distro.lower() in d.lower().replace('\x00', ''):
                return True
        return False
    
    def install_wsl(self) -> Tuple[bool, str]:
        """
        安装 WSL2（需要管理员权限）
        
        Returns:
            (success, message)
        """
        logger.info("开始安装 WSL2...")
        try:
            # 使用 --no-distribution 只安装 WSL 不安装发行版
            result = subprocess.run(
                ["wsl", "--install", "--no-distribution"],
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                msg = "WSL2 安装命令已执行。系统需要重启以完成安装。"
                logger.info(msg)
                return True, msg
            else:
                err = result.stderr or result.stdout
                logger.error(f"WSL2 安装失败: {err}")
                return False, f"安装失败: {err}"
        except Exception as e:
            logger.error(f"WSL2 安装异常: {e}")
            return False, str(e)
    
    def install_distro(self, distro: str = None) -> Tuple[bool, str]:
        """
        安装指定发行版
        
        Returns:
            (success, message)
        """
        if distro is None:
            distro = self.distro
        
        logger.info(f"开始安装 {distro}...")
        try:
            result = subprocess.run(
                ["wsl", "--install", "-d", distro],
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                msg = f"{distro} 安装成功"
                logger.info(msg)
                return True, msg
            else:
                err = result.stderr or result.stdout
                logger.error(f"{distro} 安装失败: {err}")
                return False, f"安装失败: {err}"
        except Exception as e:
            logger.error(f"{distro} 安装异常: {e}")
            return False, str(e)
    
    def check_mirrored_networking(self) -> bool:
        """检测 WSL2 是否启用了 mirrored 网络模式"""
        wslconfig_path = Path.home() / ".wslconfig"
        if not wslconfig_path.exists():
            return False
        try:
            content = wslconfig_path.read_text(encoding='utf-8')
            return 'networkingMode=mirrored' in content
        except Exception:
            return False
    
    def enable_mirrored_networking(self) -> bool:
        """启用 WSL2 mirrored 网络模式"""
        wslconfig_path = Path.home() / ".wslconfig"
        try:
            if wslconfig_path.exists():
                content = wslconfig_path.read_text(encoding='utf-8')
                if 'networkingMode' in content:
                    # 替换现有配置
                    import re
                    content = re.sub(
                        r'networkingMode\s*=\s*\w+',
                        'networkingMode=mirrored',
                        content
                    )
                else:
                    content += "\n[network]\nnetworkingMode=mirrored\n"
            else:
                content = "[wsl2]\n[network]\nnetworkingMode=mirrored\n"
            
            wslconfig_path.write_text(content, encoding='utf-8')
            logger.info("已启用 WSL2 mirrored 网络模式，需要重启WSL生效")
            return True
        except Exception as e:
            logger.error(f"启用 mirrored 网络模式失败: {e}")
            return False
    
    def exec_command(self, command: str, cwd: str = None, timeout: int = 60) -> Tuple[int, str, str]:
        """
        在 WSL 中执行命令
        
        Args:
            command: 要在 WSL 中执行的命令
            cwd: 工作目录（Windows 路径，会自动转换）
            timeout: 超时时间（秒）
            
        Returns:
            (returncode, stdout, stderr)
        """
        wsl_cmd = ["wsl", "-d", self.distro]
        if cwd:
            # 转换 Windows 路径为 WSL 路径
            wsl_cwd = self.to_wsl_path(cwd)
            wsl_cmd.extend(["--cd", wsl_cwd])
        wsl_cmd.extend(["bash", "-c", command])
        
        try:
            result = subprocess.run(
                wsl_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"WSL 命令超时: {command}")
            return -1, "", "Timeout"
        except Exception as e:
            logger.error(f"WSL 命令异常: {e}")
            return -1, "", str(e)
    
    def exec_command_async(self, command: str, cwd: str = None, 
                          stdout_file=None, stderr_file=None) -> subprocess.Popen:
        """
        在 WSL 中异步执行命令（用于启动服务）
        
        Returns:
            Popen 进程对象
        """
        wsl_cmd = ["wsl", "-d", self.distro]
        if cwd:
            wsl_cwd = self.to_wsl_path(cwd)
            wsl_cmd.extend(["--cd", wsl_cwd])
        wsl_cmd.extend(["bash", "-c", command])
        
        kwargs = {
            'creationflags': subprocess.CREATE_NO_WINDOW,
        }
        if stdout_file:
            kwargs['stdout'] = stdout_file
        if stderr_file:
            kwargs['stderr'] = stderr_file
            
        return subprocess.Popen(wsl_cmd, **kwargs)
    
    def to_wsl_path(self, windows_path: str) -> str:
        """将 Windows 路径转换为 WSL 路径"""
        path = Path(windows_path).resolve()
        # C:\Users\xxx -> /mnt/c/Users/xxx
        drive = path.drive.lower().rstrip(':')
        rest = str(path).replace(path.drive, '')
        rest = rest.replace('\\', '/')
        return f"/mnt/{drive}{rest}"
    
    def from_wsl_path(self, wsl_path: str) -> str:
        """将 WSL 路径转换为 Windows 路径"""
        # /mnt/c/Users/xxx -> C:\Users\xxx
        if wsl_path.startswith('/mnt/'):
            parts = wsl_path.split('/')
            drive = parts[2].upper() + ':'
            rest = '/'.join(parts[3:])
            return drive + '\\' + rest.replace('/', '\\')
        return wsl_path
    
    def shutdown(self):
        """关闭 WSL 实例"""
        try:
            subprocess.run(
                ["wsl", "--shutdown"],
                capture_output=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            logger.info("WSL 已关闭")
        except Exception as e:
            logger.error(f"关闭 WSL 失败: {e}")
    
    def get_wsl_home(self) -> str:
        """获取 WSL 中的用户 home 目录"""
        rc, stdout, _ = self.exec_command("echo $HOME", timeout=10)
        if rc == 0:
            return stdout.strip()
        return "/home/user"
