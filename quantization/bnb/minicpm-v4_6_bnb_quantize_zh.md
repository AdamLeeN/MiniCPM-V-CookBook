# BNB

:::{Note}
**支持版本：** MiniCPM-V 4.6 / MiniCPM-V 4.5 / MiniCPM-V 4.0 / MiniCPM-V 2.6 / MiniCPM-V 2.5
:::

## 1. 下载模型

从 [HuggingFace](https://huggingface.co/openbmb/MiniCPM-V-4_6) 下载 MiniCPM-V-4_6 模型（Thinking 版本为 `openbmb/MiniCPM-V-4_6-Thinking`），解压到本地目录。

## 2. 量化脚本

下方脚本会加载原始模型，使用 bitsandbytes 量化为 4-bit，运行一次推理校验，并保存量化后的模型。

> 需要 `transformers>=5.7.0`（MiniCPM-V 4.6 在该版本注册为独立架构）。

```python
import os
import time
import torch
from transformers import (
    AutoProcessor,
    AutoModelForImageTextToText,
    BitsAndBytesConfig,
)
from PIL import Image

assert torch.cuda.is_available(), "CUDA is not available, but this code requires a GPU."

device = "cuda"
model_path = "/model/MiniCPM-V-4_6"  # 原始模型路径
save_path = "./model/MiniCPM-V-4_6-int4"  # 量化模型保存路径
image_path = "./assets/airplane.jpeg"

# 4-bit 量化配置
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    load_in_8bit=False,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_storage=torch.uint8,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    llm_int8_enable_fp32_cpu_offload=False,
    llm_int8_has_fp16_weight=False,
    llm_int8_skip_modules=["lm_head"],
    llm_int8_threshold=6.0,
)

processor = AutoProcessor.from_pretrained(model_path)
model = AutoModelForImageTextToText.from_pretrained(
    model_path,
    device_map=device,
    quantization_config=quantization_config,
)

image = Image.open(image_path).convert("RGB")
messages = [{
    "role": "user",
    "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": "图中是什么？"},
    ],
}]

inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(model.device)

start = time.time()
out_ids = model.generate(**inputs, max_new_tokens=256)
response = processor.decode(
    out_ids[0][inputs["input_ids"].shape[-1]:],
    skip_special_tokens=True,
)

print("量化后输出：", response)
print("量化后推理耗时：", time.time() - start)

# 保存量化模型与 tokenizer / processor
os.makedirs(save_path, exist_ok=True)
model.save_pretrained(save_path, safe_serialization=True)
processor.save_pretrained(save_path)
```

## 3. 预期输出

量化完成后大致会看到：

```text
量化后输出： 图中是一架空客 A380-800 飞机，正在晴朗蓝天中飞行。机身以白色为主，垂直尾翼是醒目的蓝色，并印有红白配色的徽标。……
量化后推理耗时： 单卡 A100/4090 上约 9 s
```

量化模型会保存到 `save_path`，可通过 `AutoModelForImageTextToText.from_pretrained(save_path)` 重新加载继续推理或微调。

---
要自定义模型路径、图片或保存路径，修改脚本顶部的变量即可。
