#!/usr/bin/env python3
"""
测试单工模式的打断功能
- 发送音频，等待回复开始
- 在回复过程中发送打断信号
- 验证是否能立即停止并重新开始
"""

import asyncio
import json
import requests
import numpy as np
import wave

from livekit import rtc

BACKEND_URL = "http://127.0.0.1:8021"
LIVEKIT_URL = "wss://test-ummgc1t8.livekit.cloud"
WAV_FILE = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/test_speech.wav"


def login():
    print("=== 登录（单工模式）===")
    resp = requests.post(
        f"{BACKEND_URL}/api/login",
        json={"modelType": "simplex", "sessionType": "audio", "serviceName": "o45-cpp"},
        timeout=10
    )
    data = resp.json()
    print(f"  UserID: {data.get('userId')}")
    return data


def load_wav_file(filepath):
    print(f"\n=== 加载音频: {filepath} ===")
    with wave.open(filepath, 'rb') as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        pcm_data = wf.readframes(n_frames)
        
        audio = np.frombuffer(pcm_data, dtype=np.int16)
        print(f"  通道: {channels}, 采样率: {sample_rate} Hz")
        print(f"  时长: {n_frames / sample_rate:.2f} 秒")
        
        return pcm_data, sample_rate, channels


async def test_interrupt(room_name: str, token: str):
    print("\n=== 连接 LiveKit ===")
    
    room = rtc.Room()
    received_audio = bytearray()
    audio_task = None
    generate_started = False
    
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        print(f"  订阅到轨道: {track.kind} from {participant.identity}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("  收到音频轨道，开始录制...")
            
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
        nonlocal generate_started
        try:
            text = data.data.decode('utf-8', errors='ignore')
            if '<state>' not in text:
                print(f"  收到文本: {text[:80]}")
            else:
                print(f"  收到状态: {text[:80]}")
                if '<generate_start>' in text:
                    generate_started = True
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
    print("\n=== 发布音频轨道 ===")
    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("test-mic", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await room.local_participant.publish_track(track, options)
    print("  音频轨道已发布")
    
    # 加载音频数据
    pcm_data, sample_rate, channels = load_wav_file(WAV_FILE)
    
    # ========== 第一轮：发送音频 ==========
    print(f"\n{'='*60}")
    print("  第一轮：发送音频")
    print(f"{'='*60}")
    
    frame_size = 960
    total_frames = len(pcm_data) // frame_size
    
    for i in range(total_frames):
        chunk = pcm_data[i*frame_size:(i+1)*frame_size]
        frame = rtc.AudioFrame(data=chunk, sample_rate=48000, num_channels=1, samples_per_channel=480)
        await source.capture_frame(frame)
        await asyncio.sleep(0.01)
    
    print("  音频发送完成，等待回复开始...")
    
    # 等待 generate_start
    for i in range(20):
        await asyncio.sleep(0.5)
        if generate_started:
            print(f"  检测到 generate_start！")
            break
    
    if not generate_started:
        print("  未检测到 generate_start，放弃测试")
        return
    
    # 等待回复播放一会儿（5秒）
    print("\n  等待回复播放 5 秒...")
    await asyncio.sleep(5)
    
    audio_len_before = len(received_audio)
    print(f"  打断前已录制: {audio_len_before / (48000 * 2):.2f} 秒")
    
    # ========== 打断：发送新的音频 ==========
    print(f"\n{'='*60}")
    print("  打断：发送新的音频（模拟用户说话打断）")
    print(f"{'='*60}")
    
    # 清空之前接收的音频
    received_audio.clear()
    generate_started = False
    
    # 重新发送音频
    for i in range(total_frames):
        chunk = pcm_data[i*frame_size:(i+1)*frame_size]
        frame = rtc.AudioFrame(data=chunk, sample_rate=48000, num_channels=1, samples_per_channel=480)
        await source.capture_frame(frame)
        await asyncio.sleep(0.01)
    
    print("  新音频发送完成，等待新的回复...")
    
    # 等待新的 generate_start
    for i in range(20):
        await asyncio.sleep(0.5)
        if generate_started:
            print(f"  检测到新的 generate_start！打断成功！")
            break
    
    if not generate_started:
        print("  未检测到新的 generate_start，打断可能失败")
    
    # 等待新回复播放一会儿
    print("\n  等待新回复播放 10 秒...")
    await asyncio.sleep(10)
    
    audio_len_after = len(received_audio)
    print(f"  打断后新录制: {audio_len_after / (48000 * 2):.2f} 秒")
    
    # 保存音频
    if received_audio:
        filename = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio_interrupt.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(bytes(received_audio))
        print(f"\n  音频已保存: {filename}")
    
    # 发送 play_end
    print("\n  发送 play_end 信号...")
    await room.local_participant.publish_data(
        "<state><play_end>".encode('utf-8'), reliable=True, topic="lk.chat"
    )
    await asyncio.sleep(1)
    
    # 取消音频录制任务
    if audio_task and not audio_task.done():
        audio_task.cancel()
        try:
            await audio_task
        except asyncio.CancelledError:
            pass
    
    await room.disconnect()


async def main():
    print("=" * 60)
    print("单工模式打断测试")
    print("=" * 60)
    
    login_data = login()
    await test_interrupt(login_data["sessionId"], login_data["token"])
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
