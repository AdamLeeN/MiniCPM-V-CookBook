# MiniCPM-V 4.6 - GGUF 量化指南

本指南将引导您将 MiniCPM-V 4.6 PyTorch 模型转换为 GGUF 格式并进行量化。

生成的 GGUF 可与 [`llama.cpp`](../../deployment/llama.cpp/minicpm-v4_6_llamacpp_zh.md) 或 [`ollama`](../../deployment/ollama/minicpm-v4_6_ollama_zh.md) 配合使用。

> [!NOTE]
> v4.6 的转换流程**比 v4.5 更简洁**。模型已合并入 `transformers>=5.7.0`，`llama.cpp` 标准的 `convert_hf_to_gguf.py`（release `b9049` 及之后）一并处理语言模型与视觉 projector，**不再需要** `minicpmv-surgery.py` + `minicpmv-convert-image-encoder-to-gguf.py` 这套老脚本。

### 1. 下载 PyTorch 模型

按需选择 checkpoint：

- **Instruct** — HuggingFace：<https://huggingface.co/openbmb/MiniCPM-V-4_6> · 魔搭：<https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6>
- **Thinking** — HuggingFace：<https://huggingface.co/openbmb/MiniCPM-V-4_6-Thinking> · 魔搭：<https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6-Thinking>

### 2. 转换为 GGUF

在 `llama.cpp`（release `b9049` 及之后）的仓库根目录下执行：

```bash
# 步骤 1：将语言模型 + 视觉 merger 转为 F16 GGUF
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --outfile /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-F16.gguf \
    --outtype f16

# 步骤 2：转换视觉 projector（mmproj）
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --mmproj \
    --outfile /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf
```

`convert_hf_to_gguf.py` 会从 `config.json` 自动识别 `MiniCPMV4_6ForConditionalGeneration`。

### 3. INT4 量化

得到 F16 的语言模型 GGUF 后，使用 `llama-quantize` 进行量化：

```bash
./llama-quantize \
    /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-F16.gguf \
    /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-Q4_K_M.gguf \
    Q4_K_M
```

常用的量化档位还有 `Q5_K_M`、`Q6_K`、`Q8_0`，根据精度和显存预算选择即可。

视觉 mmproj 文件本身较小，建议保持 `F16` 与所选 LM 量化版本搭配使用。
