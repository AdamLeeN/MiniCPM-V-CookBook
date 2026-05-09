"""
完整测试打断功能

流程:
1. 登录获取 token
2. 连接 LiveKit 房间并发布音频轨道
3. 发送 init 指令
4. 等待开场白开始播放
5. 发送 break 打断指令
6. 验证音频是否立即停止
"""
import asyncio
import json
import time
import numpy as np
import aiohttp
from livekit import rtc

BACKEND_URL = "http://127.0.0.1:8021/api"
USER_ID = "test_break_full_001"
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
        "generate_start": False,
        "generate_end": False,
        "session_break": False,
    }
    audio_chunks = 0
    last_audio_time = 0
    audio_stopped = False

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
        nonlocal audio_chunks, last_audio_time
        audio_stream = rtc.AudioStream(track)
        async for frame_event in audio_stream:
            audio_chunks += 1
            last_audio_time = time.time()
            if audio_chunks <= 5:
                print(f"[音频帧] size={frame_event.frame.samples_per_channel} samples, rate={frame_event.frame.sample_rate}")

    @room.on("data_received")
    def on_data_received(packet):
        try:
            text = packet.data.decode('utf-8')

            if text == "<state><model_init_success>":
                events["model_init_success"] = True
                print("[事件] ✅ model_init_success")
            elif text == "<state><generate_start>":
                events["generate_start"] = True
                print("[事件] ✅ generate_start")
            elif text == "<state><generate_end>":
                events["generate_end"] = True
                print("[事件] ✅ generate_end")
            elif text == "<state><session_break>":
                events["session_break"] = True
                print("[事件] ✅ session_break")
            elif text.startswith("<state>"):
                pass
            else:
                print(f"[文本] {text[:60]}...")
        except Exception as e:
            pass

    print(f"\n连接 LiveKit 房间...")
    await room.connect(livekit_url, livekit_token)
    await asyncio.sleep(1)

    # 发布音频轨道（模拟麦克风）
    print("发布音频轨道...")
    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("microphone", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await room.local_participant.publish_track(track, options)

    # 发送 init
    print("\n发送 init 指令...")
    await room.local_participant.publish_data(
        payload=json.dumps({"interface": "init"}),
        reliable=True, topic="lk.chat"
    )

    # 等待开场白开始
    print("\n等待开场白开始...")
    for i in range(30):
        if events["generate_start"]:
            break
        await asyncio.sleep(0.5)
        print(f"  等待... {i+1}s")

    if not events["generate_start"]:
        print("❌ 开场白未开始")
        await room.disconnect()
        return

    # 等待音频开始播放
    print("\n等待音频开始播放...")
    for i in range(10):
        if audio_chunks > 0:
            break
        await asyncio.sleep(0.2)
    print(f"  音频帧数: {audio_chunks}")

    # 等待播放一段时间
    print("\n等待播放 3 秒...")
    await asyncio.sleep(3)
    print(f"  音频帧数: {audio_chunks}")

    # 记录打断前的音频帧数
    audio_before_break = audio_chunks
    print(f"\n===== 发送打断指令 =====")
    print(f"打断前音频帧数: {audio_before_break}")

    await room.local_participant.publish_data(
        payload=json.dumps({"interface": "break"}),
        reliable=True, topic="lk.chat"
    )

    # 等待打断结果
    print("\n等待打断结果...")
    for i in range(10):
        if events["session_break"]:
            break
        await asyncio.sleep(0.2)
        print(f"  等待... {i+1}s")

    # 等待一段时间，检查音频是否停止
    print("\n等待 2 秒，检查音频是否停止...")
    await asyncio.sleep(2)

    audio_after_break = audio_chunks
    audio_increase = audio_after_break - audio_before_break

    print(f"\n打断后音频帧数: {audio_after_break}")
    print(f"打断后增加帧数: {audio_increase}")

    # 判断打断是否成功
    if audio_increase < 10:  # 增加少于10帧认为成功停止
        audio_stopped = True
        print("✅ 音频已立即停止!")
    else:
        print(f"⚠️ 音频仍在播放，增加了 {audio_increase} 帧")

    # 结果
    print("\n" + "="*50)
    print("测试结果:")
    print("="*50)
    for k, v in events.items():
        status = "✅" if v else "❌"
        print(f"  {status} {k}: {v}")
    print(f"  总音频帧数: {audio_chunks}")
    print(f"  音频立即停止: {'✅' if audio_stopped else '❌'}")

    if events["session_break"] and audio_stopped:
        print("\n🎉 打断功能测试成功!")
    else:
        print("\n⚠️ 打断功能有问题")

    await asyncio.sleep(1)
    await room.disconnect()
    print("测试结束")


if __name__ == "__main__":
    asyncio.run(test_break())
