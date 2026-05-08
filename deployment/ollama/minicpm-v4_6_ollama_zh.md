# MiniCPM-V 4.6 - Ollama

> [!NOTE]
> MiniCPM-V 4.6 的 GGUF 支持已合并到上游 `llama.cpp`（[release `b9049`](https://github.com/ggml-org/llama.cpp/releases/tag/b9049)）。对应的 Ollama 支持正在上游合并中。在官方 Ollama 发布版包含此支持之前，可以选择以下任一方案：
> 1. 直接使用 `llama.cpp`（见 [llama.cpp 指南](../llama.cpp/minicpm-v4_6_llamacpp_zh.md)），或
> 2. 按下方步骤编译 OpenBMB Ollama 分支。

## 1. 安装 Ollama

- **macOS**：[下载](https://ollama.com/download/Ollama.dmg)
- **Windows**：[下载](https://ollama.com/download/OllamaSetup.exe)
- **Linux**：`curl -fsSL https://ollama.com/install.sh | sh`，或参照 Ollama 官方[手动安装指南](https://github.com/ollama/ollama/blob/main/docs/linux.md)。
- **Docker**：官方的 [Ollama Docker 镜像](https://hub.docker.com/r/ollama/ollama) `ollama/ollama` 已在 Docker Hub 上提供。

### 本地构建运行 Ollama（v4.6 当前推荐）

环境需求：

- [go](https://go.dev/doc/install) ≥ 1.22
- cmake ≥ 3.24
- C/C++ 编译工具链（macOS：Clang；Windows：[TDM-GCC](https://github.com/jmeubank/tdm-gcc/releases) / [llvm-mingw](https://github.com/mstorsjo/llvm-mingw)；Linux：GCC/Clang）

获取支持 MiniCPM-V 4.6 的 OpenBMB Ollama 分支：

```bash
git clone https://github.com/tc-mb/ollama.git
cd ollama
git checkout MIniCPM-V
```

在仓库根目录下编译并运行：

```bash
go build .
./ollama serve
```

## 2. 快速使用

OpenBMB 在 Ollama registry 上发布的模型可直接运行：

```bash
./ollama run openbmb/minicpm-v4.6
# 或 Thinking 版本
./ollama run openbmb/minicpm-v4.6-thinking
```

### 命令行

用空格分隔输入问题和图片路径：

```text
这张图片描述了什么？ xx.jpg
```

### API

```python
import base64, requests

with open(image_path, 'rb') as image_file:
    # 将图片文件转换为 base64 编码
    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    data = {
        "model": "minicpm-v4.6",
        "prompt": query,
        "stream": False,
        "images": [encoded_string],  # 列表可以放多张图，每张图用上面的方式转化为 base64
    }
    url = "http://localhost:11434/api/generate"
    response = requests.post(url, json=data)
```

## 3. 自定义方式

**若上述方式无法运行，请按下面的步骤手动加载 v4.6 GGUF 权重。**

### 获取 GGUF 模型

- HuggingFace：<https://huggingface.co/openbmb/MiniCPM-V-4_6-gguf>
- 魔搭社区：<https://modelscope.cn/models/OpenBMB/MiniCPM-V-4_6-gguf>

（Thinking 版本：`openbmb/MiniCPM-V-4_6-Thinking-gguf`）

### 创建 ModelFile

```bash
vim minicpmv4.6.Modelfile
```

ModelFile 的内容如下：

```plaintext
FROM ./MiniCPM-V-4_6/MiniCPM-V-4_6-Q4_K_M.gguf
FROM ./MiniCPM-V-4_6/mmproj-MiniCPM-V-4_6-F16.gguf

TEMPLATE """{{- if .Messages }}{{- range $i, $_ := .Messages }}{{- $last := eq (len (slice $.Messages $i)) 1 -}}<|im_start|>{{ .Role }}{{ .Content }}{{- if $last }}{{- if (ne .Role "assistant") }}<|im_end|><|im_start|>assistant{{ end }}{{- else }}<|im_end|>{{ end }}{{- end }}{{- else }}{{- if .System }}<|im_start|>system{{ .System }}<|im_end|>{{ end }}{{ if .Prompt }}<|im_start|>user{{ .Prompt }}<|im_end|>{{ end }}<|im_start|>assistant{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}"""

SYSTEM """You are a helpful assistant."""

PARAMETER top_p 0.8
PARAMETER num_ctx 8192
PARAMETER stop ["<|im_start|>", "<|im_end|>"]
PARAMETER temperature 0.7
```

参数说明：

| first FROM | second FROM | num_ctx |
| :--- | :--- | :--- |
| 语言模型 GGUF 路径 | 视觉 projector GGUF 路径 | 最大上下文长度 |

### 创建 Ollama 模型实例

```bash
./ollama create minicpm-v4.6 -f minicpmv4.6.Modelfile
```

### 另起一个命令行窗口，运行 Ollama 模型实例

```bash
./ollama run minicpm-v4.6
```

### 输入问题和图片路径，以空格分隔

```text
这张图片描述了什么？ xx.jpg
```
