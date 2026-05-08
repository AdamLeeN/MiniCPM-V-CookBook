# 视频理解（MiniCPM-V 4.6）

> v4.6 的视频通路非常简洁：image processor 逐帧调用，单视频帧切片预算由 processor 上的 `max_slice_nums` 控制，**无需**特殊的视频后端。

## 加载模型

```python
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

model_path = "openbmb/MiniCPM-V-4_6"  # 或 "openbmb/MiniCPM-V-4_6-Thinking"

processor = AutoProcessor.from_pretrained(model_path)
model = AutoModelForImageTextToText.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    attn_implementation="sdpa",
).eval().cuda()
```

## 视频 → 帧序列

```python
from decord import VideoReader, cpu

MAX_NUM_FRAMES = 32  # 显存吃紧时调小

def encode_video(video_path: str):
    def uniform_sample(indices, n):
        gap = len(indices) / n
        return [indices[int(i * gap + gap / 2)] for i in range(n)]

    vr = VideoReader(video_path, ctx=cpu(0))
    sample_fps = round(vr.get_avg_fps() / 1)  # 约 1 fps
    frame_idx = list(range(0, len(vr), sample_fps))
    if len(frame_idx) > MAX_NUM_FRAMES:
        frame_idx = uniform_sample(frame_idx, MAX_NUM_FRAMES)
    frames = vr.get_batch(frame_idx).asnumpy()
    return [Image.fromarray(f.astype("uint8")) for f in frames]
```

## 视频对话

```python
video_path = "assets/badminton.mp4"
frames = encode_video(video_path)
print("帧数:", len(frames))

messages = [{
    "role": "user",
    "content": [
        {"type": "video", "video": frames},
        {"type": "text",  "text":  "描述这段视频"},
    ],
}]

inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
    # 需要时调整每个视频的切片预算（数值越小越省显存）
    chat_template_kwargs={},
    max_slice_nums=2,
).to(model.device)

out_ids = model.generate(**inputs, max_new_tokens=1024)
answer = processor.decode(
    out_ids[0][inputs["input_ids"].shape[-1]:],
    skip_special_tokens=True,
)
print(answer)
```

> 如果遇到 GPU OOM：
> 1. 调小 `MAX_NUM_FRAMES`；
> 2. 调小 `max_slice_nums`（设为 1 完全关闭切片）；
> 3. 用 `bfloat16` + `attn_implementation="sdpa"` 运行。
