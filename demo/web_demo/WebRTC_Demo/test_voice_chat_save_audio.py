#!/usr/bin/env python3
"""
语音聊天测试 - 保存接收到的音频到文件
使用 rtc.AudioStream 正确获取音频帧
"""

import asyncio
import json
import base64
import time
import sys
import requests
import numpy as np
import wave

from livekit import rtc

BACKEND_URL = "http://127.0.0.1:8021"
INFERENCE_URL = "http://127.0.0.1:9060"
LIVEKIT_URL = "wss://test-ummgc1t8.livekit.cloud"


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


def generate_speech_like_audio(duration_sec=3, sample_rate=48000):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    audio = np.zeros_like(t)
    freqs = [150, 300, 450, 600, 900, 1200]
    amps = [0.4, 0.3, 0.2, 0.15, 0.1, 0.05]
    for freq, amp in zip(freqs, amps):
        freq_mod = freq * (1 + 0.1 * np.sin(2 * np.pi * 3 * t))
        phase = np.cumsum(2 * np.pi * freq_mod / sample_rate)
        audio += amp * np.sin(phase)
    noise = np.random.normal(0, 0.05, len(t))
    audio += noise
    envelope = np.ones_like(t)
    for i in range(0, len(t), int(sample_rate * 0.2)):
        end = min(i + int(sample_rate * 0.15), len(t))
        envelope[i:end] = 1.0
        end2 = min(i + int(sample_rate * 0.2), len(t))
        envelope[end:end2] = 0.1
    audio *= envelope
    audio = np.clip(audio, -0.9, 0.9)
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16.tobytes()


async def test_with_audio_save(room_name: str, token: str):
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
                # 使用 AudioStream 获取音频帧
                audio_stream = rtc.AudioStream(track)
                frame_count = 0
                async for frame_event in audio_stream:
                    frame = frame_event.frame
                    data = frame.data.tobytes()
                    received_audio.extend(data)
                    frame_count += 1
                    if frame_count % 100 == 0:  # 每约1秒打印一次
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
    print("\n=== 发布音频并发送测试语音 ===")
    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("test-mic", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await room.local_participant.publish_track(track, options)
    
    # 发送 3 秒模拟语音
    audio_data = generate_speech_like_audio(3, 48000)
    frame_size = 960
    for i in range(len(audio_data) // frame_size):
        chunk = audio_data[i*frame_size:(i+1)*frame_size]
        frame = rtc.AudioFrame(data=chunk, sample_rate=48000, num_channels=1, samples_per_channel=480)
        await source.capture_frame(frame)
        await asyncio.sleep(0.01)
    
    print("  音频发送完成")
    
    # 等待 15 秒接收回复
    print("\n=== 等待回复（15秒）===")
    for i in range(15):
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
        filename = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(bytes(received_audio))
        print(f"\n  ✅ 音频已保存到: {filename}")
        print(f"  总时长: {len(received_audio) / (48000 * 2):.2f} 秒")
        print(f"  文件大小: {len(received_audio)} bytes")
    else:
        print("\n  ❌ 没有收到音频数据")
    
    await room.disconnect()


async def main():
    print("=" * 60)
    print("语音聊天测试 - 保存音频")
    print("=" * 60)
    
    login_data = login()
    await test_with_audio_save(login_data["sessionId"], login_data["token"])
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
