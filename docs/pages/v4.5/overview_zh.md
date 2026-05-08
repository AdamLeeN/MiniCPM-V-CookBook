# MiniCPM-V 4.5 — 概览

视觉-语言多模态大模型，在图像 / 视频理解、OCR、文档解析方面表现优异。与 MiniCPM-o 4.5 同时发布。

> 新项目从这里开始？建议直接看 **[MiniCPM-V 4.6](../v4.6/overview.html)** —— 上下文更长、视觉塔更快，是当前推荐版本。

## 主要特性

- **9B 参数**，Qwen3 backbone
- 支持 **图像、多图、视频** 理解（无音频）
- 单模型，通过 `enable_thinking` 切换 **思考模式**
- HuggingFace：[`openbmb/MiniCPM-V-4_5`](https://huggingface.co/openbmb/MiniCPM-V-4_5) · 魔搭：[`OpenBMB/MiniCPM-V-4_5`](https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_5)

## 入口

- **推理：** [单图](inference/single-image.html)、[多图](inference/multi-images.html)、[视频](inference/video-understanding.html)、[OCR](inference/ocr.html)、[PDF](inference/pdf-parse.html)、[Grounding](inference/grounding.html)
- **部署：** [vLLM](deployment/vllm.html)、[SGLang](deployment/sglang.html)、[llama.cpp](deployment/llamacpp.html)、[Ollama](deployment/ollama.html)
- **量化：** [GGUF](quantization/gguf.html)、[BNB](quantization/bnb.html)、[AWQ](quantization/awq.html)
