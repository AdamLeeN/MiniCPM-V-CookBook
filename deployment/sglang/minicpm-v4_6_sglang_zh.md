# MiniCPM-V 4.6 - SGLang

> [!NOTE]
> SGLang 上游对 MiniCPM-V 4.6 的支持目前还在合并中。在官方版本发布前，请使用下方的 **OpenBMB SGLang 分支**。
>
> MiniCPM-V 4.6 在 `transformers>=5.7.0` 中以独立架构 `MiniCPMV4_6ForConditionalGeneration` 注册，SGLang 的适配也基于这一布局。

MiniCPM-V 4.6 提供两个 checkpoint：

- **Instruct** — [`openbmb/MiniCPM-V-4_6`](https://huggingface.co/openbmb/MiniCPM-V-4_6)
- **Thinking（思考）** — [`openbmb/MiniCPM-V-4_6-Thinking`](https://huggingface.co/openbmb/MiniCPM-V-4_6-Thinking)

## 1. SGLang 安装

### 从 PR 分支源码安装

```bash
# 克隆 OpenBMB 维护的 SGLang v4.6 分支
git clone -b Support-MiniCPM-V-4.6 https://github.com/tc-mb/sglang.git
cd sglang

pip install --upgrade pip
pip install -e "python[all]"
```

执行上述命令时会自动安装 `transformers>=5.7.0`。

### flashinfer 依赖（可选，建议安装）

方法 1：pip 安装（网速可能不行）

```bash
pip install flashinfer -i https://flashinfer.ai/whl/cu121/torch2.4/
```

方法 2：whl 文件安装

- 访问：[https://flashinfer.ai/whl/cu121/torch2.4/flashinfer/](https://flashinfer.ai/whl/cu121/torch2.4/flashinfer/)
- 找到适合自己服务器的版本下载，例如：`flashinfer-0.1.6+cu121torch2.4-cp310-cp310-linux_x86_64.whl`
- 用 pip 安装：

  ```bash
  pip install flashinfer-0.1.6+cu121torch2.4-cp310-cp310-linux_x86_64.whl
  ```

如有问题请参考 [SGLang 官方安装文档](https://docs.sglang.ai/start/install.html)。

## 2. 启动推理服务

默认情况下，会从 Hugging Face Hub 下载模型文件：

```bash
python -m sglang.launch_server --model-path openbmb/MiniCPM-V-4_6 --port 30000 --trust-remote-code
```

也可以在 `--model-path` 后指定本地路径：

```bash
python -m sglang.launch_server --model-path /your/local/MiniCPM-V-4_6 --port 30000 --trust-remote-code
```

部署 Thinking 模型只需替换 model id：

```bash
python -m sglang.launch_server --model-path openbmb/MiniCPM-V-4_6-Thinking --port 30000 --trust-remote-code
```

## 3. 调用服务接口

- bash / curl：

    ```bash
    curl -s http://localhost:30000/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{
        "model": "MiniCPM-V-4_6",
        "messages": [
          {
            "role": "user",
            "content": [
              {"type": "text", "text": "What is in this image?"},
              {
                "type": "image_url",
                "image_url": {
                  "url": "https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/inference/assets/airplane.jpeg?raw=true"
                }
              }
            ]
          }
        ],
        "max_tokens": 300
      }'
    ```

- Python（OpenAI 客户端）调用：

    ```python
    from openai import OpenAI

    client = OpenAI(base_url="http://localhost:30000/v1", api_key="None")

    response = client.chat.completions.create(
        model="MiniCPM-V-4_6",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请描述这张图片"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/inference/assets/airplane.jpeg?raw=true",
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
        extra_body={"stop_token_ids": [248044, 248046]},
    )

    print(response.choices[0].message.content)
    ```

> 如 `image_url` 无法访问，可替换为本地图片路径或 base64 data URL。
>
> v4.6 使用 Qwen3.5 词表 —— 若发现模型在回答后继续生成，请显式传入 `stop_token_ids=[248044, 248046]`。
>
> 更多调用方法可参考 [SGLang 使用文档](https://docs.sglang.ai/backend/openai_api_vision.html)。
