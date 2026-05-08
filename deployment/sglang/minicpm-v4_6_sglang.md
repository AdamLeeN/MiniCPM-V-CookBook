# MiniCPM-V 4.6 - SGLang Documentation

> [!NOTE]
> SGLang upstream support for MiniCPM-V 4.6 is currently being merged. Until the PR lands in an official release, please install SGLang from the **OpenBMB SGLang fork** below.
>
> MiniCPM-V 4.6 is registered in `transformers>=5.7.0` as a standalone architecture (`MiniCPMV4_6ForConditionalGeneration`); the SGLang adapter follows that layout.

MiniCPM-V 4.6 ships as two checkpoints:

- **Instruct** — [`openbmb/MiniCPM-V-4_6`](https://huggingface.co/openbmb/MiniCPM-V-4_6)
- **Thinking** — [`openbmb/MiniCPM-V-4_6-Thinking`](https://huggingface.co/openbmb/MiniCPM-V-4_6-Thinking)

## 1. Installing SGLang

### Install SGLang from the PR / fork branch

```bash
# clone the OpenBMB-maintained SGLang branch with v4.6 support
git clone -b Support-MiniCPM-V-4.6 https://github.com/tc-mb/sglang.git
cd sglang

pip install --upgrade pip
pip install -e "python[all]"
```

`transformers>=5.7.0` will be installed automatically.

### Installing flashinfer (optional but recommended)

Method 1 — pip install:

```bash
pip install flashinfer -i https://flashinfer.ai/whl/cu121/torch2.4/
```

Method 2 — whl file:

- Visit [https://flashinfer.ai/whl/cu121/torch2.4/flashinfer/](https://flashinfer.ai/whl/cu121/torch2.4/flashinfer/)
- Download a wheel matching your environment (e.g., `flashinfer-0.1.6+cu121torch2.4-cp310-cp310-linux_x86_64.whl`)
- Install it with pip:

  ```bash
  pip install flashinfer-0.1.6+cu121torch2.4-cp310-cp310-linux_x86_64.whl
  ```

For more details, see the [official SGLang installation docs](https://docs.sglang.ai/start/install.html).

## 2. Launching the Inference Server

By default the server downloads weights from the HuggingFace Hub:

```bash
python -m sglang.launch_server --model-path openbmb/MiniCPM-V-4_6 --port 30000 --trust-remote-code
```

Or specify a local path:

```bash
python -m sglang.launch_server --model-path /your/local/MiniCPM-V-4_6 --port 30000 --trust-remote-code
```

To serve the Thinking variant, swap the model id:

```bash
python -m sglang.launch_server --model-path openbmb/MiniCPM-V-4_6-Thinking --port 30000 --trust-remote-code
```

## 3. Calling the Service

- Bash / curl:

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

- Python (OpenAI client):

    ```python
    from openai import OpenAI

    client = OpenAI(base_url="http://localhost:30000/v1", api_key="None")

    response = client.chat.completions.create(
        model="MiniCPM-V-4_6",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
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

> If `image_url` is not reachable from your machine, replace it with a local path / base64 data URL.
>
> v4.6 uses the Qwen3.5 vocabulary — pass `stop_token_ids = [248044, 248046]` if you observe the model continuing past the answer.
>
> For more invocation patterns, see the [SGLang documentation](https://docs.sglang.ai/backend/openai_api_vision.html).
