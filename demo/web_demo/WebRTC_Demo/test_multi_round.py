#!/usr/bin/env python3
"""
单工模式多轮对话测试 - 支持连续多轮语音交互
关键修复：每轮结束后发送 <state><play_end> 信号，让后端重置 play_end_event
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
        print(f"  音频统计: min={audio.min()}, max={audio.max()}, std={audio.std():.1f}")
        
        return pcm_data, sample_rate, channels


async def send_audio_round(room, source, pcm_data, round_num):
    """发送一轮音频"""
    print(f"\n=== 第 {round_num} 轮: 发送音频 ===")
    
    frame_size = 960
    total_frames = len(pcm_data) // frame_size
    print(f"  发送音频（{total_frames} 帧）...")
    
    for i in range(total_frames):
        chunk = pcm_data[i*frame_size:(i+1)*frame_size]
        frame = rtc.AudioFrame(data=chunk, sample_rate=48000, num_channels=1, samples_per_channel=480)
        await source.capture_frame(frame)
        await asyncio.sleep(0.01)
        
        if (i + 1) % 100 == 0:
            print(f"    已发送 {i+1}/{total_frames} 帧 ({(i+1)*10}ms)")
    
    print(f"  第 {round_num} 轮音频发送完成")


async def wait_for_reply(room, received_audio, max_wait=50, round_num=1):
    """等待回复音频，支持检测回复结束"""
    print(f"\n=== 第 {round_num} 轮: 等待回复（最多{max_wait}秒）===")
    
    last_audio_len = 0
    no_change_count = 0
    generate_end_received = False
    
    for i in range(max_wait):
        await asyncio.sleep(1)
        current_len = len(received_audio)
        print(f"    第 {i+1} 秒，已录制 {current_len / (48000 * 2):.2f} 秒音频")
        
        # 检测音频是否停止增长（说明回复结束了）
        if current_len == last_audio_len and current_len > 0:
            no_change_count += 1
            if no_change_count >= 2:
                print(f"  检测到回复结束（音频停止增长）")
                # 发送 play_end 信号，让后端重置状态
                print(f"  发送 <state><play_end> 信号...")
                await room.local_participant.publish_data(
                    "<state><play_end>".encode('utf-8'), reliable=True, topic="lk.chat"
                )
                await asyncio.sleep(1)  # 等待后端处理
                return True
        else:
            no_change_count = 0
            last_audio_len = current_len
    
    print(f"  等待超时，发送 play_end 信号...")
    await room.local_participant.publish_data(
        "<state><play_end>".encode('utf-8'), reliable=True, topic="lk.chat"
    )
    await asyncio.sleep(1)
    return False


async def test_simplex_multi_round(room_name: str, token: str, rounds=3):
    print("\n=== 连接 LiveKit ===")
    
    room = rtc.Room()
    received_audio = bytearray()
    audio_task = None
    is_recording = False
    
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        print(f"  订阅到轨道: {track.kind} from {participant.identity}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("  收到音频轨道，开始录制...")
            
            async def record_audio():
                nonlocal is_recording
                is_recording = True
                audio_stream = rtc.AudioStream(track)
                frame_count = 0
                async for frame_event in audio_stream:
                    frame = frame_event.frame
                    data = frame.data.tobytes()
                    received_audio.extend(data)
                    frame_count += 1
                    if frame_count % 100 == 0:
                        print(f"    已录制 {len(received_audio) / (48000 * 2):.2f} 秒音频 ({frame_count} 帧)")
                is_recording = False
                print(f"  音频录制结束，共 {frame_count} 帧")
            
            nonlocal audio_task
            audio_task = asyncio.create_task(record_audio())
    
    @room.on("data_received")
    def on_data_received(data):
        try:
            text = data.data.decode('utf-8', errors='ignore')
            if '<state>' not in text:
                print(f"  收到文本: {text[:100]}")
            else:
                print(f"  收到状态: {text[:80]}")
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
    
    # 发布音频轨道（只需发布一次）
    print("\n=== 发布音频轨道 ===")
    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("test-mic", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await room.local_participant.publish_track(track, options)
    print("  音频轨道已发布")
    
    # 加载音频数据
    pcm_data, sample_rate, channels = load_wav_file(WAV_FILE)
    
    # 多轮对话
    all_replies = []
    
    for round_num in range(1, rounds + 1):
        print(f"\n{'='*60}")
        print(f"  第 {round_num}/{rounds} 轮对话")
        print(f"{'='*60}")
        
        # 清空上一轮接收到的音频
        received_audio.clear()
        
        # 发送音频
        await send_audio_round(room, source, pcm_data, round_num)
        
        # 等待回复
        await wait_for_reply(room, received_audio, max_wait=50, round_num=round_num)
        
        # 保存本轮回复
        if received_audio:
            filename = f"/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio_round_{round_num}.wav"
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(bytes(received_audio))
            
            audio_array = np.frombuffer(bytes(received_audio), dtype=np.int16)
            duration = len(received_audio) / (48000 * 2)
            all_replies.append({
                'round': round_num,
                'filename': filename,
                'duration': duration,
                'min': audio_array.min(),
                'max': audio_array.max(),
                'std': audio_array.std()
            })
            print(f"\n  第 {round_num} 轮回复已保存: {filename}")
            print(f"  时长: {duration:.2f} 秒, 质量: std={audio_array.std():.1f}")
        else:
            print(f"\n  第 {round_num} 轮没有收到音频数据")
        
        # 轮间等待
        if round_num < rounds:
            print(f"\n  等待 3 秒后开始下一轮...")
            await asyncio.sleep(3)
    
    # 取消音频录制任务
    if audio_task and not audio_task.done():
        audio_task.cancel()
        try:
            await audio_task
        except asyncio.CancelledError:
            pass
    
    # 汇总
    print(f"\n{'='*60}")
    print("  多轮对话测试汇总")
    print(f"{'='*60}")
    for reply in all_replies:
        print(f"  第 {reply['round']} 轮: {reply['duration']:.2f}秒, std={reply['std']:.1f}")
    
    await room.disconnect()
    return all_replies


async def main():
    print("=" * 60)
    print("单工模式多轮对话测试")
    print("=" * 60)
    
    login_data = login()
    results = await test_simplex_multi_round(
        login_data["sessionId"], 
        login_data["token"],
        rounds=3  # 测试3轮
    )
    
    print("\n" + "=" * 60)
    print(f"测试结束，共 {len(results)} 轮成功")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
