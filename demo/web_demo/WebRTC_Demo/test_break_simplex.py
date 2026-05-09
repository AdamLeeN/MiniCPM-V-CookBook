#!/usr/bin/env python3
"""
打断功能测试 - 基于 test_simplex_full.py
"""

import asyncio
import json
import requests
import numpy as np
import wave
import time

from livekit import rtc

BACKEND_URL = "http://127.0.0.1:8021"
LIVEKIT_URL = "wss://test-ummgc1t8.livekit.cloud"


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


async def test_break(session_id, token):
    print("\n=== 连接 LiveKit ===")
    room = rtc.Room()
    
    received_audio = bytearray()
    frame_count = 0
    audio_task = None
    generate_start_time = None
    generate_end_time = None
    break_sent_time = None
    
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("  收到音频轨道，开始录制...")
            
            async def record_audio():
                nonlocal frame_count
                audio_stream = rtc.AudioStream(track)
                async for frame_event in audio_stream:
                    frame = frame_event.frame
                    received_audio.extend(frame.data)
                    # 只统计非静音帧
                    import numpy as np
                    audio_data = np.frombuffer(frame.data, dtype=np.int16)
                    if np.abs(audio_data).max() > 100:
                        frame_count += 1
            
            nonlocal audio_task
            audio_task = asyncio.create_task(record_audio())
    
    @room.on("data_received")
    def on_data_received(data):
        try:
            text = data.data.decode('utf-8', errors='ignore')
            nonlocal generate_start_time, generate_end_time
            if text == "<state><generate_start>":
                generate_start_time = time.time()
                print(f"  [状态] generate_start")
            elif text == "<state><generate_end>":
                generate_end_time = time.time()
                print(f"  [状态] generate_end")
            elif text == "<state><session_break>":
                print(f"  [状态] session_break")
            elif '<state>' not in text:
                print(f"  [文本] {text[:60]}")
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
    
    # 等待开场白
    print("\n=== 等待开场白 ===")
    for i in range(30):
        await asyncio.sleep(0.5)
        if generate_start_time:
            print(f"    开场白开始！")
            break
        if i % 2 == 0:
            print(f"    等待... {i//2+1}s")
    
    if not generate_start_time:
        print("  开场白未开始")
        await room.disconnect()
        return
    
    # 等待播放 3 秒
    print("\n=== 等待播放 3 秒 ===")
    await asyncio.sleep(3)
    frames_before_break = frame_count
    print(f"  打断前音频帧数: {frames_before_break}")
    
    # 发送打断指令
    print("\n=== 发送打断指令 ===")
    break_msg = json.dumps({"interface": "break"})
    break_sent_time = time.time()
    await room.local_participant.publish_data(
        break_msg.encode('utf-8'), reliable=True, topic="lk.chat"
    )
    print("  已发送 break")
    
    # 等待 2 秒，检查音频是否停止
    print("\n=== 等待 2 秒，检查音频是否停止 ===")
    await asyncio.sleep(2)
    frames_after_break = frame_count
    frames_added = frames_after_break - frames_before_break
    print(f"  打断后音频帧数: {frames_after_break}")
    print(f"  打断后增加帧数: {frames_added}")
    
    if frames_added <= 5:
        print("  音频立即停止！")
    else:
        print(f"  音频仍在播放，增加了 {frames_added} 帧")
    
    # 取消音频录制任务
    if audio_task and not audio_task.done():
        audio_task.cancel()
        try:
            await audio_task
        except asyncio.CancelledError:
            pass
    
    # 保存音频到文件
    if received_audio:
        filename = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio_break.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(bytes(received_audio))
        print(f"\n  音频已保存到: {filename}")
        print(f"  总时长: {len(received_audio) / (48000 * 2):.2f} 秒")
    
    await room.disconnect()


async def main():
    print("=" * 60)
    print("打断功能测试")
    print("=" * 60)
    
    login_data = login()
    await test_break(login_data["sessionId"], login_data["token"])
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
