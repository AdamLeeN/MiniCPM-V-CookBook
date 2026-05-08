

# 🍳 MiniCPM-V & o Cookbook

[🏠 Main Repository](https://github.com/OpenBMB/MiniCPM-o) | [📚 Full Documentation](https://opensqz.github.io/MiniCPM-V-CookBook/)

Cook up amazing multimodal AI applications effortlessly with MiniCPM-o, bringing vision, speech, and live-streaming capabilities right to your fingertips! For version-specific deployment instructions, see the files in the [deployment](./deployment/) directory.



## ✨ What Makes Our Recipes Special?

### Easy Usage Documentation

Our comprehensive [documentation website](https://opensqz.github.io/MiniCPM-V-CookBook/) presents every recipe in a clear, well-organized manner.
All features are displayed at a glance, making it easy for you to quickly find exactly what you need.

### Broad User Spectrum

We support a wide range of users, from individuals to enterprises and researchers.

- **Individuals**: Enjoy effortless inference using [Ollama](./deployment/ollama/minicpm-v4_6_ollama.md) and [Llama.cpp](./deployment/llama.cpp/minicpm-v4_6_llamacpp.md) with minimal setup.
- **Enterprises**: Achieve high-throughput, scalable performance with [vLLM](./deployment/vllm/minicpm-v4_6_vllm.md) and [SGLang](./deployment/sglang/minicpm-v4_6_sglang.md).
- **Researchers**: Leverage advanced frameworks including [Transformers](./finetune/finetune_full.md) , [LLaMA-Factory](./finetune/finetune_llamafactory.md), [SWIFT](./finetune/swift.md), and [Align-anything](./finetune/align_anything.md) to enable flexible model development and cutting-edge experimentation.

### Versatile Deployment Scenarios

Our ecosystem delivers optimal solution for a variety of hardware environments and deployment demands.

- **Web demo**: Launch interactive multimodal AI web demo with [FastAPI](./demo/README.md).
- **Quantized deployment**: Maximize efficiency and minimize resource consumption using [GGUF](./quantization/gguf/minicpm-v4_6_gguf_quantize.md), [BNB](./quantization/bnb/minicpm-v4_6_bnb_quantize.md), and [AWQ](./quantization/awq/minicpm-v4_6_awq_quantize.md).
- **Edge devices**: Bring powerful AI experiences to [iPhone and iPad](./demo/ios_demo/ios.md), supporting offline and privacy-sensitive applications.

## ⭐️ Live Demonstrations

Explore real-world examples of MiniCPM-V deployed on edge devices using our curated recipes. These demos highlight the model’s high efficiency and robust performance in practical scenarios.

- Run locally on iPhone with [iOS demo](./demo/ios_demo/ios.md).

    



- Run locally on iPad with [iOS demo](./demo/ios_demo/ios.md), observing the process of drawing a rabbit.





## 🔥 Inference Recipes

> *Ready-to-run examples*


| Recipe                                                          | Description                                        |
| --------------------------------------------------------------- | -------------------------------------------------- |
| **Vision Capabilities** (MiniCPM-V 4.6)                         |                                                    |
| 🖼️ [Single-image QA](./inference/minicpm-v4_6_single_image.md) | Question answering on a single image               |
| 🧩 [Multi-image QA](./inference/minicpm-v4_6_multi_images.md)   | Question answering with multiple images            |
| 🎬 [Video QA](./inference/minicpm-v4_6_video_understanding.md)  | Video-based question answering                     |
| 📄 [Document Parser](./inference/minicpm-v4_6_pdf_parse.md)     | Parse and extract content from PDFs and webpages   |
| 📝 [Text Recognition](./inference/minicpm-v4_6_ocr.md)          | Reliable OCR for photos and screenshots            |
| 🎯 [Grounding](./inference/minicpm-v4_6_grounding.md)           | Visual grounding and object localization in images |
| **Audio Capabilities** (MiniCPM-o)                              |                                                    |
| 🎤 [Speech-to-Text](./inference/speech2text.md)                 | Multilingual speech recognition                    |
| 🗣️ [Text-to-Speech](./inference/text2speech.md)                | Instruction-following speech synthesis             |
| 🎭 [Voice Cloning](./inference/voice_clone.md)                  | Realistic voice cloning and role-play              |


## 🏋️ Fine-tuning Recipes

> *Customize your model with your own ingredients*

**Data preparation**

Follow the [guidance](./finetune/dataset_guidance.md) to set up your training datasets.

**Training**

We provide training methods serving different needs as following:


| Framework                                            | Description                                        |
| ---------------------------------------------------- | -------------------------------------------------- |
| [Transformers](./finetune/finetune_full.md)          | Most flexible for customization                    |
| [LLaMA-Factory](./finetune/finetune_llamafactory.md) | Modular fine-tuning toolkit                        |
| [SWIFT](./finetune/swift.md)                         | Lightweight and fast parameter-efficient tuning    |
| [Align-anything](./finetune/align_anything.md)       | Visual instruction alignment for multimodal models |


## 📦 Serving Recipes

> *Deploy your model efficiently*


| Method                                                       | Description                                  |
| ------------------------------------------------------------ | -------------------------------------------- |
| [vLLM](./deployment/vllm/minicpm-v4_6_vllm.md)               | High-throughput GPU inference                |
| [SGLang](./deployment/sglang/minicpm-v4_6_sglang.md)         | High-throughput GPU inference                |
| [Llama.cpp](./deployment/llama.cpp/minicpm-v4_6_llamacpp.md) | Fast CPU inference on PC, iPhone and iPad    |
| [Ollama](./deployment/ollama/minicpm-v4_6_ollama.md)         | User-friendly setup                          |
| [OpenWebUI](./demo/web_demo/openwebui)                       | Interactive Web demo with Open WebUI         |
| [Gradio](./demo/web_demo/gradio/README.md)                   | Interactive Web demo with Gradio             |
| [FastAPI](./demo/README.md)                                  | Interactive Omni Streaming demo with FastAPI |
| [iOS](./demo/ios_demo/ios.md)                                | Interactive iOS demo with llama.cpp          |


## 🥄 Quantization Recipes

> *Compress your model to improve efficiency*


| Format                                                    | Key Feature                                                                    |
| --------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [GGUF](./quantization/gguf/minicpm-v4_6_gguf_quantize.md) | Simplest and most portable format                                              |
| [BNB](./quantization/bnb/minicpm-v4_6_bnb_quantize.md)    | Simple and easy-to-use quantization method                                     |
| [AWQ](./quantization/awq/minicpm-v4_6_awq_quantize.md)    | High-performance quantization for efficient inference                          |
| [GPTQ](./quantization/gptq/minicpm-v4_5_gptq_quantize.md) | Weight-only INT4 with vLLM-compatible packaging *(v4.5 only — Qwen3 backbone)* |


## Framework Support Matrix

> The latest release is **MiniCPM-V 4.6** (Instruct + Thinking). The matrix below tracks v4.6 first, with v4.5 / o4.5 rows kept for reference.


| Model                        | Category                                                                                                            | Framework                                                                                                              | Cookbook Link                                                                                                          | Upstream PR                                                                                                                      | Supported since (branch)                                          | Supported since (release)                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **MiniCPM-V 4.6** *(latest)* | Inference                                                                                                           | Transformers                                                                                                           | [Transformers Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/inference/minicpm-v4_6_single_image.md)     | [huggingface/transformers](https://github.com/huggingface/transformers/tree/v5.7.0/src/transformers/models/minicpmv4_6) (merged) | main                                                              | [v5.7.0](https://github.com/huggingface/transformers/releases/tag/v5.7.0) |
| Edge (On-device)             | Llama.cpp                                                                                                           | [Llama.cpp Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/deployment/llama.cpp/minicpm-v4_6_llamacpp.md) | [#22529](https://github.com/ggml-org/llama.cpp/pull/22529) (2026-05-06)                                                | master (2026-05-06)                                                                                                              | [b9049](https://github.com/ggml-org/llama.cpp/releases/tag/b9049) |                                                                           |
| Ollama                       | [Ollama Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/deployment/ollama/minicpm-v4_6_ollama.md)      | Merging                                                                                                                | Merging                                                                                                                | Waiting for official release                                                                                                     |                                                                   |                                                                           |
| Serving (Cloud)              | vLLM                                                                                                                | [vLLM Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/deployment/vllm/minicpm-v4_6_vllm.md)               | [#41254](https://github.com/vllm-project/vllm/pull/41254) (2026-04-29)                                                 | Merging                                                                                                                          | Waiting for official release                                      |                                                                           |
| SGLang                       | [SGLang Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/deployment/sglang/minicpm-v4_6_sglang.md)      | Merging                                                                                                                | Merging                                                                                                                | Waiting for official release                                                                                                     |                                                                   |                                                                           |
| **MiniCPM-o 4.5**            | Edge (On-device)                                                                                                    | Llama.cpp                                                                                                              | [Llama.cpp Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/deployment/llama.cpp/minicpm-o4_5_llamacpp.md) | [#19211](https://github.com/ggml-org/llama.cpp/pull/19211)(2026-01-30)                                                           | master(2026-01-30)                                                | [b7895](https://github.com/ggml-org/llama.cpp/releases/tag/b7895)         |
| Ollama                       | [Ollama Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/deployment/ollama/minicpm-o4_5_ollama.md)      | [#12078](https://github.com/ollama/ollama/pull/12078)(2025-08-26)                                                      | Merging                                                                                                                | Waiting for official release                                                                                                     |                                                                   |                                                                           |
| Serving(Cloud)               | vLLM                                                                                                                | [vLLM Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/deployment/vllm/minicpm-o4_5_vllm.md)               | [#33431](https://github.com/vllm-project/vllm/pull/33431)(2026-01-30)                                                  | Merging                                                                                                                          | Waiting for official release                                      |                                                                           |
| SGLang                       | [SGLang Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/deployment/sglang/minicpm-o4_5_sglang.md)      | [#9610](https://github.com/sgl-project/sglang/pull/9610)(2025-08-26)                                                   | Merging                                                                                                                | Waiting for official release                                                                                                     |                                                                   |                                                                           |
| *Cross-version*              | Finetuning                                                                                                          | LLaMA-Factory                                                                                                          | [LLaMA-Factory Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/finetune/finetune_llamafactory.md)         | [#9022](https://github.com/hiyouga/LLaMA-Factory/pull/9022) (2025-08-26)                                                         | main (2025-08-26)                                                 | Waiting for official release                                              |
| Quantization                 | GGUF                                                                                                                | [GGUF Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/quantization/gguf/minicpm-v4_6_gguf_quantize.md)    | —                                                                                                                      | —                                                                                                                                | —                                                                 |                                                                           |
| BNB                          | [BNB Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/quantization/bnb/minicpm-v4_6_bnb_quantize.md)    | —                                                                                                                      | —                                                                                                                      | —                                                                                                                                |                                                                   |                                                                           |
| AWQ                          | [AWQ Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/quantization/awq/minicpm-v4_6_awq_quantize.md)    | [tc-mb/AutoAWQ](https://github.com/tc-mb/AutoAWQ)                                                                      | —                                                                                                                      | —                                                                                                                                |                                                                   |                                                                           |
| GPTQ                         | [GPTQ Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/quantization/gptq/minicpm-v4_5_gptq_quantize.md) | [openbmb/MiniCPM-V-4_5-GPTQ](https://huggingface.co/openbmb/MiniCPM-V-4_5-GPTQ)                                        | —                                                                                                                      | —                                                                                                                                |                                                                   |                                                                           |
| Demos                        | Gradio Demo                                                                                                         | [Gradio Demo Doc](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/demo/web_demo/gradio/README.md)              | —                                                                                                                      | —                                                                                                                                | —                                                                 |                                                                           |


If you'd like us to prioritize support for another open-source framework, please let us know via this
[short form](https://docs.google.com/forms/d/e/1FAIpQLSdyTUrOPBgWqPexs3ORrg47ZcZ1r4vFQaA4ve2iA7L9sMfMWw/viewform).

## Awesome Works using MiniCPM-V & o

- [text-extract-api](https://github.com/CatchTheTornado/text-extract-api): Document extraction API using OCRs and Ollama supported models GitHub Repo stars
- [comfyui_LLM_party](https://github.com/heshengtao/comfyui_LLM_party): Build LLM workflows and integrate into existing image workflows GitHub Repo stars
- [Ollama-OCR](https://github.com/imanoop7/Ollama-OCR): OCR package uses vlms through Ollama to extract text from images and PDF GitHub Repo stars
- [comfyui-mixlab-nodes](https://github.com/MixLabPro/comfyui-mixlab-nodes): ComfyUI node suite supports Workflow-to-APP、GPT&3D and more GitHub Repo stars
- [OpenAvatarChat](https://github.com/HumanAIGC-Engineering/OpenAvatarChat): Interactive digital human conversation implementation on single PC GitHub Repo stars
- [pensieve](https://github.com/arkohut/pensieve): A privacy-focused passive recording project by recording screen content GitHub Repo stars
- [paperless-gpt](https://github.com/icereed/paperless-gpt): Use LLMs to handle paperless-ngx, AI-powered titles, tags and OCR GitHub Repo stars
- [Neuro](https://github.com/kimjammer/Neuro): A recreation of Neuro-Sama, but running on local models on consumer hardware GitHub Repo stars

## 👥 Community

### Contributing

We love new recipes! Please share your creative dishes:

1. Fork the repository
2. Create your recipe
3. Submit a pull request

### Issues & Support

- Found a bug? [Open an issue](https://github.com/OpenBMB/MiniCPM-o/issues)
- Need help? Join our [Discord](https://discord.gg/rftuRMbqzf)

## Institutions

This cookbook is developed by [OpenBMB](https://github.com/openbmb) and [OpenSQZ](https://github.com/opensqz).

## 📜 License

This cookbook is served under the [Apache-2.0 License](LICENSE) - cook freely, share generously! 🍳

## Citation 

If you find our model/code/paper helpful, please consider citing our papers 📝 and staring us ⭐️！

```bib
@misc{yu2025minicpmv45cookingefficient,
      title={MiniCPM-V 4.5: Cooking Efficient MLLMs via Architecture, Data, and Training Recipe}, 
      author={Tianyu Yu and Zefan Wang and Chongyi Wang and Fuwei Huang and Wenshuo Ma and Zhihui He and Tianchi Cai and Weize Chen and Yuxiang Huang and Yuanqian Zhao and Bokai Xu and Junbo Cui and Yingjing Xu and Liqing Ruan and Luoyuan Zhang and Hanyu Liu and Jingkun Tang and Hongyuan Liu and Qining Guo and Wenhao Hu and Bingxiang He and Jie Zhou and Jie Cai and Ji Qi and Zonghao Guo and Chi Chen and Guoyang Zeng and Yuxuan Li and Ganqu Cui and Ning Ding and Xu Han and Yuan Yao and Zhiyuan Liu and Maosong Sun},
      year={2025},
      eprint={2509.18154},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2509.18154}, 
}

@article{yao2024minicpm,
  title={MiniCPM-V: A GPT-4V Level MLLM on Your Phone},
  author={Yao, Yuan and Yu, Tianyu and Zhang, Ao and Wang, Chongyi and Cui, Junbo and Zhu, Hongji and Cai, Tianchi and Li, Haoyu and Zhao, Weilin and He, Zhihui and others},
  journal={Nat Commun 16, 5509 (2025)},
  year={2025}
}

```

