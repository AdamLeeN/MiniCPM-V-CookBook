# AWQ

::::{Note}
**支持版本：** MiniCPM-V 4.6（Instruct & Thinking）/ MiniCPM-V 4.5
::::

> MiniCPM-V 使用的 AutoAWQ 工作流位于 [`tc-mb/AutoAWQ`](https://github.com/tc-mb/AutoAWQ)（上游 `casper-hansen/AutoAWQ` 已停止维护）。
>
> MiniCPM-V 4.6 要求 `transformers>=5.7.0`；上述 AutoAWQ fork 同步跟进了这个依赖。

## 方法 1 — 用预量化模型 + vLLM 推理

### 1. 下载预量化模型

```bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_6-AWQ
```

（Thinking 版本发布后将是 `openbmb/MiniCPM-V-4_6-Thinking-AWQ`。）

### 2. 用 vLLM 运行

```python
from PIL import Image
from transformers import AutoProcessor
from vllm import LLM, SamplingParams

MODEL_NAME = "openbmb/MiniCPM-V-4_6-AWQ"
IMAGES = ["image.png"]

image = Image.open(IMAGES[0]).convert("RGB")
processor = AutoProcessor.from_pretrained(MODEL_NAME)

llm = LLM(
    model=MODEL_NAME,
    max_model_len=8192,
    trust_remote_code=True,
    # limit_mm_per_prompt={"image": 5},
)

messages = [{
    "role": "user",
    "content": [
        {"type": "image"},
        {"type": "text", "text": "请描述这张图片的内容"},
    ],
}]

prompt = processor.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)

sampling_params = SamplingParams(
    stop_token_ids=[248044, 248046],   # v4.6 使用 Qwen3.5 词表
    temperature=0.7,
    top_p=0.8,
    max_tokens=1024,
)

outputs = llm.generate(
    {
        "prompt": prompt,
        "multi_modal_data": {"image": image},
    },
    sampling_params=sampling_params,
)
print(outputs[0].outputs[0].text)
```

## 方法 2 — 用 AutoAWQ 直接运行 AWQ 模型

### 1. 下载模型

```bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_6-AWQ
```

### 2. 从源码安装 AutoAWQ

```bash
git clone https://github.com/tc-mb/AutoAWQ.git
cd AutoAWQ
pip install -e .
```

### 3. 推理脚本

```python
import torch
from PIL import Image
from transformers import AutoProcessor
from awq import AutoAWQForCausalLM

model_path = "openbmb/MiniCPM-V-4_6-AWQ"
image_path = "./assets/airplane.jpeg"

model = AutoAWQForCausalLM.from_quantized(
    model_path, trust_remote_code=True
).to("cuda")
processor = AutoProcessor.from_pretrained(model_path)

image = Image.open(image_path).convert("RGB")
messages = [{
    "role": "user",
    "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": "图中是什么？"},
    ],
}]

inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to("cuda")

with torch.inference_mode():
    out_ids = model.generate(**inputs, max_new_tokens=256)

response = processor.decode(
    out_ids[0][inputs["input_ids"].shape[-1]:],
    skip_special_tokens=True,
)
print("输出:", response)
```

## 方法 3 — 自己进行 AWQ 量化

### 1. 下载原始模型

```bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_6
```

### 2. 从源码安装 AutoAWQ

```bash
git clone https://github.com/tc-mb/AutoAWQ.git
cd AutoAWQ
pip install -e .
```

### 3. 量化脚本

```python
import os
import shutil
import torch
from datasets import load_dataset
from transformers import AutoTokenizer
from awq import AutoAWQForCausalLM

model_path = "/openbmb/MiniCPM-V-4_6"
quant_path = "/model_quantized/minicpmv4_6_awq"

# AWQ 配置 — 4-bit 权重，group size 128，GEMM 后端
quant_config = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4,
    "version": "GEMM",
}

model = AutoAWQForCausalLM.from_pretrained(
    model_path, trust_remote_code=True, torch_dtype=torch.bfloat16
)
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)


def copy_files_not_in_B(A_path, B_path):
    """如果文件在 A 中存在但 B 中不存在，则从 A 拷贝到 B（跳过权重文件）。"""
    if not os.path.exists(A_path):
        raise FileNotFoundError(f"The directory {A_path} does not exist.")
    if not os.path.exists(B_path):
        os.makedirs(B_path)

    files_in_A = set(
        f for f in os.listdir(A_path)
        if not (".bin" in f or "safetensors" in f)
    )
    files_in_B = set(os.listdir(B_path))

    for f in files_in_A - files_in_B:
        src = os.path.join(A_path, f)
        dst = os.path.join(B_path, f)
        if os.path.isfile(src):
            shutil.copy2(src, dst)


def load_alpaca():
    data = load_dataset("tatsu-lab/alpaca", split="train")

    def concatenate(x):
        if x["input"] and x["instruction"]:
            msgs = [
                {"role": "system", "content": x["instruction"]},
                {"role": "user", "content": x["input"]},
                {"role": "assistant", "content": x["output"]},
            ]
        elif x["input"]:
            msgs = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": x["input"]},
                {"role": "assistant", "content": x["output"]},
            ]
        else:
            msgs = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": x["instruction"]},
                {"role": "assistant", "content": x["output"]},
            ]
        text = tokenizer.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True
        )
        return {"text": text}

    return [r["text"] for r in data.map(concatenate)][:1024]


calib_data = load_alpaca()
model.quantize(tokenizer, quant_config=quant_config, calib_data=calib_data)

model.save_quantized(quant_path)
tokenizer.save_pretrained(quant_path)

copy_files_not_in_B(model_path, quant_path)
print(f'Model is quantized and saved at "{quant_path}"')
```
