"""
模型下载器 - 从 ModelScope / HuggingFace 下载 GGUF 模型
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, Callable

from utils.logger import get_logger

logger = get_logger()


class ModelDownloader:
    """模型下载器"""
    
    DEFAULT_REPO = "openbmb/MiniCPM-o-4_5-gguf"
    
    def __init__(self, wsl_manager):
        self.wsl = wsl_manager
    
    def check_model_exists(self, model_dir: str) -> bool:
        """检查模型是否已下载"""
        # 在 WSL 中检查
        rc, stdout, _ = self.wsl.exec_command(
            f"ls {model_dir}/*.gguf 2>/dev/null | head -1",
            timeout=10
        )
        return rc == 0 and stdout.strip()
    
    def download_model(self, model_dir: str, quant: str = "Q4_K_M",
                       progress_callback: Callable[[str, int], None] = None) -> bool:
        """
        下载模型
        
        Args:
            model_dir: 模型保存目录（WSL 路径）
            quant: 量化级别
            progress_callback: 进度回调函数 (message, percent)
            
        Returns:
            是否成功
        """
        try:
            if progress_callback:
                progress_callback("准备下载环境...", 5)
            
            # 确保 modelscope 已安装
            rc, _, _ = self.wsl.exec_command(
                "python -c 'import modelscope'",
                timeout=10
            )
            if rc != 0:
                if progress_callback:
                    progress_callback("安装 modelscope...", 10)
                self.wsl.exec_command(
                    "pip install modelscope -q",
                    timeout=120
                )
            
            if progress_callback:
                progress_callback("开始下载模型...", 15)
            
            # 创建下载脚本
            download_script = f'''
import sys
import os
from modelscope import snapshot_download

repo_id = "{self.DEFAULT_REPO}"
local_dir = "{model_dir}"
llm_quant = "{quant}"

allow_patterns = [
    f"MiniCPM-o-4_5-{{llm_quant}}.gguf",
    "vision/*",
    "audio/*",
    "tts/*",
    "token2wav*/*",
    "*.md",
]

print(f"Downloading from {{repo_id}} to {{local_dir}}")
print(f"Patterns: {{allow_patterns}}")

snapshot_download(
    model_id=repo_id,
    local_dir=local_dir,
    allow_patterns=allow_patterns,
    local_dir_use_symlinks=False,
)
print("Download complete!")
'''
            
            # 写入临时脚本
            tmp_script = "/tmp/minicpmo_download.py"
            self.wsl.exec_command(
                f'cat > {tmp_script} << \'EOF\'\n{download_script}\nEOF',
                timeout=10
            )
            
            if progress_callback:
                progress_callback("下载中（这可能需要较长时间）...", 20)
            
            # 执行下载
            rc, stdout, stderr = self.wsl.exec_command(
                f"python {tmp_script}",
                timeout=3600  # 1小时超时
            )
            
            # 清理临时脚本
            self.wsl.exec_command(f"rm -f {tmp_script}", timeout=5)
            
            if rc != 0:
                logger.error(f"模型下载失败: {stderr}")
                if progress_callback:
                    progress_callback(f"下载失败: {stderr}", 0)
                return False
            
            if progress_callback:
                progress_callback("模型下载完成", 100)
            
            logger.info("模型下载完成")
            return True
            
        except Exception as e:
            logger.error(f"模型下载异常: {e}")
            if progress_callback:
                progress_callback(f"异常: {e}", 0)
            return False
    
    def get_model_size(self, quant: str) -> str:
        """获取模型大概大小"""
        sizes = {
            "Q4_0": "~4.7 GB",
            "Q4_K_M": "~5.0 GB",
            "Q4_K_S": "~4.8 GB",
            "Q5_K_M": "~5.8 GB",
            "Q8_0": "~8.7 GB",
            "F16": "~16 GB",
        }
        return sizes.get(quant, "未知")
