#!/usr/bin/env python3
import urllib.request
import json
import time

def test(name, url, method="GET", data=None):
    start = time.time()
    try:
        req = urllib.request.Request(url, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(data).encode()
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            elapsed = (time.time() - start) * 1000
            return resp.status, body[:200], elapsed
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        elapsed = (time.time() - start) * 1000
        return e.code, body[:200], elapsed
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return -1, str(e)[:100], elapsed

print("=" * 60)
print("API 快速测试")
print("=" * 60)

# 1. 健康检查
s, b, t = test("/health", "http://127.0.0.1:8021/health")
print(f"\n[1/5] /health           → HTTP {s} | {t:.1f}ms | {b[:80]}")

# 2. 推理服务列表
s, b, t = test("/services", "http://127.0.0.1:8021/api/inference/services")
print(f"[2/5] /services         → HTTP {s} | {t:.1f}ms | {b[:80]}")

# 3. 登录
s, b, t = test("/login", "http://127.0.0.1:8021/api/login", "POST", {
    "uid": "test-user-001",
    "language": "zh",
    "use_video": False,
    "local_test": True,
    "bot_id": -1
})
print(f"[3/5] /login            → HTTP {s} | {t:.1f}ms")
if s == 200:
    try:
        data = json.loads(b)
        token = data.get("token", "")[:30] + "..."
        print(f"       token: {token}")
        print(f"       sessionId: {data.get('sessionId', 'N/A')}")
    except:
        print(f"       body: {b[:100]}")
else:
    print(f"       error: {b[:100]}")

# 4. C++ 健康
s, b, t = test("cpp /health", "http://127.0.0.1:9060/health")
print(f"[4/5] C++ /health       → HTTP {s} | {t:.1f}ms | {b[:80]}")

# 5. LiveKit HTTP
s, b, t = test("livekit /", "http://127.0.0.1:7880")
print(f"[5/5] LiveKit /         → HTTP {s} | {t:.1f}ms | {b[:80]}")

print("=" * 60)
