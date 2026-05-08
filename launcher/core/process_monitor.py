"""
进程监控器 - 监控各服务进程状态
"""
import psutil
import socket
import time
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger

logger = get_logger()


class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    status: ServiceStatus
    pid: Optional[int] = None
    port: Optional[int] = None
    url: Optional[str] = None
    last_error: Optional[str] = None
    start_time: Optional[float] = None


class ProcessMonitor:
    """进程监控器"""
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
    
    def register_service(self, name: str, port: int = None, url: str = None):
        """注册要监控的服务"""
        self._services[name] = ServiceInfo(
            name=name,
            status=ServiceStatus.STOPPED,
            port=port,
            url=url
        )
    
    def update_service(self, name: str, status: ServiceStatus = None, 
                       pid: int = None, error: str = None):
        """更新服务状态"""
        if name not in self._services:
            return
        
        service = self._services[name]
        if status is not None:
            service.status = status
        if pid is not None:
            service.pid = pid
        if error is not None:
            service.last_error = error
        if status == ServiceStatus.RUNNING and service.start_time is None:
            service.start_time = time.time()
        if status == ServiceStatus.STOPPED:
            service.start_time = None
    
    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """获取服务信息"""
        return self._services.get(name)
    
    def get_all_services(self) -> Dict[str, ServiceInfo]:
        """获取所有服务信息"""
        return self._services.copy()
    
    def check_port_open(self, port: int, host: str = "127.0.0.1") -> bool:
        """检测端口是否开放"""
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    def find_pid_by_port(self, port: int) -> Optional[int]:
        """通过端口查找进程PID"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    return conn.pid
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        return None
    
    def is_process_running(self, pid: int) -> bool:
        """检测进程是否仍在运行"""
        try:
            process = psutil.Process(pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """终止进程"""
        try:
            process = psutil.Process(pid)
            if force:
                process.kill()
            else:
                process.terminate()
                # 等待5秒
                gone, alive = psutil.wait_procs([process], timeout=5)
                if process in alive:
                    process.kill()
            return True
        except psutil.NoSuchProcess:
            return True
        except Exception as e:
            logger.error(f"终止进程 {pid} 失败: {e}")
            return False
    
    def kill_process_tree(self, pid: int) -> bool:
        """终止进程及其所有子进程"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            gone, alive = psutil.wait_procs(children, timeout=5)
            for child in alive:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.terminate()
            parent.wait(5)
            return True
        except psutil.NoSuchProcess:
            return True
        except Exception as e:
            logger.error(f"终止进程树 {pid} 失败: {e}")
            return False
    
    def find_processes_by_name(self, name: str) -> List[psutil.Process]:
        """通过进程名查找进程"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if name.lower() in proc.info['name'].lower():
                    processes.append(proc)
                elif proc.info['cmdline'] and any(name.lower() in cmd.lower() for cmd in proc.info['cmdline']):
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes
    
    def refresh_all(self):
        """刷新所有服务状态"""
        for name, service in self._services.items():
            if service.pid is not None:
                if not self.is_process_running(service.pid):
                    service.status = ServiceStatus.STOPPED
                    service.pid = None
            
            # 如果有端口，通过端口检测状态
            if service.port is not None:
                if self.check_port_open(service.port):
                    if service.status != ServiceStatus.RUNNING:
                        service.status = ServiceStatus.RUNNING
                        # 尝试获取PID
                        pid = self.find_pid_by_port(service.port)
                        if pid:
                            service.pid = pid
                else:
                    if service.status == ServiceStatus.RUNNING:
                        service.status = ServiceStatus.STOPPED
                        service.pid = None
