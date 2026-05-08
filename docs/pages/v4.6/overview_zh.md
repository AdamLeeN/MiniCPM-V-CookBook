# MiniCPM-V 4.6 — 概览

> MiniCPM-V 系列的最新版本。

## 4.6 新特性

- **两个独立 checkpoint，统一架构。** 与 4.5（一份模型 + `enable_thinking` 切换）不同，4.6 拆为两个独立 checkpoint，按需选用。
  - [`openbmb/MiniCPM-V-4_6`](https://huggingface.co/openbmb/MiniCPM-V-4_6) —— Instruct
  - [`openbmb/MiniCPM-V-4_6-Thinking`](https://huggingface.co/openbmb/MiniCPM-V-4_6-Thinking) —— Thinking（思考）
- **Qwen3.5 hybrid backbone。** 线性注意力与全注意力混合，最长支持 **256K** 上下文。
- **NaViT 风格视觉塔。** 用 merger 替换原有 resampler，结构更高效，GGUF 转换流程也大大简化。
- **transformers 独立架构。** 在 `transformers >= 5.7.0` 中以 `MiniCPMV4_6ForConditionalGeneration` 注册，标准 `AutoProcessor` + `AutoModelForImageTextToText` 即可使用。

## 快速上手

### 推理（HF Transformers）

```python
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

model_path = "openbmb/MiniCPM-V-4_6"   # 或 MiniCPM-V-4_6-Thinking
processor = AutoProcessor.from_pretrained(model_path)
model = AutoModelForImageTextToText.from_pretrained(
    model_path, torch_dtype=torch.bfloat16, attn_implementation="sdpa",
).eval().cuda()

image = Image.open("example.jpg").convert("RGB")
messages = [{"role": "user", "content": [
    {"type": "image", "image": image},
    {"type": "text",  "text":  "请描述这张图片"},
]}]
inputs = processor.apply_chat_template(
    messages, add_generation_prompt=True, tokenize=True,
    return_dict=True, return_tensors="pt",
).to(model.device)

out = model.generate(**inputs, max_new_tokens=256)
print(processor.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True))
```

### 用 vLLM 部署

```bash
# v4.6 在 vllm-project/vllm#41254 合并前请使用 PR 分支
git clone -b Support-MiniCPM-V-4.6 https://github.com/tc-mb/vllm.git
cd vllm
MAX_JOBS=6 VLLM_USE_PRECOMPILED=1 pip install --editable . -v

vllm serve openbmb/MiniCPM-V-4_6 --trust-remote-code --max-model-len 8192
```

详见 [vLLM 部署指南](deployment/vllm.html)。

### 用 llama.cpp 部署

```bash
# release b9049 起包含 v4.6 支持
git clone https://github.com/ggml-org/llama.cpp.git && cd llama.cpp
cmake -B build && cmake --build build --config Release

# 用标准脚本转换（v4.6 不再需要 surgery 脚本！）
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --outfile /path/to/MiniCPM-V-4_6-F16.gguf --outtype f16
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --mmproj --outfile /path/to/mmproj-MiniCPM-V-4_6-F16.gguf

./build/bin/llama-mtmd-cli \
    -m /path/to/MiniCPM-V-4_6-F16.gguf \
    --mmproj /path/to/mmproj-MiniCPM-V-4_6-F16.gguf \
    -c 8192 --image example.jpg -p "请描述这张图片"
```

详见 [llama.cpp 部署指南](deployment/llamacpp.html)。

## 与 v4.5 的关键差异

| 主题 | v4.5 | v4.6 |
| :--- | :--- | :--- |
| 思考模式 | 单模型，请求级 `enable_thinking` 切换 | **两个独立 checkpoint**（Instruct、Thinking） |
| LM Backbone | Qwen3 | **Qwen3.5 hybrid**（线性 + 全注意力） |
| 最大上下文 | 32K | **256K** |
| 视觉塔 | Perceiver resampler | **NaViT 风格 merger** |
| GGUF 转换 | `minicpmv-surgery.py` + image encoder 脚本 | **标准 `convert_hf_to_gguf.py`** |
| stop_token_ids（vLLM） | `[1, 151645]` | `[248044, 248046]` |
| 音频 | —（仅视觉） | —（仅视觉） |

从 v4.5 迁移过来时，最常见的几个坑：

1. `stop_token_ids` 改为 `[248044, 248046]`（Qwen3.5 与 Qwen3 词表不同）。
2. 不再使用 `enable_thinking` 请求参数 —— 改为部署对应 checkpoint。
3. GGUF 转换不再需要 `minicpmv-surgery.py`，直接用 `convert_hf_to_gguf.py`。

## 下一步

- **试用：** [单图问答](inference/single-image.html)、[视频](inference/video-understanding.html)、[文档解析](inference/pdf-parse.html)
- **大规模部署：** [vLLM](deployment/vllm.html)、[SGLang](deployment/sglang.html)
- **本地运行：** [llama.cpp](deployment/llamacpp.html)、[Ollama](deployment/ollama.html)
- **量化：** [GGUF](quantization/gguf.html)、[BNB](quantization/bnb.html)、[AWQ](quantization/awq.html)
