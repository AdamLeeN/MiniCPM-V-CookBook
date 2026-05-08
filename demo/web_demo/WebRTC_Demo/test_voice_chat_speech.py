#!/usr/bin/env python3
"""
语音聊天测试 - 使用模拟人声测试
"""

import asyncio
import json
import base64
import time
import requests
import numpy as np
import wave

from livekit import rtc

BACKEND_URL = "http://127.0.0.1:8021"
LIVEKIT_URL = "wss://test-ummgc1t8.livekit.cloud"
WAV_FILE = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/test_speech.wav"


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


def load_wav_file(filepath):
    """加载 WAV 文件并返回 PCM 数据"""
    print(f"\n=== 加载音频: {filepath} ===")
    with wave.open(filepath, 'rb') as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        
        print(f"  通道: {channels}")
        print(f"  采样宽度: {sample_width} bytes")
        print(f"  采样率: {sample_rate} Hz")
        print(f"  总帧数: {n_frames}")
        print(f"  时长: {n_frames / sample_rate:.2f} 秒")
        
        pcm_data = wf.readframes(n_frames)
        
        # 转换为 numpy 检查
        audio = np.frombuffer(pcm_data, dtype=np.int16)
        print(f"  音频统计: min={audio.min()}, max={audio.max()}, std={audio.std():.1f}")
        
        return pcm_data, sample_rate, channels


async def test_with_speech(room_name: str, token: str):
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
    print("\n=== 发布音频并发送模拟人声 ===")
    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("test-mic", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await room.local_participant.publish_track(track, options)
    
    # 加载并发送模拟人声
    pcm_data, sample_rate, channels = load_wav_file(WAV_FILE)
    
    # 如果采样率不是 48kHz，需要重采样（这里假设是 48kHz）
    frame_size = 960  # 10ms at 48kHz, 16bit, mono
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
        filename = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio_speech.wav"
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
    print("语音聊天测试 - 使用模拟人声")
    print("=" * 60)
    
    login_data = login()
    await test_with_speech(login_data["sessionId"], login_data["token"])
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
