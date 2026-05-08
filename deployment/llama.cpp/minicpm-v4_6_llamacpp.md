# MiniCPM-V 4.6 - llama.cpp

> [!NOTE]
> MiniCPM-V 4.6 support has been merged into the official `llama.cpp` ([PR #22529](https://github.com/ggml-org/llama.cpp/pull/22529)) and is included starting from release [`b9049`](https://github.com/ggml-org/llama.cpp/releases/tag/b9049).
>
> Compared to v4.5, v4.6 reworks the vision tower (the resampler is replaced by a new merger structure for better ViT efficiency), and GGUF conversion is now folded into the standard `convert_hf_to_gguf.py` flow — no model-specific surgery script is needed.

## 1. Build llama.cpp

Clone the upstream repository (require commit on/after release `b9049`):

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
```

Build with `CMake` (see [build docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) for details):

**CPU / Metal:**

```bash
cmake -B build
cmake --build build --config Release
```

**CUDA:**

```bash
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release
```

## 2. GGUF files

### Option 1: Download official GGUF files

Download the language model file (e.g., `MiniCPM-V-4_6-Q4_K_M.gguf`) and the vision projector (`mmproj-MiniCPM-V-4_6-F16.gguf`) from:

- HuggingFace: <https://huggingface.co/openbmb/MiniCPM-V-4_6-gguf>
- ModelScope: <https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6-gguf>

The Thinking variant is published separately at:

- <https://huggingface.co/openbmb/MiniCPM-V-4_6-Thinking-gguf>

### Option 2: Convert from PyTorch model

Download the PyTorch checkpoint:

- HuggingFace: <https://huggingface.co/openbmb/MiniCPM-V-4_6> (or `MiniCPM-V-4_6-Thinking`)
- ModelScope: <https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6>

Run the standard `convert_hf_to_gguf.py` from the `llama.cpp` repo:

```bash
# 1) Convert the language model + vision merger to GGUF
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --outfile /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-F16.gguf \
    --outtype f16

# 2) Convert the vision projector (mmproj)
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --mmproj \
    --outfile /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf
```

`convert_hf_to_gguf.py` autodetects `MiniCPMV4_6ForConditionalGeneration` from `config.json` and emits both the LM and the vision tower.

> v4.6 no longer needs the `legacy-models/minicpmv-surgery.py` + `minicpmv-convert-image-encoder-to-gguf.py` two-step. If you're following an older v4.5 guide, ignore those scripts here.

## 3. Model Inference

```bash
cd build/bin/

# F16 weights
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-F16.gguf \
    --mmproj /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg -p "What is in the image?"

# Quantized INT4 weights
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-Q4_K_M.gguf \
    --mmproj /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg -p "What is in the image?"

# Interactive mode
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-Q4_K_M.gguf \
    --mmproj /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg -i
```

If you're running the **Thinking** checkpoint, you can control the reasoning budget through `--jinja` + `--reasoning-budget`:

```bash
# Allow unlimited thinking (Thinking model)
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6-Thinking/MiniCPM-V-4_6-Thinking-Q4_K_M.gguf \
    --mmproj /path/to/MiniCPM-V-4_6-Thinking/mmproj-MiniCPM-V-4_6-Thinking-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg --jinja --reasoning-budget -1 -p "What is in the image?"

# Skip the leading <think> block on a Thinking model
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6-Thinking/MiniCPM-V-4_6-Thinking-Q4_K_M.gguf \
    --mmproj /path/to/MiniCPM-V-4_6-Thinking/mmproj-MiniCPM-V-4_6-Thinking-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg --jinja --reasoning-budget 0 -p "What is in the image?"
```

The Instruct checkpoint has no `<think>` block, so `--reasoning-budget` is a no-op there.

**Argument Reference:**

| Argument | `-m, --model` | `--mmproj` | `--image` | `-p, --prompt` | `-c, --ctx-size` | `--reasoning-budget` | `--jinja` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Description | Path to the language model | Path to the vision projector | Path to the input image | The prompt | Maximum context size | Maximum tokens used for reasoning (`-1` unlimited, `0` disabled) | Use the model's Jinja chat template |
