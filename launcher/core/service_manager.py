"""
服务管理器 - 管理4个服务的启动/停止/监控
"""
import os
import subprocess
import time
import signal
from pathlib import Path
from typing import Dict, Optional, Tuple

from core.wsl_manager import WSLManager
from core.process_monitor import ProcessMonitor, ServiceStatus
from core.config_manager import ConfigManager
from utils.logger import get_logger

logger = get_logger()


class ServiceManager:
    """服务管理器"""
    
    SERVICES = ["livekit", "backend", "cpp_inference", "frontend"]
    
    def __init__(self, config: ConfigManager, wsl: WSLManager, monitor: ProcessMonitor):
        self.config = config
        self.wsl = wsl
        self.monitor = monitor
        self._processes: Dict[str, subprocess.Popen] = {}
        self._log_files: Dict[str, object] = {}
        
        # 注册服务到监控器
        ports = config.get("ports")
        self.monitor.register_service("livekit", port=ports.get("livekit"))
        self.monitor.register_service("backend", port=ports.get("backend"))
        self.monitor.register_service("cpp_inference", port=ports.get("cpp_server"))
        self.monitor.register_service("frontend", port=ports.get("frontend"))
    
    def _get_log_file(self, service_name: str):
        """获取服务的日志文件句柄"""
        if service_name not in self._log_files or self._log_files[service_name].closed:
            log_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "user_data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{service_name}.log"
            self._log_files[service_name] = open(log_path, "a", encoding="utf-8")
        return self._log_files[service_name]
    
    def _close_log_files(self):
        """关闭所有日志文件"""
        for f in self._log_files.values():
            if not f.closed:
                f.close()
        self._log_files.clear()
    
    def _get_project_dir(self) -> str:
        """获取 WSL 中的项目目录"""
        wsl_home = self.wsl.get_wsl_home()
        return f"{wsl_home}/.minicpmo"
    
    def _get_webrtc_dir(self) -> str:
        """获取 WebRTC_Demo 在 WSL 中的路径"""
        return f"{self._get_project_dir()}/WebRTC_Demo"
    
    def _get_llamacpp_dir(self) -> str:
        """获取 llama.cpp-omni 在 WSL 中的路径"""
        return f"{self._get_project_dir()}/llama.cpp-omni"
    
    # ==================== LiveKit (Windows 侧) ====================
    
    def start_livekit(self) -> Tuple[bool, str]:
        """启动 LiveKit Server (Windows 原生)"""
        logger.info("[LiveKit] 启动中...")
        self.monitor.update_service("livekit", ServiceStatus.STARTING)
        
        try:
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            livekit_exe = base_dir / "embedded" / "livekit-server.exe"
            webrtc_dir = base_dir / "demo" / "web_demo" / "WebRTC_Demo"
            
            if not livekit_exe.exists():
                # 尝试从 WebRTC_Demo 目录查找
                livekit_exe = webrtc_dir / "livekit-server.exe"
            
            if not livekit_exe.exists():
                err = f"livekit-server.exe 未找到: {livekit_exe}"
                logger.error(f"[LiveKit] {err}")
                self.monitor.update_service("livekit", ServiceStatus.ERROR, error=err)
                return False, err
            
            config_file = webrtc_dir / "livekit-windows.yaml"
            if not config_file.exists():
                err = f"LiveKit 配置文件未找到: {config_file}"
                logger.error(f"[LiveKit] {err}")
                self.monitor.update_service("livekit", ServiceStatus.ERROR, error=err)
                return False, err
            
            log_file = self._get_log_file("livekit")
            
            process = subprocess.Popen(
                [str(livekit_exe), "--config", str(config_file)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self._processes["livekit"] = process
            
            # 等待端口开放
            port = self.config.get("ports.livekit")
            for i in range(10):
                if self.monitor.check_port_open(port):
                    logger.info(f"[LiveKit] 启动成功 (PID: {process.pid}, Port: {port})")
                    self.monitor.update_service("livekit", ServiceStatus.RUNNING, pid=process.pid)
                    return True, f"启动成功 (PID: {process.pid})"
                time.sleep(1)
            
            err = "LiveKit 端口未开放，可能启动失败"
            logger.error(f"[LiveKit] {err}")
            self.monitor.update_service("livekit", ServiceStatus.ERROR, error=err)
            return False, err
            
        except Exception as e:
            err = str(e)
            logger.error(f"[LiveKit] 启动异常: {err}")
            self.monitor.update_service("livekit", ServiceStatus.ERROR, error=err)
            return False, err
    
    def stop_livekit(self) -> bool:
        """停止 LiveKit Server"""
        logger.info("[LiveKit] 停止中...")
        if "livekit" in self._processes:
            process = self._processes["livekit"]
            self.monitor.kill_process_tree(process.pid)
            del self._processes["livekit"]
        
        # 也尝试通过进程名查找并终止
        for proc in self.monitor.find_processes_by_name("livekit-server"):
            self.monitor.kill_process_tree(proc.pid)
        
        self.monitor.update_service("livekit", ServiceStatus.STOPPED)
        logger.info("[LiveKit] 已停止")
        return True
    
    # ==================== Backend (WSL) ====================
    
    def start_backend(self) -> Tuple[bool, str]:
        """启动 Backend (FastAPI)"""
        logger.info("[Backend] 启动中...")
        self.monitor.update_service("backend", ServiceStatus.STARTING)
        
        try:
            webrtc_dir = self._get_webrtc_dir()
            backend_dir = f"{webrtc_dir}/omini_backend_code/code"
            port = self.config.get("ports.backend")
            livekit_port = self.config.get("ports.livekit")
            
            # 环境变量
            env_vars = {
                "APP_ENV": "local",
                "SERVER_PORT": str(port),
                "LIVEKIT_URL": f"ws://localhost:{livekit_port}",
                "LIVEKIT_API_KEY": self.config.get("livekit.api_key"),
                "LIVEKIT_API_SECRET": self.config.get("livekit.api_secret"),
                "WORKERS": "1",
                "NUMBA_CACHE_DIR": "/tmp/numba_cache",
            }
            
            env_str = " ".join([f'{k}="{v}"' for k, v in env_vars.items()])
            
            log_file = self._get_log_file("backend")
            
            # 在 WSL 中启动
            command = f"cd {backend_dir} && {env_str} python main.py"
            process = self.wsl.exec_command_async(command, stdout_file=log_file, stderr_file=log_file)
            
            self._processes["backend"] = process
            
            # 等待端口开放
            for i in range(30):
                if self.monitor.check_port_open(port):
                    logger.info(f"[Backend] 启动成功 (PID: {process.pid}, Port: {port})")
                    self.monitor.update_service("backend", ServiceStatus.RUNNING, pid=process.pid)
                    return True, f"启动成功 (PID: {process.pid})"
                time.sleep(1)
            
            err = "Backend 端口未开放"
            logger.error(f"[Backend] {err}")
            self.monitor.update_service("backend", ServiceStatus.ERROR, error=err)
            return False, err
            
        except Exception as e:
            err = str(e)
            logger.error(f"[Backend] 启动异常: {err}")
            self.monitor.update_service("backend", ServiceStatus.ERROR, error=err)
            return False, err
    
    def stop_backend(self) -> bool:
        """停止 Backend"""
        logger.info("[Backend] 停止中...")
        if "backend" in self._processes:
            process = self._processes["backend"]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del self._processes["backend"]
        
        self.monitor.update_service("backend", ServiceStatus.STOPPED)
        logger.info("[Backend] 已停止")
        return True
    
    # ==================== C++ Inference (WSL) ====================
    
    def start_cpp_inference(self) -> Tuple[bool, str]:
        """启动 C++ 推理服务"""
        logger.info("[CPP Inference] 启动中...")
        self.monitor.update_service("cpp_inference", ServiceStatus.STARTING)
        
        try:
            webrtc_dir = self._get_webrtc_dir()
            llamacpp_dir = self._get_llamacpp_dir()
            port = self.config.get("ports.cpp_server")
            backend_port = self.config.get("ports.backend")
            model_dir = self.config.get("model.dir").replace("~", self.wsl.get_wsl_home())
            cpp_mode = self.config.get("cpp_mode", "simplex")
            
            server_script = f"{webrtc_dir}/cpp_server/minicpmo_cpp_http_server.py"
            ref_audio = f"{webrtc_dir}/cpp_server/assets/default_ref_audio.wav"
            
            env_vars = {
                "LLAMACPP_ROOT": llamacpp_dir,
                "MODEL_DIR": model_dir,
                "REF_AUDIO": ref_audio,
                "CUDA_VISIBLE_DEVICES": "0",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            }
            
            env_str = " ".join([f'{k}="{v}"' for k, v in env_vars.items()])
            mode_flag = f"--{cpp_mode}"
            
            log_file = self._get_log_file("cpp_inference")
            
            command = (
                f"cd {llamacpp_dir} && {env_str} "
                f"python {server_script} "
                f"--llamacpp-root {llamacpp_dir} "
                f"--model-dir {model_dir} "
                f"--port {port} "
                f"{mode_flag}"
            )
            
            process = self.wsl.exec_command_async(command, stdout_file=log_file, stderr_file=log_file)
            self._processes["cpp_inference"] = process
            
            # C++ 推理服务启动较慢（模型加载）
            logger.info("[CPP Inference] 等待模型加载（可能需要2-3分钟）...")
            for i in range(300):  # 最多等5分钟
                if self.monitor.check_port_open(port):
                    # 额外等待健康检查
                    time.sleep(2)
                    logger.info(f"[CPP Inference] 启动成功 (PID: {process.pid}, Port: {port})")
                    self.monitor.update_service("cpp_inference", ServiceStatus.RUNNING, pid=process.pid)
                    
                    # 注册到 backend
                    self._register_inference_service(port, backend_port)
                    return True, f"启动成功 (PID: {process.pid})"
                time.sleep(1)
                if i % 30 == 0 and i > 0:
                    logger.info(f"[CPP Inference] 仍在加载... ({i}s/300s)")
            
            err = "C++ 推理服务启动超时"
            logger.error(f"[CPP Inference] {err}")
            self.monitor.update_service("cpp_inference", ServiceStatus.ERROR, error=err)
            return False, err
            
        except Exception as e:
            err = str(e)
            logger.error(f"[CPP Inference] 启动异常: {err}")
            self.monitor.update_service("cpp_inference", ServiceStatus.ERROR, error=err)
            return False, err
    
    def _register_inference_service(self, cpp_port: int, backend_port: int):
        """注册推理服务到 backend"""
        try:
            import requests
            import json
            
            register_body = {
                "ip": "127.0.0.1",
                "port": cpp_port,
                "model_port": cpp_port,
                "model_type": self.config.get("cpp_mode", "simplex"),
                "session_type": "release",
                "service_name": "o45-cpp",
            }
            
            url = f"http://localhost:{backend_port}/api/inference/register"
            response = requests.post(url, json=register_body, timeout=10)
            if response.status_code == 200:
                logger.info("[CPP Inference] 推理服务注册成功")
            else:
                logger.warning(f"[CPP Inference] 推理服务注册失败: {response.status_code}")
        except Exception as e:
            logger.warning(f"[CPP Inference] 推理服务注册异常: {e}")
    
    def stop_cpp_inference(self) -> bool:
        """停止 C++ 推理服务"""
        logger.info("[CPP Inference] 停止中...")
        if "cpp_inference" in self._processes:
            process = self._processes["cpp_inference"]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del self._processes["cpp_inference"]
        
        # 也尝试终止 WSL 中的相关进程
        self.wsl.exec_command("pkill -f 'minicpmo_cpp_http_server' || true", timeout=10)
        self.wsl.exec_command("pkill -f 'llama-server' || true", timeout=10)
        
        self.monitor.update_service("cpp_inference", ServiceStatus.STOPPED)
        logger.info("[CPP Inference] 已停止")
        return True
    
    # ==================== Frontend (WSL) ====================
    
    def start_frontend(self) -> Tuple[bool, str]:
        """启动 Frontend (Vue + 静态服务器)"""
        logger.info("[Frontend] 启动中...")
        self.monitor.update_service("frontend", ServiceStatus.STARTING)
        
        try:
            webrtc_dir = self._get_webrtc_dir()
            frontend_dir = f"{webrtc_dir}/o45-frontend"
            port = self.config.get("ports.frontend")
            backend_port = self.config.get("ports.backend")
            livekit_port = self.config.get("ports.livekit")
            frontend_mode = self.config.get("frontend_mode", "prod")
            cpp_mode = self.config.get("cpp_mode", "simplex")
            
            log_file = self._get_log_file("frontend")
            
            if frontend_mode == "prod":
                # 生产模式：使用 serve-prod.mjs
                command = (
                    f"cd {frontend_dir} && "
                    f"VITE_CPP_MODE={cpp_mode} node serve-prod.mjs "
                    f"--port {port} --backend {backend_port} --livekit {livekit_port}"
                )
            else:
                # 开发模式：使用 Vite
                command = (
                    f"cd {frontend_dir} && "
                    f"VITE_CPP_MODE={cpp_mode} pnpm run dev:external"
                )
            
            process = self.wsl.exec_command_async(command, stdout_file=log_file, stderr_file=log_file)
            self._processes["frontend"] = process
            
            # 等待端口开放
            for i in range(30):
                if self.monitor.check_port_open(port):
                    logger.info(f"[Frontend] 启动成功 (PID: {process.pid}, Port: {port})")
                    self.monitor.update_service("frontend", ServiceStatus.RUNNING, pid=process.pid)
                    return True, f"启动成功 (PID: {process.pid})"
                time.sleep(1)
            
            err = "Frontend 端口未开放"
            logger.error(f"[Frontend] {err}")
            self.monitor.update_service("frontend", ServiceStatus.ERROR, error=err)
            return False, err
            
        except Exception as e:
            err = str(e)
            logger.error(f"[Frontend] 启动异常: {err}")
            self.monitor.update_service("frontend", ServiceStatus.ERROR, error=err)
            return False, err
    
    def stop_frontend(self) -> bool:
        """停止 Frontend"""
        logger.info("[Frontend] 停止中...")
        if "frontend" in self._processes:
            process = self._processes["frontend"]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del self._processes["frontend"]
        
        self.wsl.exec_command("pkill -f 'serve-prod.mjs' || true", timeout=10)
        
        self.monitor.update_service("frontend", ServiceStatus.STOPPED)
        logger.info("[Frontend] 已停止")
        return True
    
    # ==================== 批量操作 ====================
    
    def start_all(self) -> Dict[str, Tuple[bool, str]]:
        """按顺序启动所有服务"""
        results = {}
        
        # 1. LiveKit
        results["livekit"] = self.start_livekit()
        if not results["livekit"][0]:
            logger.error("LiveKit 启动失败，中止后续服务")
            return results
        
        # 2. Backend
        results["backend"] = self.start_backend()
        if not results["backend"][0]:
            logger.error("Backend 启动失败，中止后续服务")
            self.stop_livekit()
            return results
        
        # 3. C++ Inference
        results["cpp_inference"] = self.start_cpp_inference()
        if not results["cpp_inference"][0]:
            logger.warning("C++ Inference 启动失败，但 Frontend 仍可启动（仅无推理功能）")
        
        # 4. Frontend
        results["frontend"] = self.start_frontend()
        if not results["frontend"][0]:
            logger.error("Frontend 启动失败")
        
        return results
    
    def stop_all(self):
        """停止所有服务（反向顺序）"""
        logger.info("停止所有服务...")
        self.stop_frontend()
        self.stop_cpp_inference()
        self.stop_backend()
        self.stop_livekit()
        self._close_log_files()
        logger.info("所有服务已停止")
    
    def restart_all(self) -> Dict[str, Tuple[bool, str]]:
        """重启所有服务"""
        self.stop_all()
        time.sleep(2)
        return self.start_all()
    
    def get_status_summary(self) -> str:
        """获取状态摘要"""
        services = self.monitor.get_all_services()
        lines = []
        for name, info in services.items():
            status_icon = {
                ServiceStatus.RUNNING: "🟢",
                ServiceStatus.STARTING: "🟡",
                ServiceStatus.STOPPED: "🔴",
                ServiceStatus.ERROR: "❌",
                ServiceStatus.UNKNOWN: "⚪",
            }.get(info.status, "⚪")
            lines.append(f"{status_icon} {name}: {info.status.value}")
        return "\n".join(lines)
