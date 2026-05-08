# MiniCPM-V 4.6 - GGUF Quantization Guide

This guide walks through converting the MiniCPM-V 4.6 PyTorch model to GGUF and quantizing it.

The resulting GGUFs are meant to be used with [`llama.cpp`](../../deployment/llama.cpp/minicpm-v4_6_llamacpp.md) or [`ollama`](../../deployment/ollama/minicpm-v4_6_ollama.md).

> [!NOTE]
> v4.6 conversion is **simpler than v4.5**. The model is registered upstream in `transformers>=5.7.0`, and `llama.cpp`'s standard `convert_hf_to_gguf.py` (≥ release `b9049`) handles both the language model and the vision projector. The legacy `minicpmv-surgery.py` + `minicpmv-convert-image-encoder-to-gguf.py` scripts are no longer needed.

### 1. Download the PyTorch model

Pick the variant you want to quantize:

- **Instruct** — HuggingFace: <https://huggingface.co/openbmb/MiniCPM-V-4_6> · ModelScope: <https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6>
- **Thinking** — HuggingFace: <https://huggingface.co/openbmb/MiniCPM-V-4_6-Thinking> · ModelScope: <https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6-Thinking>

### 2. Convert to GGUF

Run from the root of a `llama.cpp` checkout (release `b9049` or later):

```bash
# Step 1 — convert the language model + vision merger to F16 GGUF
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --outfile /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-F16.gguf \
    --outtype f16

# Step 2 — convert the vision projector (mmproj)
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --mmproj \
    --outfile /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf
```

`convert_hf_to_gguf.py` autodetects `MiniCPMV4_6ForConditionalGeneration` from `config.json`.

### 3. Quantize to INT4

Once you have the F16 LM GGUF, quantize it with `llama-quantize`:

```bash
./llama-quantize \
    /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-F16.gguf \
    /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-Q4_K_M.gguf \
    Q4_K_M
```

Other common quant types you can swap in: `Q5_K_M`, `Q6_K`, `Q8_0`. Pick based on your accuracy vs. memory tradeoff.

The mmproj file is already small — keep it at `F16` and pair it with whichever quantization you chose for the LM.
