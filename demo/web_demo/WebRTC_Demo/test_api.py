import requests
import json

resp = requests.get("http://127.0.0.1:9060/openapi.json")
d = resp.json()
print("Available endpoints:")
for path in d.get("paths", {}):
    print(f"  {path}")
