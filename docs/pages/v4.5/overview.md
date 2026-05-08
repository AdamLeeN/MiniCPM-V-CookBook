# MiniCPM-V 4.5 — Overview

A vision-language MLLM with strong performance on image / video understanding, OCR, and document parsing. Released alongside MiniCPM-o 4.5.

> Looking at this for a new project? Consider **[MiniCPM-V 4.6](../v4.6/overview.html)** instead — it has a longer context, faster vision tower, and is the actively-recommended release.

## Highlights

- **9B parameters**, Qwen3 backbone
- **Image, multi-image, and video** understanding (no audio)
- One model with optional **thinking mode** (toggle via `enable_thinking`)
- HuggingFace: [`openbmb/MiniCPM-V-4_5`](https://huggingface.co/openbmb/MiniCPM-V-4_5) · ModelScope: [`OpenBMB/MiniCPM-V-4_5`](https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_5)

## Where to start

- **Inference:** [Single image](inference/single-image.html), [Multi-image](inference/multi-images.html), [Video](inference/video-understanding.html), [OCR](inference/ocr.html), [PDF](inference/pdf-parse.html), [Grounding](inference/grounding.html)
- **Deploy:** [vLLM](deployment/vllm.html), [SGLang](deployment/sglang.html), [llama.cpp](deployment/llamacpp.html), [Ollama](deployment/ollama.html)
- **Quantize:** [GGUF](quantization/gguf.html), [BNB](quantization/bnb.html), [AWQ](quantization/awq.html)
