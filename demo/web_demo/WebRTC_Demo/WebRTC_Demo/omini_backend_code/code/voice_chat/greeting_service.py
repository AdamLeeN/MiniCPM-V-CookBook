"""
🔧 [开场白] 开场白音频生成服务
使用 edge-tts 预先生成开场白音频，保存为PCM格式

使用方式:
1. 服务启动时调用 init_global_greeting() 预生成开场白
2. 每个会话通过 get_global_greeting() 获取预生成的音频数据
"""
import asyncio
import io
import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

import edge_tts
import numpy as np

logger = logging.getLogger(__name__)

# 默认开场白模板
DEFAULT_GREETING_TEMPLATE = "请说：您好，请问是{customer_name}吗？"

# edge-tts 语音配置
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # 女声，自然流畅
DEFAULT_RATE = "+0%"   # 语速
DEFAULT_PITCH = "+0Hz"  # 音调

# 音频输出配置
OUTPUT_SAMPLE_RATE = 48000  # 目标采样率 (WebRTC使用48kHz)
EDGE_TTS_SAMPLE_RATE = 24000  # edge-tts 默认输出24kHz

# 🔧 [开场白] 全局预生成音频缓存
_global_greeting_pcm: Optional[bytes] = None
_global_greeting_sr: int = OUTPUT_SAMPLE_RATE
_global_greeting_text: Optional[str] = None
_global_greeting_initialized: bool = False


class GreetingService:
    """
    开场白音频生成服务
    """
    
    def __init__(
        self,
        customer_name: str = "张三",
        template: Optional[str] = None,
        voice: str = DEFAULT_VOICE,
        rate: str = DEFAULT_RATE,
        pitch: str = DEFAULT_PITCH,
        cache_dir: Optional[str] = None,
    ):
        self.customer_name = customer_name
        self.template = template or DEFAULT_GREETING_TEMPLATE
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        
        # 缓存目录
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / "cache" / "greetings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成的音频数据
        self.pcm_bytes: Optional[bytes] = None
        self.sample_rate: int = OUTPUT_SAMPLE_RATE
        self.text: Optional[str] = None
        
        logger.info(f"[开场白] 服务初始化: customer={customer_name}, voice={voice}")
    
    def _generate_cache_key(self) -> str:
        """生成缓存文件名（基于参数哈希）"""
        import hashlib
        content = f"{self.template}|{self.customer_name}|{self.voice}|{self.rate}|{self.pitch}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _get_cache_path(self) -> Path:
        """获取缓存文件路径"""
        cache_key = self._generate_cache_key()
        return self.cache_dir / f"greeting_{cache_key}.pcm"
    
    def _render_text(self) -> str:
        """渲染开场白文本"""
        text = self.template.format(customer_name=self.customer_name)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()
    
    async def generate_greeting(self, force_regenerate: bool = False) -> Tuple[Optional[bytes], int]:
        """
        生成开场白音频
        
        Returns:
            (pcm_bytes, sample_rate) 或 (None, 0) 如果失败
        """
        cache_path = self._get_cache_path()
        
        # 检查缓存
        if not force_regenerate and cache_path.exists():
            try:
                self.pcm_bytes = cache_path.read_bytes()
                self.text = self._render_text()
                logger.info(f"[开场白] 从缓存加载: {cache_path}, 大小: {len(self.pcm_bytes)} bytes")
                return self.pcm_bytes, self.sample_rate
            except Exception as e:
                logger.warning(f"[开场白] 缓存读取失败: {e}")
        
        # 生成文本
        self.text = self._render_text()
        logger.info(f"[开场白] 生成文本: {self.text}")
        
        try:
            # 使用 edge-tts 生成音频
            communicate = edge_tts.Communicate(
                text=self.text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
            )
            
            # 收集音频数据
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            # 合并音频数据
            mp3_bytes = b"".join(audio_chunks)
            logger.info(f"[开场白] MP3生成完成: {len(mp3_bytes)} bytes")
            
            # 解码MP3为PCM
            pcm_bytes = await self._decode_mp3_to_pcm(mp3_bytes)
            
            if pcm_bytes is None or len(pcm_bytes) == 0:
                logger.error("[开场白] PCM解码失败")
                return None, 0
            
            # 重采样到48kHz
            pcm_48k = await self._resample_to_48k(pcm_bytes)
            
            self.pcm_bytes = pcm_48k
            
            # 保存缓存
            try:
                cache_path.write_bytes(self.pcm_bytes)
                logger.info(f"[开场白] 缓存已保存: {cache_path}")
            except Exception as e:
                logger.warning(f"[开场白] 缓存保存失败: {e}")
            
            logger.info(f"[开场白] 生成完成: {len(self.pcm_bytes)} bytes, {self.sample_rate}Hz")
            return self.pcm_bytes, self.sample_rate
            
        except Exception as e:
            logger.error(f"[开场白] 生成失败: {e}", exc_info=True)
            return None, 0
    
    async def _decode_mp3_to_pcm(self, mp3_bytes: bytes) -> Optional[bytes]:
        """将MP3解码为16-bit PCM (24kHz, mono)"""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            
            # 转换为单声道、16-bit、24kHz
            audio = audio.set_channels(1)
            audio = audio.set_sample_width(2)  # 16-bit = 2 bytes
            audio = audio.set_frame_rate(EDGE_TTS_SAMPLE_RATE)
            
            pcm_bytes = audio.raw_data
            return pcm_bytes
            
        except ImportError:
            logger.error("[开场白] 缺少 pydub，请安装: pip install pydub")
            return None
        except Exception as e:
            logger.error(f"[开场白] MP3解码失败: {e}")
            return None
    
    async def _resample_to_48k(self, pcm_24k: bytes) -> bytes:
        """将24kHz PCM重采样到48kHz"""
        try:
            from scipy.signal import resample_poly
            
            audio_array = np.frombuffer(pcm_24k, dtype=np.int16)
            
            # 2倍上采样 (24k -> 48k)
            resampled = resample_poly(audio_array, 2, 1, padtype='line')
            
            # 裁剪到有效范围
            resampled = np.clip(resampled, -32768, 32767).astype(np.int16)
            
            return resampled.tobytes()
            
        except ImportError:
            logger.warning("[开场白] 缺少 scipy，使用简单插值重采样")
            audio_array = np.frombuffer(pcm_24k, dtype=np.int16)
            resampled = np.repeat(audio_array, 2)
            return resampled.tobytes()
        except Exception as e:
            logger.error(f"[开场白] 重采样失败: {e}")
            return pcm_24k
    
    def get_greeting_data(self) -> Tuple[Optional[bytes], int]:
        """获取已生成的开场白数据"""
        return self.pcm_bytes, self.sample_rate
    
    def get_greeting_text(self) -> Optional[str]:
        """获取开场白文本"""
        return self.text


# ============================================================
# 🔧 [开场白] 全局预生成接口
# ============================================================

async def init_global_greeting(
    customer_name: str = "张三",
    template: Optional[str] = None,
    voice: str = DEFAULT_VOICE,
) -> bool:
    """
    服务启动时预生成开场白音频，存入全局缓存
    
    应该在 main.py 启动时调用一次
    
    Returns:
        True 如果成功，False 如果失败
    """
    global _global_greeting_pcm, _global_greeting_sr, _global_greeting_text, _global_greeting_initialized
    
    if _global_greeting_initialized and _global_greeting_pcm is not None:
        logger.info("[开场白] 全局开场白已预生成，跳过")
        return True
    
    logger.info("[开场白] 开始全局预生成开场白音频...")
    
    service = GreetingService(
        customer_name=customer_name,
        template=template,
        voice=voice,
    )
    
    pcm_bytes, sr = await service.generate_greeting()
    
    if pcm_bytes and len(pcm_bytes) > 0:
        _global_greeting_pcm = pcm_bytes
        _global_greeting_sr = sr
        _global_greeting_text = service.get_greeting_text()
        _global_greeting_initialized = True
        logger.info(f"[开场白] 全局预生成成功: {len(pcm_bytes)} bytes, {sr}Hz")
        logger.info(f"[开场白] 文本: {_global_greeting_text}")
        return True
    else:
        logger.error("[开场白] 全局预生成失败")
        return False


def get_global_greeting() -> Tuple[Optional[bytes], int, Optional[str]]:
    """
    获取全局预生成的开场白音频数据
    
    Returns:
        (pcm_bytes, sample_rate, text) 或 (None, 0, None) 如果未预生成
    """
    return _global_greeting_pcm, _global_greeting_sr, _global_greeting_text


def is_global_greeting_ready() -> bool:
    """检查全局开场白是否已预生成"""
    return _global_greeting_initialized and _global_greeting_pcm is not None


# 便捷函数：快速生成开场白（旧接口，保留兼容）
async def generate_greeting_audio(
    customer_name: str = "张三",
    template: Optional[str] = None,
    voice: str = DEFAULT_VOICE,
) -> Tuple[Optional[bytes], int]:
    """
    快速生成开场白音频
    
    Returns:
        (pcm_bytes, sample_rate) 或 (None, 0)
    """
    service = GreetingService(
        customer_name=customer_name,
        template=template,
        voice=voice,
    )
    return await service.generate_greeting()


# 测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        # 测试全局预生成
        success = await init_global_greeting()
        print(f"全局预生成: {'成功' if success else '失败'}")
        
        pcm, sr, text = get_global_greeting()
        if pcm:
            print(f"获取成功: {len(pcm)} bytes, {sr}Hz")
            print(f"文本: {text}")
        else:
            print("获取失败")
    
    asyncio.run(test())
