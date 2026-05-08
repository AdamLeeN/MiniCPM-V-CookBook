"""
状态面板 - 显示4个服务的状态
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from core.process_monitor import ProcessMonitor, ServiceStatus


class ServiceCard(QFrame):
    """单个服务状态卡片"""
    
    clicked = pyqtSignal(str)
    
    STATUS_COLORS = {
        ServiceStatus.RUNNING: "#4CAF50",   # 绿色
        ServiceStatus.STARTING: "#FFC107",  # 黄色
        ServiceStatus.STOPPED: "#9E9E9E",   # 灰色
        ServiceStatus.ERROR: "#F44336",     # 红色
        ServiceStatus.UNKNOWN: "#9E9E9E",   # 灰色
    }
    
    STATUS_TEXTS = {
        ServiceStatus.RUNNING: "运行中",
        ServiceStatus.STARTING: "启动中",
        ServiceStatus.STOPPED: "已停止",
        ServiceStatus.ERROR: "错误",
        ServiceStatus.UNKNOWN: "未知",
    }
    
    def __init__(self, name: str, display_name: str, port: int, parent=None):
        super().__init__(parent)
        self.service_name = name
        self.display_name = display_name
        self.port = port
        self._init_ui()
    
    def _init_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            ServiceCard {
                background-color: #f5f5f5;
                border-radius: 8px;
                padding: 10px;
                min-width: 180px;
                min-height: 100px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 服务名称
        self.name_label = QLabel(self.display_name)
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(self.name_label)
        
        # 状态指示器
        status_layout = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {self.STATUS_COLORS[ServiceStatus.STOPPED]}; font-size: 20px;")
        status_layout.addWidget(self.status_dot)
        
        self.status_label = QLabel(self.STATUS_TEXTS[ServiceStatus.STOPPED])
        self.status_label.setStyleSheet("font-size: 14px; color: #666;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 端口信息
        self.port_label = QLabel(f"端口: {self.port}")
        self.port_label.setStyleSheet("font-size: 12px; color: #999;")
        layout.addWidget(self.port_label)
        
        # PID
        self.pid_label = QLabel("PID: --")
        self.pid_label.setStyleSheet("font-size: 12px; color: #999;")
        layout.addWidget(self.pid_label)
        
        layout.addStretch()
    
    def update_status(self, status: ServiceStatus, pid: int = None):
        """更新服务状态显示"""
        color = self.STATUS_COLORS.get(status, "#9E9E9E")
        text = self.STATUS_TEXTS.get(status, "未知")
        
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 20px;")
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: 14px; color: {color};")
        
        if pid:
            self.pid_label.setText(f"PID: {pid}")
        else:
            self.pid_label.setText("PID: --")
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.service_name)


class StatusPanel(QWidget):
    """服务状态面板"""
    
    service_clicked = pyqtSignal(str)
    
    def __init__(self, monitor: ProcessMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.cards = {}
        self._init_ui()
        
        # 定时刷新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(2000)  # 每2秒刷新
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("服务状态")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        # 服务卡片网格
        grid = QGridLayout()
        grid.setSpacing(15)
        
        services = [
            ("livekit", "LiveKit Server", 7880),
            ("backend", "Backend (FastAPI)", 8021),
            ("cpp_inference", "C++ Inference", 9060),
            ("frontend", "Frontend (Vue)", 8088),
        ]
        
        for i, (name, display, port) in enumerate(services):
            card = ServiceCard(name, display, port)
            card.clicked.connect(self._on_card_clicked)
            self.cards[name] = card
            grid.addWidget(card, i // 2, i % 2)
        
        layout.addLayout(grid)
        layout.addStretch()
    
    def _on_card_clicked(self, name: str):
        self.service_clicked.emit(name)
    
    def refresh_status(self):
        """刷新所有服务状态"""
        self.monitor.refresh_all()
        services = self.monitor.get_all_services()
        
        for name, info in services.items():
            if name in self.cards:
                self.cards[name].update_status(info.status, info.pid)
    
    def start_refresh(self):
        """开始定时刷新"""
        self.timer.start()
    
    def stop_refresh(self):
        """停止定时刷新"""
        self.timer.stop()
