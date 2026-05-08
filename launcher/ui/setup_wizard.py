"""
首次运行向导 - 引导用户完成初始化
"""
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit,
    QComboBox, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core.wsl_manager import WSLManager
from core.model_downloader import ModelDownloader
from core.config_manager import ConfigManager
from utils.logger import get_logger

logger = get_logger()


class SetupWizardThread(QThread):
    """初始化工作线程"""
    progress = pyqtSignal(str, int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, wsl: WSLManager, project_dir: str, model_dir: str, quant: str):
        super().__init__()
        self.wsl = wsl
        self.project_dir = project_dir
        self.model_dir = model_dir
        self.quant = quant
    
    def run(self):
        try:
            import os
            from pathlib import Path
            
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            # 1. 复制源码
            self.progress.emit("复制项目文件到 WSL2...", 10)
            self.wsl.exec_command(f"mkdir -p {self.project_dir}", timeout=10)
            
            webrtc_src = base_dir / "demo" / "web_demo" / "WebRTC_Demo"
            if webrtc_src.exists():
                wsl_path = self.wsl.to_wsl_path(str(webrtc_src))
                rc, _, err = self.wsl.exec_command(
                    f"cp -r {wsl_path} {self.project_dir}/",
                    timeout=120
                )
                if rc != 0:
                    self.finished_signal.emit(False, f"复制项目文件失败: {err}")
                    return
            
            # 2. 运行 setup_wsl.sh
            self.progress.emit("安装依赖（Python/Node.js/cmake）...", 30)
            script_path = base_dir / "launcher" / "scripts" / "setup_wsl.sh"
            wsl_script = self.wsl.to_wsl_path(str(script_path))
            
            rc, stdout, stderr = self.wsl.exec_command(
                f"bash {wsl_script} {self.project_dir}",
                timeout=1800
            )
            
            if rc != 0:
                self.finished_signal.emit(False, f"依赖安装失败: {stderr or stdout}")
                return
            
            # 3. 下载模型
            self.progress.emit("下载模型（约需10-30分钟）...", 60)
            downloader = ModelDownloader(self.wsl)
            
            success = downloader.download_model(
                self.model_dir,
                self.quant,
                lambda msg, pct: self.progress.emit(msg, 60 + int(pct * 0.35))
            )
            
            if not success:
                self.finished_signal.emit(False, "模型下载失败")
                return
            
            self.progress.emit("初始化完成", 100)
            self.finished_signal.emit(True, "初始化完成！可以启动服务了。")
            
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class SetupWizard(QWizard):
    """首次运行向导"""
    
    setup_finished = pyqtSignal(bool)
    
    def __init__(self, wsl: WSLManager, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.wsl = wsl
        self.config = config
        self.setWindowTitle("MiniCPM-o 首次运行向导")
        self.setMinimumSize(600, 500)
        
        self._init_pages()
    
    def _init_pages(self):
        # 欢迎页
        welcome = QWizardPage()
        welcome.setTitle("欢迎使用 MiniCPM-o WebRTC Launcher")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(
            "本向导将帮助您完成首次运行所需的初始化设置。\n\n"
            "初始化内容包括：\n"
            "  • 检查 WSL2 环境\n"
            "  • 安装 Python、Node.js、cmake 等依赖\n"
            "  • 编译 llama-server（C++推理引擎）\n"
            "  • 下载 GGUF 模型（约 5-9GB）\n\n"
            "整个过程可能需要 30-60 分钟，请耐心等待。"
        ))
        welcome.setLayout(layout)
        self.addPage(welcome)
        
        # WSL2 检查页
        wsl_page = QWizardPage()
        wsl_page.setTitle("WSL2 环境检查")
        wsl_layout = QVBoxLayout()
        
        self.wsl_status = QLabel("检测中...")
        wsl_layout.addWidget(self.wsl_status)
        
        self.wsl_fix_btn = QPushButton("安装 WSL2")
        self.wsl_fix_btn.clicked.connect(self._install_wsl)
        self.wsl_fix_btn.setVisible(False)
        wsl_layout.addWidget(self.wsl_fix_btn)
        
        wsl_page.setLayout(wsl_layout)
        self.addPage(wsl_page)
        
        # 模型配置页
        model_page = QWizardPage()
        model_page.setTitle("模型配置")
        model_layout = QVBoxLayout()
        
        model_layout.addWidget(QLabel("选择模型量化级别（影响显存占用和推理质量）："))
        
        self.quant_combo = QComboBox()
        self.quant_combo.addItems([
            "Q4_K_M (推荐，~5GB，性价比高)",
            "Q4_K_S (~4.8GB，更小)",
            "Q5_K_M (~5.8GB，更好质量)",
            "Q8_0 (~8.7GB，高质量)",
            "F16 (~16GB，最佳质量)",
        ])
        model_layout.addWidget(self.quant_combo)
        
        model_layout.addWidget(QLabel("模型保存目录（WSL 路径）："))
        self.model_dir_input = QLineEdit("~/models/openbmb/MiniCPM-o-4_5-gguf")
        model_layout.addWidget(self.model_dir_input)
        
        model_page.setLayout(model_layout)
        self.addPage(model_page)
        
        # 初始化进度页
        progress_page = QWizardPage()
        progress_page.setTitle("初始化中...")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("准备开始...")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_log = QTextEdit()
        self.progress_log.setReadOnly(True)
        self.progress_log.setMaximumHeight(150)
        progress_layout.addWidget(self.progress_log)
        
        progress_page.setLayout(progress_layout)
        self.addPage(progress_page)
        
        # 完成页
        finish_page = QWizardPage()
        finish_page.setTitle("初始化完成")
        self.finish_layout = QVBoxLayout()
        self.finish_label = QLabel("")
        self.finish_layout.addWidget(self.finish_label)
        finish_page.setLayout(self.finish_layout)
        self.addPage(finish_page)
    
    def initializePage(self, id):
        super().initializePage(id)
        
        if id == 1:  # WSL2 检查页
            self._check_wsl()
        elif id == 3:  # 进度页
            self._start_setup()
    
    def _check_wsl(self):
        """检查 WSL2 状态"""
        if self.wsl.check_wsl_installed():
            if self.wsl.check_distro_installed():
                self.wsl_status.setText("✅ WSL2 和 Ubuntu 发行版已就绪")
                self.wsl_fix_btn.setVisible(False)
            else:
                self.wsl_status.setText("⚠️ WSL2 已安装，但 Ubuntu 发行版未安装")
                self.wsl_fix_btn.setText("安装 Ubuntu")
                self.wsl_fix_btn.setVisible(True)
        else:
            self.wsl_status.setText("❌ WSL2 未安装")
            self.wsl_fix_btn.setText("安装 WSL2")
            self.wsl_fix_btn.setVisible(True)
    
    def _install_wsl(self):
        """安装 WSL2 或 Ubuntu"""
        if not self.wsl.check_wsl_installed():
            success, msg = self.wsl.install_wsl()
            if success:
                QMessageBox.information(self, "需要重启", 
                    "WSL2 安装命令已执行。\n请重启系统后再次运行本程序。")
            else:
                QMessageBox.critical(self, "安装失败", msg)
        else:
            success, msg = self.wsl.install_distro()
            if success:
                self._check_wsl()
            else:
                QMessageBox.critical(self, "安装失败", msg)
    
    def _start_setup(self):
        """开始初始化"""
        quant = self.quant_combo.currentText().split()[0]
        model_dir = self.model_dir_input.text().replace("~", self.wsl.get_wsl_home())
        project_dir = f"{self.wsl.get_wsl_home()}/.minicpmo"
        
        self.config.set("model.quant", quant)
        self.config.set("model.dir", self.model_dir_input.text())
        
        self.worker = SetupWizardThread(self.wsl, project_dir, model_dir, quant)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, message: str, percent: int):
        self.progress_label.setText(message)
        self.progress_bar.setValue(percent)
        self.progress_log.append(message)
    
    def _on_finished(self, success: bool, message: str):
        self.finish_label.setText(message)
        self.config.set("first_run", False)
        self.setup_finished.emit(success)
        
        if success:
            self.button(QWizard.WizardButton.Finish).setEnabled(True)
        else:
            self.button(QWizard.WizardButton.Finish).setEnabled(True)
            self.button(QWizard.WizardButton.Back).setEnabled(True)
    
    def validateCurrentPage(self):
        if self.currentId() == 1:  # WSL2 检查页
            if not self.wsl.check_wsl_installed() or not self.wsl.check_distro_installed():
                QMessageBox.warning(self, "环境未就绪", 
                    "请先安装 WSL2 和 Ubuntu 发行版")
                return False
        return True
