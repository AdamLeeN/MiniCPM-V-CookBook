#!/usr/bin/env python3
"""
测试单工模式（simplex）
"""

import asyncio
import json
import requests
import numpy as np

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


async def test_simplex(room_name: str, token: str):
    print("\n=== 连接 LiveKit ===")
    
    room = rtc.Room()
    
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        print(f"  订阅到轨道: {track.kind} from {participant.identity}")
    
    @room.on("data_received")
    def on_data_received(data):
        try:
            text = data.data.decode('utf-8', errors='ignore')
            print(f"  📨 收到: {text[:100]}")
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
    
    await asyncio.sleep(5)
    
    await room.disconnect()
    print("\n  测试完成")


async def main():
    print("=" * 60)
    print("单工模式测试")
    print("=" * 60)
    
    login_data = login()
    await test_simplex(login_data["sessionId"], login_data["token"])
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
