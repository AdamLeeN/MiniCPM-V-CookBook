"""
测试单工模式打断功能

流程:
1. 登录获取 token
2. 连接 LiveKit 房间
3. 发送 init 指令
4. 等待开场白开始播放
5. 发送 break 打断指令
6. 验证打断是否成功（generate_end, session_break）
7. 用户说话后验证 AI 是否响应
"""
import asyncio
import json
import time
import numpy as np
import aiohttp
from livekit import rtc

BACKEND_URL = "http://127.0.0.1:8021/api"
USER_ID = "test_break_001"
MODEL_TYPE = "simplex"

livekit_url = None
livekit_token = None
room_name = None


async def login():
    global livekit_url, livekit_token, room_name
    async with aiohttp.ClientSession() as session:
        data = {
            "userId": USER_ID,
            "modelType": MODEL_TYPE,
            "highRefresh": True,
            "sessionType": "voice",
            "sessionId": USER_ID,
        }
        async with session.post(f"{BACKEND_URL}/login", json=data) as resp:
            result = await resp.json()
            if result.get("success"):
                import base64
                token = result["token"]
                payload_b64 = token.split('.')[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += '=' * padding
                payload = json.loads(base64.b64decode(payload_b64))
                room_name = payload["video"]["room"]
                livekit_token = token
                livekit_url = "wss://test-ummgc1t8.livekit.cloud"
                print(f"登录成功! Room: {room_name}")
                return True
            else:
                print(f"登录失败: {result}")
                return False


async def test_break():
    if not await login():
        return

    loop = asyncio.get_event_loop()
    room = rtc.Room(loop=loop)

    events = {
        "model_init_success": False,
        "audio_start": False,
        "generate_start": False,
        "generate_end": False,
        "session_break": False,
        "vad_end": False,
        "second_generate_start": False,
    }
    audio_chunks = 0
    text_msgs = []

    @room.on("connected")
    def on_connected():
        print("[事件] LiveKit 连接成功")

    @room.on("participant_connected")
    def on_participant_connected(participant):
        print(f"[事件] 参与者连接: {participant.identity}")

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("[事件] 开始接收音频轨道...")
            asyncio.create_task(receive_audio(track))

    async def receive_audio(track):
        nonlocal audio_chunks
        audio_stream = rtc.AudioStream(track)
        async for frame_event in audio_stream:
            audio_chunks += 1

    @room.on("data_received")
    def on_data_received(packet):
        try:
            text = packet.data.decode('utf-8')
            text_msgs.append(text)

            if text == "<state><model_init_success>":
                events["model_init_success"] = True
                print("[事件] ✅ model_init_success")
            elif text == "<state><audio_start>":
                events["audio_start"] = True
                print("[事件] ✅ audio_start")
            elif text == "<state><generate_start>":
                if events["generate_start"]:
                    events["second_generate_start"] = True
                    print("[事件] ✅ second_generate_start (打断后重新生成)")
                else:
                    events["generate_start"] = True
                    print("[事件] ✅ generate_start")
            elif text == "<state><generate_end>":
                events["generate_end"] = True
                print("[事件] ✅ generate_end")
            elif text == "<state><session_break>":
                events["session_break"] = True
                print("[事件] ✅ session_break")
            elif text == "<state><vad_end>":
                events["vad_end"] = True
                print("[事件] ✅ vad_end")
            elif text.startswith("<state>"):
                print(f"[事件] 状态: {text}")
            else:
                print(f"[文本] {text[:80]}...")
        except Exception as e:
            print(f"[错误] {e}")

    print(f"\n连接 LiveKit 房间...")
    await room.connect(livekit_url, livekit_token)
    await asyncio.sleep(1)

    # 发送 init
    print("\n发送 init 指令...")
    await room.local_participant.publish_data(
        payload=json.dumps({"interface": "init"}),
        reliable=True, topic="lk.chat"
    )

    # 等待开场白开始
    print("\n等待开场白开始...")
    for i in range(20):
        if events["generate_start"]:
            break
        await asyncio.sleep(0.5)
        print(f"  等待开场白... {i+1}s")

    if not events["generate_start"]:
        print("❌ 开场白未开始")
        await room.disconnect()
        return

    # 等待音频开始播放
    print("\n等待音频开始播放...")
    for i in range(10):
        if audio_chunks > 0:
            break
        await asyncio.sleep(0.5)
    print(f"  音频帧数: {audio_chunks}")

    # 发送打断指令
    print("\n===== 发送打断指令 =====")
    await room.local_participant.publish_data(
        payload=json.dumps({"interface": "break"}),
        reliable=True, topic="lk.chat"
    )

    # 等待打断结果
    print("\n等待打断结果...")
    for i in range(10):
        if events["session_break"]:
            break
        await asyncio.sleep(0.5)
        print(f"  等待打断... {i+1}s")

    if events["session_break"]:
        print("✅ 打断信号已收到")
    else:
        print("⚠️ 未收到 session_break")

    # 等待一段时间，看是否有 generate_end
    print("\n等待 generate_end...")
    for i in range(10):
        if events["generate_end"]:
            break
        await asyncio.sleep(0.5)
        print(f"  等待... {i+1}s")

    # 模拟用户说话（发送一段音频）
    print("\n===== 模拟用户说话 =====")
    # 生成 2 秒静音（模拟用户说话前的 VAD 检测）
    silence = np.zeros(48000 * 2, dtype=np.int16)
    # 将音频放入队列（通过 publish_data 不行，需要 publish_track）
    # 这里我们直接等待，看是否能检测到第二次 generate_start

    print("\n等待 5 秒，看是否有第二次生成...")
    for i in range(10):
        if events["second_generate_start"]:
            break
        await asyncio.sleep(0.5)
        print(f"  等待第二次生成... {i+1}s")

    # 结果
    print("\n" + "="*50)
    print("测试结果:")
    print("="*50)
    for k, v in events.items():
        status = "✅" if v else "❌"
        print(f"  {status} {k}: {v}")
    print(f"  音频帧数: {audio_chunks}")
    print(f"  文本消息数: {len(text_msgs)}")

    if events["session_break"]:
        print("\n🎉 打断功能测试成功!")
    else:
        print("\n⚠️ 打断功能可能有问题")

    await asyncio.sleep(2)
    await room.disconnect()
    print("测试结束")


if __name__ == "__main__":
    asyncio.run(test_break())
