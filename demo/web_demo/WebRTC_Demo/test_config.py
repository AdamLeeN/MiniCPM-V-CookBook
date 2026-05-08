import sys
sys.path.insert(0, '/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/omini_backend_code/code')

from config import get_livekit_settings

settings = get_livekit_settings()
print("LiveKit URL:", settings.url)
print("LiveKit API Key:", settings.api_key)
print("LiveKit API Secret:", "***" if settings.api_secret else "EMPTY")
