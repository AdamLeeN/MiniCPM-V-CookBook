import base64
import json

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiNzYwYWE2M2EtNDhjMS00NzlhLWFjYjAtYTdjZGMzZGM0ZGY3X25hbWUiLCJ2aWRlbyI6eyJyb29tSm9pbiI6dHJ1ZSwicm9vbSI6Ijc2MGFhNjNhLTQ4YzEtNDc5YS1hY2IwLWE3Y2RjM2RjNGRmNzgzIiwiY2FuUHVibGlzaCI6dHJ1ZSwiY2FuU3Vic2NyaWJlIjp0cnVlLCJjYW5QdWJsaXNoRGF0YSI6dHJ1ZX0sInN1YiI6Ijc2MGFhNjNhLTQ4YzEtNDc5YS1hY2IwLWE3Y2RjM2RjNGRmNyIsImlzcyI6ImRldmtleSIsIm5iZiI6MTc3ODIwOTQ5NiwiZXhwIjoxNzc4Mjk1ODk2fQ.kGl5Aqec0BrlUquxDWyD_HOGB9dgc8V1AzgXApkQHeQ"

parts = token.split(".")
payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
print("Token payload:")
print(json.dumps(payload, indent=2))
print("\nISS (issuer):", payload.get("iss"))
print("EXP:", payload.get("exp"))
