#!/usr/bin/env python3
import urllib.request
import json

req = urllib.request.Request(
    "http://127.0.0.1:8021/api/login",
    data=json.dumps({
        "uid": "test-user-003",
        "language": "zh",
        "use_video": False,
        "local_test": True,
        "bot_id": -1
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, timeout=10) as resp:
    body = json.loads(resp.read().decode())
    print("=== /login 完整响应 ===")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    print("")
    print("=== 关键字段检查 ===")
    for key in ["token", "livekitServer", "userId", "sessionId", "success"]:
        val = body.get(key, "<缺失>")
        if key == "token" and val != "<缺失>":
            val = val[:40] + "..."
        print(f"  {key}: {val}")
