import requests
import json
import base64

# 1. 检查推理服务
print("=== 1. 检查推理服务 ===")
resp = requests.get("http://127.0.0.1:8021/api/inference/services")
print(resp.json())

# 2. 登录获取 token
print("\n=== 2. 登录 ===")
resp = requests.post(
    "http://127.0.0.1:8021/api/login",
    json={"modelType": "simplex", "sessionType": "audio", "serviceName": "o45-cpp"}
)
data = resp.json()
print("Response:", json.dumps({k: v for k, v in data.items() if k != "token"}, indent=2))

# 解码 token
if data.get("token"):
    parts = data["token"].split(".")
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    print("\nToken payload:")
    print(json.dumps(payload, indent=2))
    print("\nISS:", payload.get("iss"))
