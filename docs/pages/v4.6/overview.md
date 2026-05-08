# MiniCPM-V 4.6 — Overview

> The latest release in the MiniCPM-V series.

## What's new in 4.6

- **Two checkpoints, one architecture.** Unlike 4.5 (one model, two modes via `enable_thinking`), 4.6 ships two independent checkpoints — pick whichever matches your use case.
  - [`openbmb/MiniCPM-V-4_6`](https://huggingface.co/openbmb/MiniCPM-V-4_6) — Instruct
  - [`openbmb/MiniCPM-V-4_6-Thinking`](https://huggingface.co/openbmb/MiniCPM-V-4_6-Thinking) — Thinking
- **Qwen3.5 hybrid backbone.** Mixed linear / full-attention layers, with up to **256K** context window.
- **NaViT-style vision tower.** Replaces the resampler with a more efficient merger structure — simpler GGUF conversion, fewer surgery scripts.
- **Standalone transformers architecture.** Registered as `MiniCPMV4_6ForConditionalGeneration` in `transformers >= 5.7.0`. Standard `AutoProcessor` + `AutoModelForImageTextToText` flow works out of the box.

## Quick start

### Inference (HF Transformers)

```python
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

model_path = "openbmb/MiniCPM-V-4_6"   # or MiniCPM-V-4_6-Thinking
processor = AutoProcessor.from_pretrained(model_path)
model = AutoModelForImageTextToText.from_pretrained(
    model_path, torch_dtype=torch.bfloat16, attn_implementation="sdpa",
).eval().cuda()

image = Image.open("example.jpg").convert("RGB")
messages = [{"role": "user", "content": [
    {"type": "image", "image": image},
    {"type": "text",  "text":  "Describe the image."},
]}]
inputs = processor.apply_chat_template(
    messages, add_generation_prompt=True, tokenize=True,
    return_dict=True, return_tensors="pt",
).to(model.device)

out = model.generate(**inputs, max_new_tokens=256)
print(processor.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True))
```

### Serve with vLLM

```bash
# v4.6 lives on the PR branch until vllm-project/vllm#41254 is merged
git clone -b Support-MiniCPM-V-4.6 https://github.com/tc-mb/vllm.git
cd vllm
MAX_JOBS=6 VLLM_USE_PRECOMPILED=1 pip install --editable . -v

vllm serve openbmb/MiniCPM-V-4_6 --trust-remote-code --max-model-len 8192
```

See the [vLLM guide](deployment/vllm.html) for full details.

### Run with llama.cpp

```bash
# release b9049 or newer ships v4.6 support
git clone https://github.com/ggml-org/llama.cpp.git && cd llama.cpp
cmake -B build && cmake --build build --config Release

# convert with the standard script (no surgery script needed for v4.6!)
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --outfile /path/to/MiniCPM-V-4_6-F16.gguf --outtype f16
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --mmproj --outfile /path/to/mmproj-MiniCPM-V-4_6-F16.gguf

./build/bin/llama-mtmd-cli \
    -m /path/to/MiniCPM-V-4_6-F16.gguf \
    --mmproj /path/to/mmproj-MiniCPM-V-4_6-F16.gguf \
    -c 8192 --image example.jpg -p "Describe the image."
```

See the [llama.cpp guide](deployment/llamacpp.html) for full details.

## Important differences from v4.5

| Topic | v4.5 | v4.6 |
| :--- | :--- | :--- |
| Thinking mode | One model, switch via `enable_thinking` | **Two separate checkpoints** (`Instruct`, `Thinking`) |
| LM backbone | Qwen3 | **Qwen3.5 hybrid** (linear + full attention) |
| Max context | 32K | **256K** |
| Vision tower | Perceiver resampler | **NaViT-style merger** |
| GGUF conversion | `minicpmv-surgery.py` + image encoder script | **Standard `convert_hf_to_gguf.py`** |
| Stop tokens (vLLM) | `[1, 151645]` | `[248044, 248046]` |
| Audio support | — (vision only) | — (vision only) |

If you're migrating from v4.5, the most common runtime gotchas are:

1. Update `stop_token_ids` to `[248044, 248046]` (the vocab is different — Qwen3.5 instead of Qwen3).
2. Drop the `enable_thinking` request flag and instead deploy the right checkpoint from the start.
3. The legacy `minicpmv-surgery.py` flow is no longer needed for GGUF — use `convert_hf_to_gguf.py` directly.

## Where to next

- **Try it out:** [Single-image QA](inference/single-image.html), [Video](inference/video-understanding.html), [Document parsing](inference/pdf-parse.html)
- **Deploy at scale:** [vLLM](deployment/vllm.html), [SGLang](deployment/sglang.html)
- **Run locally:** [llama.cpp](deployment/llamacpp.html), [Ollama](deployment/ollama.html)
- **Quantize:** [GGUF](quantization/gguf.html), [BNB](quantization/bnb.html), [AWQ](quantization/awq.html)
