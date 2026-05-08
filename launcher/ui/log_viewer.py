"""
日志查看器 - 分标签页显示各服务日志
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QTextEdit, QPushButton, QComboBox,
    QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor, QColor

from utils.logger import LogEmitter


class LogTab(QWidget):
    """单个日志标签页"""
    
    def __init__(self, log_file: str, parent=None):
        super().__init__(parent)
        self.log_file = log_file
        self._init_ui()
        
        # 定时读取日志
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._read_log)
        self._file_pos = 0
        
        # 如果文件存在，跳到末尾
        if os.path.exists(log_file):
            self._file_pos = os.path.getsize(log_file)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.auto_scroll = QCheckBox("自动滚动")
        self.auto_scroll.setChecked(True)
        toolbar.addWidget(self.auto_scroll)
        
        toolbar.addStretch()
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self.clear_btn)
        
        layout.addLayout(toolbar)
        
        # 日志文本框
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: none;
                padding: 5px;
            }
        """)
        layout.addWidget(self.text_edit)
    
    def _read_log(self):
        """读取新日志内容"""
        if not os.path.exists(self.log_file):
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self._file_pos)
                new_content = f.read()
                self._file_pos = f.tell()
                
                if new_content:
                    self._append_text(new_content)
        except Exception:
            pass
    
    def _append_text(self, text: str):
        """追加文本并着色"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 根据日志级别着色
        for line in text.split('\n'):
            if not line:
                continue
            
            # 检测日志级别
            color = "#d4d4d4"  # 默认白色
            if "[ERROR]" in line or "error" in line.lower():
                color = "#f48771"  # 红色
            elif "[WARN]" in line or "warn" in line.lower():
                color = "#dcdcaa"  # 黄色
            elif "[OK]" in line or "success" in line.lower():
                color = "#4ec9b0"  # 绿色
            elif "[INFO]" in line:
                color = "#569cd6"  # 蓝色
            
            cursor.insertHtml(f'<span style="color: {color}">{line}</span><br>')
        
        if self.auto_scroll.isChecked():
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()
    
    def _clear(self):
        """清空显示"""
        self.text_edit.clear()
    
    def start_monitoring(self):
        """开始监控日志文件"""
        self.timer.start(500)  # 每500ms读取一次
    
    def stop_monitoring(self):
        """停止监控"""
        self.timer.stop()
    
    def append_launcher_log(self, level: str, message: str):
        """追加启动器日志（来自信号）"""
        color = "#d4d4d4"
        if level == "ERROR":
            color = "#f48771"
        elif level == "WARNING":
            color = "#dcdcaa"
        elif level == "INFO":
            color = "#569cd6"
        
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(f'<span style="color: {color}">[{level}] {message}</span><br>')
        
        if self.auto_scroll.isChecked():
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()


class LogViewer(QWidget):
    """日志查看器主组件"""
    
    def __init__(self, log_dir: str, parent=None):
        super().__init__(parent)
        self.log_dir = log_dir
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 启动器日志（接收信号）
        self.launcher_tab = LogTab("")
        self.tabs.addTab(self.launcher_tab, "🚀 启动器")
        
        # 各服务日志
        self.service_tabs = {}
        services = [
            ("livekit", "📡 LiveKit"),
            ("backend", "⚙️ Backend"),
            ("cpp_inference", "🔥 C++ Inference"),
            ("frontend", "🌐 Frontend"),
        ]
        
        for name, display in services:
            log_file = os.path.join(self.log_dir, f"{name}.log")
            tab = LogTab(log_file)
            self.service_tabs[name] = tab
            self.tabs.addTab(tab, display)
        
        layout.addWidget(self.tabs)
    
    def connect_log_emitter(self, emitter: LogEmitter):
        """连接日志发射器"""
        emitter.log_signal.connect(self._on_log_received)
    
    def _on_log_received(self, level: str, message: str):
        """接收日志信号"""
        self.launcher_tab.append_launcher_log(level, message)
    
    def start_all_monitoring(self):
        """开始监控所有日志"""
        self.launcher_tab.start_monitoring()
        for tab in self.service_tabs.values():
            tab.start_monitoring()
    
    def stop_all_monitoring(self):
        """停止监控所有日志"""
        self.launcher_tab.stop_monitoring()
        for tab in self.service_tabs.values():
            tab.stop_monitoring()
