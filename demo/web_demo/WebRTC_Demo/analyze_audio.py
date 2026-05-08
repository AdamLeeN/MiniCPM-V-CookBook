import numpy as np
import wave

with wave.open("/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/received_audio_real.wav", "rb") as wf:
    data = wf.readframes(wf.getnframes())
    audio = np.frombuffer(data, dtype=np.int16)
    
    # 检测静音段（连续低于阈值的样本）
    threshold = 500
    is_silent = np.abs(audio) < threshold
    
    # 找出静音段的起止位置
    silent_runs = []
    start = None
    for i, silent in enumerate(is_silent):
        if silent and start is None:
            start = i
        elif not silent and start is not None:
            duration = (i - start) / 48000  # 转换为秒
            if duration > 0.05:  # 超过50ms的静音段
                silent_runs.append((start / 48000, i / 48000, duration))
            start = None
    
    print(f"总时长: {len(audio) / 48000:.2f} 秒")
    print(f"静音段数量 (>50ms): {len(silent_runs)}")
    print(f"\n前20个静音段:")
    for i, (s, e, d) in enumerate(silent_runs[:20]):
        print(f"  {i+1}. {s:.2f}s - {e:.2f}s, 持续 {d:.3f}s")
    
    # 计算有声段
    total_silent = sum(d for _, _, d in silent_runs)
    print(f"\n总静音时间: {total_silent:.2f} 秒")
    print(f"静音占比: {total_silent / (len(audio) / 48000) * 100:.1f}%")
