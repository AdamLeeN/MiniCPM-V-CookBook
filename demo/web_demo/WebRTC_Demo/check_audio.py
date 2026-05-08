import wave
import numpy as np

with wave.open("/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio.wav", "rb") as wf:
    print(f"Channels: {wf.getnchannels()}")
    print(f"Sample Width: {wf.getsampwidth()} bytes")
    print(f"Frame Rate: {wf.getframerate()} Hz")
    print(f"Total Frames: {wf.getnframes()}")
    print(f"Duration: {wf.getnframes() / wf.getframerate():.2f} seconds")
    
    # 读取前 1 秒数据检查
    frames = wf.readframes(wf.getframerate())
    audio = np.frombuffer(frames, dtype=np.int16)
    print(f"\nFirst second stats:")
    print(f"  Min: {audio.min()}")
    print(f"  Max: {audio.max()}")
    print(f"  Mean: {audio.mean():.2f}")
    print(f"  Std: {audio.std():.2f}")
    print(f"  Non-zero samples: {np.count_nonzero(audio)} / {len(audio)}")
    
    # 检查整个文件是否有声音（非零值）
    wf.rewind()
    all_frames = wf.readframes(wf.getnframes())
    all_audio = np.frombuffer(all_frames, dtype=np.int16)
    print(f"\nFull file stats:")
    print(f"  Min: {all_audio.min()}")
    print(f"  Max: {all_audio.max()}")
    print(f"  Mean: {all_audio.mean():.2f}")
    print(f"  Std: {all_audio.std():.2f}")
    print(f"  Non-zero samples: {np.count_nonzero(all_audio)} / {len(all_audio)}")
    
    # 检查是否有连续的静音（全零）
    zero_runs = 0
    current_run = 0
    max_run = 0
    for sample in all_audio:
        if sample == 0:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            if current_run > 4800:  # 超过 100ms 的静音
                zero_runs += 1
            current_run = 0
    
    print(f"\n  Zero runs > 100ms: {zero_runs}")
    print(f"  Max zero run: {max_run} samples ({max_run/48000*1000:.1f}ms)")
