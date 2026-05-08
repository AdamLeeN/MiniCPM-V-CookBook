# MiniCPM-V 4.6 - llama.cpp

> [!NOTE]
> MiniCPM-V 4.6 已合并到官方 `llama.cpp`（[PR #22529](https://github.com/ggml-org/llama.cpp/pull/22529)），从 release [`b9049`](https://github.com/ggml-org/llama.cpp/releases/tag/b9049) 开始包含。
>
> 与 v4.5 相比，v4.6 重做了视觉塔（resampler 被替换为新的 merger 结构，提升 ViT 推理效率），并且 GGUF 转换合并到了标准的 `convert_hf_to_gguf.py` 流程中 —— **不再需要专用的 surgery 脚本**。

## 1. 编译安装 llama.cpp

克隆 llama.cpp 代码仓库（需要 release `b9049` 及之后的提交）：

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
```

使用 `CMake` 构建（详见[构建文档](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)）：

**CPU / Metal：**

```bash
cmake -B build
cmake --build build --config Release
```

**CUDA：**

```bash
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release
```

## 2. 获取 GGUF 权重

### 方法一：下载官方 GGUF 文件

从仓库中下载语言模型文件（如 `MiniCPM-V-4_6-Q4_K_M.gguf`）与视觉模型文件（`mmproj-MiniCPM-V-4_6-F16.gguf`）：

- HuggingFace：<https://huggingface.co/openbmb/MiniCPM-V-4_6-gguf>
- 魔搭社区：<https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6-gguf>

Thinking 版本在以下仓库单独发布：

- <https://huggingface.co/openbmb/MiniCPM-V-4_6-Thinking-gguf>

### 方法二：从 PyTorch 模型转换

下载 PyTorch 模型：

- HuggingFace：<https://huggingface.co/openbmb/MiniCPM-V-4_6>（或 `MiniCPM-V-4_6-Thinking`）
- 魔搭社区：<https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6>

用 `llama.cpp` 仓库自带的标准脚本 `convert_hf_to_gguf.py` 直接转换：

```bash
# 1) 将语言模型 + 视觉 merger 转为 GGUF
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --outfile /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-F16.gguf \
    --outtype f16

# 2) 转换视觉 projector（mmproj）
python ./convert_hf_to_gguf.py /path/to/MiniCPM-V-4_6 \
    --mmproj \
    --outfile /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf
```

`convert_hf_to_gguf.py` 会从 `config.json` 自动识别 `MiniCPMV4_6ForConditionalGeneration`，同时输出 LM 与视觉塔。

> v4.6 不再需要 `legacy-models/minicpmv-surgery.py` + `minicpmv-convert-image-encoder-to-gguf.py` 这套两步流程。如果您在跟随旧的 v4.5 文档，请忽略这些脚本。

## 3. 模型推理

```bash
cd build/bin/

# F16 版本
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-F16.gguf \
    --mmproj /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg -p "请描述这张图片"

# INT4 量化版本
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-Q4_K_M.gguf \
    --mmproj /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg -p "请描述这张图片"

# 交互模式
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6/MiniCPM-V-4_6-Q4_K_M.gguf \
    --mmproj /path/to/MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg -i
```

部署 **Thinking** 模型时，可通过 `--jinja` + `--reasoning-budget` 控制思考预算：

```bash
# Thinking 模型 - 不限制思考输出
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6-Thinking/MiniCPM-V-4_6-Thinking-Q4_K_M.gguf \
    --mmproj /path/to/MiniCPM-V-4_6-Thinking/mmproj-MiniCPM-V-4_6-Thinking-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg --jinja --reasoning-budget -1 -p "图中有什么？"

# Thinking 模型 - 跳过开头的 <think> 块（直接出答案）
./llama-mtmd-cli \
    -m  /path/to/MiniCPM-V-4_6-Thinking/MiniCPM-V-4_6-Thinking-Q4_K_M.gguf \
    --mmproj /path/to/MiniCPM-V-4_6-Thinking/mmproj-MiniCPM-V-4_6-Thinking-F16.gguf \
    -c 8192 --temp 0.7 --top-p 0.8 --top-k 100 --repeat-penalty 1.05 \
    --image xx.jpg --jinja --reasoning-budget 0 -p "图中有什么？"
```

Instruct 模型本身不会生成 `<think>` 块，因此 `--reasoning-budget` 在它上面是无效的。

**命令行参数说明：**

| 参数 | `-m, --model` | `--mmproj` | `--image` | `-p, --prompt` | `-c, --ctx-size` | `--reasoning-budget` | `--jinja` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 含义 | 语言模型路径 | 视觉模型路径 | 输入图片路径 | 提示词 | 输入上下文最大长度 | 最大思考输出 token 数（`-1` 无限制，`0` 禁用） | 使用模型自带的 Jinja chat template |
