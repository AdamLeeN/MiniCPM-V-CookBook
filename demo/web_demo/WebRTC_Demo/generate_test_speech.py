#!/usr/bin/env python3
"""
生成模拟语音测试文件 - 使用更复杂的音频特征模拟人声
"""

import numpy as np
import wave
import struct

# 生成 5 秒的模拟语音（更接近真实人声特征）
sample_rate = 48000
duration = 5.0
t = np.linspace(0, duration, int(sample_rate * duration), False)

# 模拟人声特征：
# 1. 基频变化（模拟语调）
# 2. 共振峰（模拟元音）
# 3. 噪声（模拟辅音/呼吸）
# 4. 振幅包络（模拟音节）

audio = np.zeros_like(t)

# 基频：模拟中文 "你好" 的语调
# "你" - 低平调，约 150Hz
# "好" - 上升调，从 150Hz 到 200Hz
base_freq = np.piecewise(t, 
    [t < 2.0, (t >= 2.0) & (t < 2.5), t >= 2.5],
    [150, lambda t: 150 + (t - 2.0) * 100, 250]
)

# 生成基频和谐波（模拟声带振动）
for harmonic in range(1, 8):
    freq = base_freq * harmonic
    # 添加轻微频率抖动（模拟自然语音）
    jitter = np.random.normal(0, 0.01, len(t))
    phase = np.cumsum(2 * np.pi * freq * (1 + jitter) / sample_rate)
    amplitude = 0.5 / harmonic  # 谐波衰减
    audio += amplitude * np.sin(phase)

# 添加共振峰（模拟口腔共鸣）
formants = [(500, 0.3), (1500, 0.2), (2500, 0.1)]
for freq, amp in formants:
    phase = np.cumsum(2 * np.pi * freq / sample_rate)
    audio += amp * np.sin(phase)

# 添加噪声（模拟辅音和呼吸）
noise = np.random.normal(0, 0.05, len(t))
# 噪声包络：在音节开头添加更多噪声（模拟辅音）
noise_envelope = np.ones_like(t)
for i in range(0, len(t), int(sample_rate * 0.3)):
    # 每个音节开头 50ms 添加更多噪声
    end = min(i + int(sample_rate * 0.05), len(t))
    noise_envelope[i:end] = 2.0
noise *= noise_envelope
audio += noise

# 振幅包络（模拟音节结构）
envelope = np.ones_like(t)
syllable_duration = 0.3  # 每个音节 300ms
for i in range(0, len(t), int(sample_rate * syllable_duration)):
    # 音节内：快速上升到最大，然后缓慢衰减
    syllable_len = min(int(sample_rate * syllable_duration), len(t) - i)
    x = np.linspace(0, 1, syllable_len)
    # 攻击段（快速上升）
    attack = np.minimum(x * 5, 1.0)
    # 衰减段（缓慢下降）
    decay = np.exp(-x * 2)
    syllable_env = attack * decay
    envelope[i:i+syllable_len] = syllable_env

audio *= envelope

# 限制幅度
audio = np.clip(audio, -0.9, 0.9)

# 转换为 16-bit PCM
audio_int16 = (audio * 32767).astype(np.int16)

# 保存为 WAV 文件
output_file = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/test_speech.wav"
with wave.open(output_file, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(audio_int16.tobytes())

print(f"生成测试语音: {output_file}")
print(f"时长: {duration} 秒")
print(f"采样率: {sample_rate} Hz")
print(f"最小值: {audio_int16.min()}")
print(f"最大值: {audio_int16.max()}")
print(f"标准差: {audio_int16.std():.1f}")
