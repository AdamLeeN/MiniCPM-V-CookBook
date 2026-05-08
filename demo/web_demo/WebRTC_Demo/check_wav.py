import wave
with wave.open("/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio_real.wav", "rb") as wf:
    print(f"Channels: {wf.getnchannels()}")
    print(f"Sample Rate: {wf.getframerate()} Hz")
    print(f"Duration: {wf.getnframes() / wf.getframerate():.2f} seconds")
    print(f"File Size: {wf.getnframes() * wf.getsampwidth() * wf.getnchannels()} bytes")
