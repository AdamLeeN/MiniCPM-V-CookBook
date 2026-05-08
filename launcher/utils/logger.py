"""
统一日志系统 - 输出到文件和UI信号
"""
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal


class LogEmitter(QObject):
    """用于跨线程发送日志信号到UI"""
    log_signal = pyqtSignal(str, str)  # (level, message)


class UILogHandler(logging.Handler):
    """将日志输出到UI的Handler"""
    def __init__(self, emitter: LogEmitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record):
        msg = self.format(record)
        self.emitter.log_signal.emit(record.levelname, msg)


def setup_logger(name: str = "launcher", log_dir: str = None) -> logging.Logger:
    """
    设置统一日志系统
    
    Args:
        name: 日志器名称
        log_dir: 日志目录，默认 user_data/logs
        
    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 日志格式
    fmt = '[%(asctime)s] [%(levelname)s] %(message)s'
    formatter = logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'user_data', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'launcher_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "launcher") -> logging.Logger:
    """获取已配置的日志器"""
    return logging.getLogger(name)
