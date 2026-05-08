#!/usr/bin/env python3
import urllib.request
import json

BASE = "http://127.0.0.1:8021"

def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

# 1. 注册
s, r = post(f"{BASE}/api/inference/register", {
    "ip": "127.0.0.1", "port": 9060, "model_port": 9060,
    "model_type": "simplex", "session_type": "release", "service_name": "o45-cpp"
})
print(f"[1/3] register: HTTP {s}")
print(f"       {r}")

# 2. 查询
req = urllib.request.Request(f"{BASE}/api/inference/services")
with urllib.request.urlopen(req, timeout=10) as resp:
    r = json.loads(resp.read().decode())
    print(f"[2/3] services: {r}")

# 3. 登录
s, r = post(f"{BASE}/api/login", {
    "uid": "test-win-002", "language": "zh", "use_video": False,
    "local_test": True, "bot_id": -1
})
print(f"[3/3] login: HTTP {s}")
if s == 200:
    print(f"       token: {r.get('token','N/A')[:40]}...")
    print(f"       sessionId: {r.get('sessionId','N/A')}")
else:
    print(f"       error: {r}")
