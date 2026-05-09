"""
测试开场白功能

流程:
1. 登录获取 token
2. 连接 LiveKit 房间
3. 发送 init 指令
4. 等待 model_init_success
5. 等待开场白音频（模型生成）
6. 发送用户语音测试对话
"""
import asyncio
import json
import time
import numpy as np
import aiohttp
from livekit import rtc

# 配置
BACKEND_URL = "http://127.0.0.1:8021/api"
USER_ID = "test_greeting_001"
MODEL_TYPE = "simplex"  # 单工模式

# LiveKit 配置（从登录响应获取）
livekit_url = None
livekit_token = None
room_name = None


async def login():
    """登录获取 LiveKit token"""
    global livekit_url, livekit_token, room_name
    
    async with aiohttp.ClientSession() as session:
        data = {
            "userId": USER_ID,
            "modelType": MODEL_TYPE,
            "highRefresh": True,
            "sessionType": "voice",
            "sessionId": USER_ID,
        }
        async with session.post(
            f"{BACKEND_URL}/login",
            json=data
        ) as resp:
            result = await resp.json()
            print(f"登录响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("success") == True:
                # 从 JWT token 中解析 room 信息
                import base64
                token = result["token"]
                # JWT payload 是第二部分
                payload_b64 = token.split('.')[1]
                # 添加 padding
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += '=' * padding
                payload = json.loads(base64.b64decode(payload_b64))
                
                room_name = payload["video"]["room"]
                livekit_token = token
                # LiveKit Cloud URL
                livekit_url = "wss://test-ummgc1t8.livekit.cloud"
                
                print(f"\n登录成功!")
                print(f"  LiveKit URL: {livekit_url}")
                print(f"  Room: {room_name}")
                print(f"  SessionId: {result['sessionId']}")
                return True
            else:
                print(f"登录失败: {result}")
                return False


async def test_greeting():
    """测试开场白"""
    
    # 1. 登录
    if not await login():
        return
    
    # 2. 连接 LiveKit
    loop = asyncio.get_event_loop()
    room = rtc.Room(loop=loop)
    
    # 事件跟踪
    events = {
        "connected": False,
        "participant_connected": False,
        "model_init_success": False,
        "audio_start": False,
        "generate_start": False,
        "generate_end": False,
        "vad_end": False,
    }
    
    audio_chunks_received = 0
    text_received = []
    
    @room.on("connected")
    def on_connected():
        events["connected"] = True
        print("[事件] LiveKit 连接成功")
    
    @room.on("disconnected")
    def on_disconnected():
        print("[事件] LiveKit 断开连接")
    
    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        events["participant_connected"] = True
        print(f"[事件] 参与者连接: {participant.identity}")
    
    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        print(f"[事件] 订阅轨道: {track.name} ({track.kind})")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("[事件] 开始接收音频轨道...")
            asyncio.create_task(receive_audio(track))
    
    async def receive_audio(track: rtc.Track):
        """接收音频数据"""
        nonlocal audio_chunks_received
        audio_stream = rtc.AudioStream(track)
        async for frame_event in audio_stream:
            audio_data = frame_event.frame.data.tobytes()
            audio_chunks_received += 1
            if audio_chunks_received % 100 == 0:
                print(f"[音频] 已接收 {audio_chunks_received} 个音频帧")
    
    # 接收文本消息
    @room.on("data_received")
    def on_data_received(packet):
        try:
            text = packet.data.decode('utf-8')
            text_received.append(text)
            
            if text == "<state><model_init_success>":
                events["model_init_success"] = True
                print("[事件] ✅ model_init_success 收到!")
            elif text == "<state><audio_start>":
                events["audio_start"] = True
                print("[事件] ✅ audio_start 收到!")
            elif text == "<state><generate_start>":
                events["generate_start"] = True
                print("[事件] ✅ generate_start 收到!")
            elif text == "<state><generate_end>":
                events["generate_end"] = True
                print("[事件] ✅ generate_end 收到!")
            elif text == "<state><vad_end>":
                events["vad_end"] = True
                print("[事件] ✅ vad_end 收到!")
            elif text.startswith("<state>"):
                print(f"[事件] 状态消息: {text}")
            else:
                print(f"[文本] {text[:100]}...")
        except Exception as e:
            print(f"[错误] 处理数据失败: {e}")
    
    # 连接房间
    print(f"\n连接 LiveKit 房间: {room_name}")
    await room.connect(livekit_url, livekit_token)
    
    # 等待连接
    await asyncio.sleep(1)
    
    # 3. 发送 init 指令
    print("\n发送 init 指令...")
    await room.local_participant.publish_data(
        payload=json.dumps({"interface": "init"}),
        reliable=True,
        topic="lk.chat"
    )
    
    # 4. 等待 model_init_success
    print("\n等待 model_init_success...")
    for i in range(30):  # 最多等30秒
        if events["model_init_success"]:
            break
        await asyncio.sleep(1)
        print(f"  等待中... {i+1}s")
    
    if not events["model_init_success"]:
        print("❌ 超时: 未收到 model_init_success")
        await room.disconnect()
        return
    
    # 5. 等待开场白音频
    print("\n等待开场白音频...")
    for i in range(60):  # 最多等60秒
        if events["generate_end"]:
            break
        if audio_chunks_received > 0 and i > 5:
            print(f"  已接收 {audio_chunks_received} 个音频帧")
        await asyncio.sleep(1)
        if i % 5 == 0:
            print(f"  等待中... {i}s, 音频帧: {audio_chunks_received}")
    
    # 6. 检查结果
    print("\n" + "="*50)
    print("测试结果:")
    print("="*50)
    for key, value in events.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    print(f"  音频帧数: {audio_chunks_received}")
    print(f"  文本消息数: {len(text_received)}")
    
    if events["generate_end"] and audio_chunks_received > 0:
        print("\n🎉 开场白测试成功!")
    else:
        print("\n⚠️ 开场白可能未正常播放")
    
    # 7. 测试用户对话（可选）
    print("\n等待5秒后断开...")
    await asyncio.sleep(5)
    
    await room.disconnect()
    print("测试结束")


if __name__ == "__main__":
    asyncio.run(test_greeting())
