#!/usr/bin/env python3
"""
语音聊天全流程测试脚本 - 使用 lk.chat topic
"""

import asyncio
import json
import base64
import time
import sys
import requests
import numpy as np

from livekit import rtc

BACKEND_URL = "http://117.72.163.123:3666"
INFERENCE_URL = "http://117.72.163.123:7881"
LIVEKIT_URL = "wss://test-ummgc1t8.livekit.cloud"


def check_inference_health():
    print("=== 1. 检查推理服务 ===")
    try:
        resp = requests.get(f"{INFERENCE_URL}/health", timeout=5)
        print(f"  推理服务状态: {resp.status_code}")
        print(f"  响应: {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"  ❌ 推理服务不可用: {e}")
        return False


def login():
    print("\n=== 2. 登录获取 Token ===")
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/login",
            json={"modelType": "duplex", "sessionType": "audio", "serviceName": "o45-cpp"},
            timeout=10
        )
        data = resp.json()
        if data.get("success"):
            print(f"  ✅ 登录成功")
            print(f"  UserID: {data.get('userId')}")
            print(f"  SessionID: {data.get('sessionId')}")
            token = data.get("token", "")
            parts = token.split(".")
            if len(parts) >= 2:
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
                print(f"  Token ISS: {payload.get('iss')}")
            return data
        else:
            print(f"  ❌ 登录失败: {data}")
            return None
    except Exception as e:
        print(f"  ❌ 登录请求失败: {e}")
        return None


def generate_speech_like_audio(duration_sec=5, sample_rate=48000):
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


async def test_livekit_connection(room_name: str, token: str):
    print("\n=== 3. 连接 LiveKit 房间 ===")
    
    room = rtc.Room()
    reply_received = False
    audio_received = False
    init_received = False
    
    @room.on("connection_state_changed")
    def on_connection_state_changed(state):
        print(f"  连接状态: {state}")
    
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        print(f"  ✅ 订阅到轨道: {track.kind} from {participant.identity}")
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("  🎵 收到音频轨道！")
            nonlocal audio_received
            audio_received = True
    
    @room.on("data_received")
    def on_data_received(data):
        nonlocal reply_received, init_received
        try:
            msg = json.loads(data.data.decode('utf-8'))
            print(f"  📨 收到数据消息: {msg}")
            reply_received = True
        except:
            text = data.data.decode('utf-8', errors='ignore')
            print(f"  📨 收到文本: {text[:200]}")
            if '<state><model_init_success>' in text:
                init_received = True
                print("  ✅ 收到 model_init_success")
            elif '<state><session_init>' in text:
                print("  ✅ 收到 session_init，音频处理已启动")
            elif '<state>' not in text:
                reply_received = True
    
    @room.on("participant_connected")
    def on_participant_connected(participant):
        print(f"  👤 参与者加入: {participant.identity}")
    
    try:
        await room.connect(LIVEKIT_URL, token)
        print(f"  ✅ 已连接到房间: {room.name}")
        
        # 等待后端加入
        print("\n  等待后端加入...")
        for i in range(15):
            await asyncio.sleep(1)
            participants = list(room.remote_participants.keys())
            if participants:
                print(f"    ✅ 后端已加入: {participants}")
                break
        else:
            print("  ❌ 后端未加入")
            await room.disconnect()
            return
        
        # 等待 model_init_success
        print("\n  等待 model_init_success...")
        for i in range(10):
            await asyncio.sleep(1)
            if init_received:
                break
        
        # 发送 init 指令（使用 lk.chat topic）
        print("\n=== 4. 发送 init 指令 ===")
        init_msg = json.dumps({"interface": "init"})
        
        # 使用 publish_data 并指定 topic
        await room.local_participant.publish_data(
            init_msg.encode('utf-8'),
            reliable=True,
            topic="lk.chat"
        )
        print(f"  ✅ 已发送 init 指令到 lk.chat")
        
        # 等待 session_init
        print("\n  等待 session_init...")
        for i in range(5):
            await asyncio.sleep(1)
        
        # 发布音频轨道
        print("\n=== 5. 发布音频轨道 ===")
        source = rtc.AudioSource(48000, 1)
        track = rtc.LocalAudioTrack.create_audio_track("test-mic", source)
        options = rtc.TrackPublishOptions()
        options.source = rtc.TrackSource.SOURCE_MICROPHONE
        publication = await room.local_participant.publish_track(track, options)
        print(f"  ✅ 音频轨道已发布: {publication.sid}")
        
        # 发送模拟语音
        print("\n=== 6. 发送模拟语音（5秒）===")
        audio_data = generate_speech_like_audio(5, 48000)
        frame_size = 960
        total_frames = len(audio_data) // frame_size
        for i in range(total_frames):
            chunk = audio_data[i*frame_size:(i+1)*frame_size]
            frame = rtc.AudioFrame(data=chunk, sample_rate=48000, num_channels=1, samples_per_channel=480)
            await source.capture_frame(frame)
            await asyncio.sleep(0.01)
            if (i + 1) % 100 == 0:
                print(f"    已发送 {i+1}/{total_frames} 帧")
        
        print("  ✅ 音频发送完成")
        
        # 等待回复
        print("\n=== 7. 等待后端回复（最多 30 秒）===")
        for i in range(30):
            await asyncio.sleep(1)
            status = []
            if audio_received:
                status.append("🎵 收到音频")
            if reply_received:
                status.append("📨 收到文本")
            if status:
                print(f"    第 {i+1} 秒: {', '.join(status)}")
                if reply_received:
                    print("  ✅ 收到回复！")
                    break
            else:
                print(f"    第 {i+1} 秒: 等待中...")
        else:
            print("  ⚠️ 未收到回复（超时）")
        
        await room.disconnect()
        print("\n  ✅ 测试完成")
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("=" * 60)
    print("语音聊天全流程测试")
    print("=" * 60)
    
    if not check_inference_health():
        print("\n❌ 推理服务不健康")
        return
    
    login_data = login()
    if not login_data:
        print("\n❌ 登录失败")
        return
    
    await test_livekit_connection(login_data["sessionId"], login_data["token"])
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
