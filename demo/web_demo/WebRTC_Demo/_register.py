#!/usr/bin/env python3
import urllib.request
import json

req = urllib.request.Request(
    "http://127.0.0.1:8021/api/inference/register",
    data=json.dumps({
        "ip": "127.0.0.1",
        "port": 9060,
        "model_port": 9060,
        "model_type": "simplex",
        "session_type": "release",
        "service_name": "o45-cpp"
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("Register:", resp.status, resp.read().decode())
except urllib.error.HTTPError as e:
    print("Error:", e.code, e.read().decode())
