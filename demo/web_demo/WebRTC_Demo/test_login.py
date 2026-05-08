import requests
import json

resp = requests.post(
    "http://127.0.0.1:8021/api/login",
    json={"modelType": "simplex", "sessionType": "audio", "serviceName": "o45-cpp"}
)
print("Status:", resp.status_code)
print("Response:", resp.text[:1000])
