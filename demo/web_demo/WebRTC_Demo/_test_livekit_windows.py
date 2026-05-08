#!/usr/bin/env python3
"""
在 Windows 上测试 LiveKit 连接
需要: pip install livekit livekit-api
"""
import asyncio
import sys
import urllib.request
import json

LIVEKIT_URL = "ws://127.0.0.1:7880"
BACKEND_URL = "http://127.0.0.1:8021"

async def test():
    from livekit import rtc

    print("=" * 50)
    print("LiveKit 连接测试 (Windows -> WSL2)")
    print("=" * 50)

    # 1. 获取 token
    print("\n[1/3] 调用 /login 获取 token...")
    req = urllib.request.Request(
        f"{BACKEND_URL}/api/login",
        data=json.dumps({
            "uid": "win-test-001",
            "language": "zh",
            "use_video": False,
            "local_test": True,
            "bot_id": -1
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            token = data.get("token")
            session_id = data.get("sessionId")
            if not token:
                print(f"  ❌ /login 失败: {data}")
                return
            print(f"  ✅ Token 获取成功 (sessionId: {session_id[:20]}...)")
    except Exception as e:
        print(f"  ❌ /login 错误: {e}")
        return

    # 2. 连接 LiveKit
    print(f"\n[2/3] 连接 LiveKit: {LIVEKIT_URL}")
    room = rtc.Room()

    connected_event = asyncio.Event()
    disconnected_event = asyncio.Event()
    error_msg = None

    @room.on("connected")
    def on_connected():
        print(f"  ✅ Room 连接成功: {room.name}")
        connected_event.set()

    @room.on("disconnected")
    def on_disconnected():
        print(f"  ❌ Room 断开")
        disconnected_event.set()

    @room.on("connection_quality_changed")
    def on_quality_changed(quality, participant, *_):
        print(f"  📊 连接质量: {quality}")

    # 强制使用 TCP，避免 UDP 问题
    try:
        await room.connect(LIVEKIT_URL, token, rtc.RoomOptions(
            rtc_engine_options=rtc.RTCEngineOptions(
                # 可以在这里加更多选项
            )
        ))
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return

    # 等待连接事件
    try:
        await asyncio.wait_for(connected_event.wait(), timeout=10)
    except asyncio.TimeoutError:
        print("  ⏱️ 连接超时 (10s)")
        await room.disconnect()
        return

    # 3. 发布测试音频
    print(f"\n[3/3] 发布音频轨道...")
    try:
        source = rtc.AudioSource(48000, 1)
        track = rtc.LocalAudioTrack.create_audio_track("test-mic", source)
        await room.local_participant.publish_track(track)
        print("  ✅ 音频轨道已发布")
    except Exception as e:
        print(f"  ❌ 发布失败: {e}")
        await room.disconnect()
        return

    # 等待 5 秒观察连接状态
    print(f"\n  等待 5 秒观察连接稳定性...")
    try:
        await asyncio.wait_for(disconnected_event.wait(), timeout=5)
        print("  ❌ 连接在 5 秒内断开")
    except asyncio.TimeoutError:
        print("  ✅ 连接稳定 (5s 内未断开)")

    await room.disconnect()
    print("\n  测试结束")

if __name__ == "__main__":
    try:
        asyncio.run(test())
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请运行: pip install livekit livekit-api")
        sys.exit(1)
