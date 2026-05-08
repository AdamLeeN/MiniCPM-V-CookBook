"""
主窗口 - MiniCPM-o Launcher 主界面
"""
import os
import webbrowser
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSplitter, QMessageBox,
    QProgressDialog, QDialog, QLineEdit, QComboBox,
    QFormLayout, QDialogButtonBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

from core.config_manager import ConfigManager
from core.wsl_manager import WSLManager
from core.process_monitor import ProcessMonitor
from core.service_manager import ServiceManager
from ui.status_panel import StatusPanel
from ui.log_viewer import LogViewer
from ui.setup_wizard import SetupWizard
from utils.logger import setup_logger, LogEmitter, get_logger





class ConfigDialog(QDialog):
    """配置对话框"""
    
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("配置")
        self.setMinimumWidth(400)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # 端口配置
        ports_group = QGroupBox("端口配置")
        ports_layout = QFormLayout()
        
        self.livekit_port = QLineEdit(str(self.config.get("ports.livekit")))
        self.backend_port = QLineEdit(str(self.config.get("ports.backend")))
        self.frontend_port = QLineEdit(str(self.config.get("ports.frontend")))
        self.cpp_port = QLineEdit(str(self.config.get("ports.cpp_server")))
        
        ports_layout.addRow("LiveKit:", self.livekit_port)
        ports_layout.addRow("Backend:", self.backend_port)
        ports_layout.addRow("Frontend:", self.frontend_port)
        ports_layout.addRow("C++ Inference:", self.cpp_port)
        ports_group.setLayout(ports_layout)
        layout.addWidget(ports_group)
        
        # 模型配置
        model_group = QGroupBox("模型配置")
        model_layout = QFormLayout()
        
        self.model_dir = QLineEdit(self.config.get("model.dir"))
        self.model_quant = QComboBox()
        self.model_quant.addItems(["Q4_K_M", "Q4_K_S", "Q5_K_M", "Q8_0", "F16"])
        self.model_quant.setCurrentText(self.config.get("model.quant"))
        
        model_layout.addRow("模型目录:", self.model_dir)
        model_layout.addRow("量化级别:", self.model_quant)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # 运行模式
        mode_group = QGroupBox("运行模式")
        mode_layout = QFormLayout()
        
        self.cpp_mode = QComboBox()
        self.cpp_mode.addItems(["simplex", "duplex"])
        self.cpp_mode.setCurrentText(self.config.get("cpp_mode"))
        
        self.frontend_mode = QComboBox()
        self.frontend_mode.addItems(["prod", "dev"])
        self.frontend_mode.setCurrentText(self.config.get("frontend_mode"))
        
        mode_layout.addRow("CPP 模式:", self.cpp_mode)
        mode_layout.addRow("前端模式:", self.frontend_mode)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _save(self):
        self.config.set("ports.livekit", int(self.livekit_port.text()))
        self.config.set("ports.backend", int(self.backend_port.text()))
        self.config.set("ports.frontend", int(self.frontend_port.text()))
        self.config.set("ports.cpp_server", int(self.cpp_port.text()))
        self.config.set("model.dir", self.model_dir.text())
        self.config.set("model.quant", self.model_quant.currentText())
        self.config.set("cpp_mode", self.cpp_mode.currentText())
        self.config.set("frontend_mode", self.frontend_mode.currentText())
        self.accept()


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MiniCPM-o WebRTC Launcher")
        self.setMinimumSize(1000, 700)
        
        # 初始化核心组件
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.log_dir = self.base_dir / "user_data" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_emitter = LogEmitter()
        setup_logger(log_dir=str(self.log_dir))
        self.logger = get_logger()
        
        self.config = ConfigManager()
        self.wsl = WSLManager(distro=self.config.get("wsl.distro", "Ubuntu"))
        self.monitor = ProcessMonitor()
        self.service_manager = ServiceManager(self.config, self.wsl, self.monitor)
        
        self._init_ui()
        self._check_first_run()
    
    def _init_ui(self):
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title = QLabel("MiniCPM-o WebRTC Launcher")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1976d2;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 副标题
        subtitle = QLabel("一键启动 WebRTC 实时语音对话服务")
        subtitle.setStyleSheet("font-size: 14px; color: #666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # 控制按钮栏
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ 启动服务")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.start_btn.clicked.connect(self._start_services)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ 停止服务")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #da190b; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.stop_btn.clicked.connect(self._stop_services)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.restart_btn = QPushButton("🔄 重启")
        self.restart_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #e68900; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.restart_btn.clicked.connect(self._restart_services)
        self.restart_btn.setEnabled(False)
        btn_layout.addWidget(self.restart_btn)
        
        btn_layout.addStretch()
        
        self.config_btn = QPushButton("⚙️ 配置")
        self.config_btn.clicked.connect(self._show_config)
        btn_layout.addWidget(self.config_btn)
        
        self.open_btn = QPushButton("🌐 打开网页")
        self.open_btn.clicked.connect(self._open_browser)
        self.open_btn.setEnabled(False)
        btn_layout.addWidget(self.open_btn)
        
        layout.addLayout(btn_layout)
        
        # 分割器：状态面板 + 日志查看器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 状态面板
        self.status_panel = StatusPanel(self.monitor)
        self.status_panel.setMaximumHeight(350)
        splitter.addWidget(self.status_panel)
        
        # 日志查看器
        self.log_viewer = LogViewer(str(self.log_dir))
        self.log_viewer.connect_log_emitter(self.log_emitter)
        splitter.addWidget(self.log_viewer)
        
        splitter.setSizes([300, 400])
        layout.addWidget(splitter)
        
        # 状态栏
        self.status_bar = QLabel("就绪")
        self.status_bar.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.status_bar)
    
    def _check_first_run(self):
        """检查是否首次运行"""
        if self.config.get("first_run", True):
            self.logger.info("首次运行，显示初始化向导")
            self._show_setup_wizard()
        else:
            # 检查 WSL2
            if not self.wsl.check_wsl_installed():
                QMessageBox.warning(self, "WSL2 未安装", 
                    "WSL2 未安装，请先安装 WSL2 并重启系统。\n"
                    "在 PowerShell (管理员) 中运行: wsl --install")
    
    def _show_setup_wizard(self):
        """显示首次运行向导"""
        wizard = SetupWizard(self.wsl, self.config, self)
        wizard.setup_finished.connect(self._on_wizard_finished)
        wizard.exec()
    
    def _on_wizard_finished(self, success: bool):
        """向导完成回调"""
        if success:
            self.status_bar.setText("就绪 - 可以启动服务")
        else:
            self.status_bar.setText("初始化未完成，请重新运行向导")
    
    def _get_wsl_project_dir(self) -> str:
        """获取 WSL 中的项目目录"""
        wsl_home = self.wsl.get_wsl_home()
        return f"{wsl_home}/.minicpmo"
    
    def _start_services(self):
        """启动所有服务"""
        self.logger.info("开始启动所有服务...")
        self.status_bar.setText("启动服务中...")
        self.start_btn.setEnabled(False)
        
        # 在单独的线程中启动
        self.start_thread = ServiceStartThread(self.service_manager)
        self.start_thread.finished_signal.connect(self._on_start_finished)
        self.start_thread.start()
        
        self.log_viewer.start_all_monitoring()
        self.status_panel.start_refresh()
    
    def _on_start_finished(self, results: dict):
        success_count = sum(1 for ok, _ in results.values() if ok)
        total = len(results)
        
        if success_count == total:
            self.status_bar.setText(f"所有 {total} 个服务已启动")
            self.stop_btn.setEnabled(True)
            self.restart_btn.setEnabled(True)
            self.open_btn.setEnabled(True)
        else:
            self.status_bar.setText(f"{success_count}/{total} 个服务启动成功")
            self.stop_btn.setEnabled(True)
            self.restart_btn.setEnabled(True)
        
        # 显示结果
        msg = "启动结果:\n"
        for name, (ok, info) in results.items():
            status = "✅" if ok else "❌"
            msg += f"{status} {name}: {info}\n"
        
        self.logger.info(msg)
    
    def _stop_services(self):
        """停止所有服务"""
        self.logger.info("停止所有服务...")
        self.status_bar.setText("停止服务中...")
        
        self.service_manager.stop_all()
        self.log_viewer.stop_all_monitoring()
        self.status_panel.stop_refresh()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.restart_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.status_bar.setText("所有服务已停止")
        self.logger.info("所有服务已停止")
    
    def _restart_services(self):
        """重启所有服务"""
        self.logger.info("重启所有服务...")
        self.status_bar.setText("重启服务中...")
        
        self.service_manager.restart_all()
        self.status_bar.setText("服务已重启")
        self.logger.info("服务已重启")
    
    def _show_config(self):
        """显示配置对话框"""
        dialog = ConfigDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.logger.info("配置已更新")
    
    def _open_browser(self):
        """打开浏览器访问前端"""
        port = self.config.get("ports.frontend")
        url = f"https://127.0.0.1:{port}"
        webbrowser.open(url)
        self.logger.info(f"打开浏览器: {url}")
    
    def closeEvent(self, event):
        """关闭窗口时停止所有服务"""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "退出将停止所有服务，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.service_manager.stop_all()
            event.accept()
        else:
            event.ignore()


class ServiceStartThread(QThread):
    """服务启动线程"""
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, service_manager: ServiceManager):
        super().__init__()
        self.service_manager = service_manager
    
    def run(self):
        results = self.service_manager.start_all()
        self.finished_signal.emit(results)
