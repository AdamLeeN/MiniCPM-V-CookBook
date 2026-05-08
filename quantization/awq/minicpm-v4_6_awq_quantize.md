# AWQ

::::{Note}
**Support:** MiniCPM-V 4.6 (Instruct & Thinking) / MiniCPM-V 4.5
::::

> The AutoAWQ workflow used by MiniCPM-V is hosted at [`tc-mb/AutoAWQ`](https://github.com/tc-mb/AutoAWQ) (the upstream `casper-hansen/AutoAWQ` is no longer maintained).
>
> MiniCPM-V 4.6 requires `transformers>=5.7.0`; the AutoAWQ fork tracks that requirement.

## Method 1 — Use the pre-quantized model with vLLM

### 1. Download the pre-quantized model

```bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_6-AWQ
```

(Or `openbmb/MiniCPM-V-4_6-Thinking-AWQ` for the Thinking variant once published.)

### 2. Run with vLLM

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
        {"type": "text", "text": "Please describe the content of this image"},
    ],
}]

prompt = processor.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)

sampling_params = SamplingParams(
    stop_token_ids=[248044, 248046],   # v4.6 uses Qwen3.5 vocab
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

## Method 2 — Run the AWQ checkpoint with AutoAWQ directly

### 1. Download the model

```bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_6-AWQ
```

### 2. Build AutoAWQ from source

```bash
git clone https://github.com/tc-mb/AutoAWQ.git
cd AutoAWQ
pip install -e .
```

### 3. Inference script

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
        {"type": "text", "text": "What is in this picture?"},
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
print("Output:", response)
```

## Method 3 — Quantize the model yourself

### 1. Download the original model

```bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_6
```

### 2. Build AutoAWQ from source

```bash
git clone https://github.com/tc-mb/AutoAWQ.git
cd AutoAWQ
pip install -e .
```

### 3. Quantization script

```python
import os
import shutil
import torch
from datasets import load_dataset
from transformers import AutoTokenizer
from awq import AutoAWQForCausalLM

model_path = "/openbmb/MiniCPM-V-4_6"
quant_path = "/model_quantized/minicpmv4_6_awq"

# AWQ config — 4-bit weights, group size 128, GEMM backend
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
    """Copy non-weight files from A to B if missing."""
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
