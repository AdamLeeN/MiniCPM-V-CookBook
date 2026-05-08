#!/usr/bin/env python3
"""
语音聊天测试 - 使用真实 test.mp3 音频文件
"""

import asyncio
import json
import base64
import time
import sys
import requests
import numpy as np
import wave
import subprocess

from livekit import rtc

BACKEND_URL = "http://127.0.0.1:8021"
INFERENCE_URL = "http://127.0.0.1:9060"
LIVEKIT_URL = "wss://test-ummgc1t8.livekit.cloud"
MP3_FILE = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/test.mp3"


def login():
    print("=== 登录 ===")
    resp = requests.post(
        f"{BACKEND_URL}/api/login",
        json={"modelType": "duplex", "sessionType": "audio", "serviceName": "o45-cpp"},
        timeout=10
    )
    data = resp.json()
    print(f"  UserID: {data.get('userId')}")
    return data


def convert_mp3_to_pcm(mp3_path, sample_rate=48000, channels=1):
    """使用 ffmpeg 将 MP3 转换为 48kHz 单声道 PCM"""
    print(f"\n=== 转换音频: {mp3_path} ===")
    
    # 先获取 MP3 信息
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
         "-of", "default=noprint_wrappers=1:nokey=1", mp3_path],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    print(f"  MP3 时长: {duration:.2f} 秒")
    
    # 转换为 PCM
    pcm_path = mp3_path.replace(".mp3", "_48k_mono.pcm")
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ar", str(sample_rate), "-ac", str(channels),
        "-f", "s16le", pcm_path
    ], capture_output=True)
    
    # 读取 PCM 数据
    with open(pcm_path, "rb") as f:
        pcm_data = f.read()
    
    print(f"  PCM 数据大小: {len(pcm_data)} bytes")
    print(f"  PCM 时长: {len(pcm_data) / (sample_rate * channels * 2):.2f} 秒")
    
    # 验证音频数据
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    print(f"  音频统计: min={audio_array.min()}, max={audio_array.max()}, mean={audio_array.mean():.1f}")
    
    return pcm_data, sample_rate, channels


async def test_with_real_audio(room_name: str, token: str):
    print("\n=== 连接 LiveKit ===")
    
    room = rtc.Room()
    received_audio = bytearray()
    audio_task = None
    
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        print(f"  订阅到轨道: {track.kind} from {participant.identity}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("  🎵 收到音频轨道，开始录制...")
            
            async def record_audio():
                audio_stream = rtc.AudioStream(track)
                frame_count = 0
                async for frame_event in audio_stream:
                    frame = frame_event.frame
                    data = frame.data.tobytes()
                    received_audio.extend(data)
                    frame_count += 1
                    if frame_count % 100 == 0:
                        print(f"    已录制 {len(received_audio) / (48000 * 2):.2f} 秒音频 ({frame_count} 帧)")
                print(f"  音频录制结束，共 {frame_count} 帧")
            
            nonlocal audio_task
            audio_task = asyncio.create_task(record_audio())
    
    @room.on("data_received")
    def on_data_received(data):
        try:
            text = data.data.decode('utf-8', errors='ignore')
            if '<state>' not in text:
                print(f"  📨 收到文本: {text[:100]}")
            else:
                print(f"  📨 收到状态: {text[:50]}")
        except:
            pass
    
    await room.connect(LIVEKIT_URL, token)
    print(f"  已连接到房间: {room.name}")
    
    # 等待后端加入
    print("\n  等待后端加入...")
    for i in range(15):
        await asyncio.sleep(1)
        if room.remote_participants:
            print(f"    后端已加入")
            break
    
    # 发送 init 指令
    print("\n=== 发送 init 指令 ===")
    init_msg = json.dumps({"interface": "init"})
    await room.local_participant.publish_data(
        init_msg.encode('utf-8'), reliable=True, topic="lk.chat"
    )
    print("  已发送 init")
    
    await asyncio.sleep(2)
    
    # 发布音频轨道
    print("\n=== 发布音频并发送真实语音 ===")
    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("test-mic", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await room.local_participant.publish_track(track, options)
    
    # 转换并发送 MP3 音频
    pcm_data, sample_rate, channels = convert_mp3_to_pcm(MP3_FILE, 48000, 1)
    
    # 分帧发送（每帧 10ms = 480 samples * 2 bytes = 960 bytes）
    frame_size = 960
    total_frames = len(pcm_data) // frame_size
    print(f"\n  发送音频（{total_frames} 帧）...")
    
    for i in range(total_frames):
        chunk = pcm_data[i*frame_size:(i+1)*frame_size]
        frame = rtc.AudioFrame(data=chunk, sample_rate=48000, num_channels=1, samples_per_channel=480)
        await source.capture_frame(frame)
        await asyncio.sleep(0.01)
        
        if (i + 1) % 100 == 0:
            print(f"    已发送 {i+1}/{total_frames} 帧 ({(i+1)*10}ms)")
    
    print("  ✅ 音频发送完成")
    
    # 等待回复
    print("\n=== 等待回复（20秒）===")
    for i in range(20):
        await asyncio.sleep(1)
        print(f"    第 {i+1} 秒，已录制 {len(received_audio) / (48000 * 2):.2f} 秒音频")
    
    # 取消音频录制任务
    if audio_task and not audio_task.done():
        audio_task.cancel()
        try:
            await audio_task
        except asyncio.CancelledError:
            pass
    
    # 保存音频到文件
    if received_audio:
        filename = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio_real.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(bytes(received_audio))
        print(f"\n  ✅ 音频已保存到: {filename}")
        print(f"  总时长: {len(received_audio) / (48000 * 2):.2f} 秒")
        
        # 检查音频质量
        audio_array = np.frombuffer(bytes(received_audio), dtype=np.int16)
        print(f"  音频质量: min={audio_array.min()}, max={audio_array.max()}, std={audio_array.std():.1f}")
    else:
        print("\n  ❌ 没有收到音频数据")
    
    await room.disconnect()


async def main():
    print("=" * 60)
    print("语音聊天测试 - 使用真实音频")
    print("=" * 60)
    
    login_data = login()
    await test_with_real_audio(login_data["sessionId"], login_data["token"])
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
