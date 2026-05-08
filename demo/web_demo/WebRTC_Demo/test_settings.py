import sys
sys.path.insert(0, '/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/WebRTC_Demo/omini_backend_code/code')

from config import get_livekit_settings

s = get_livekit_settings()
print("URL:", repr(s.url))
print("API_KEY:", repr(s.api_key))
print("API_SECRET:", repr(s.api_secret[:10] if s.api_secret else None))
