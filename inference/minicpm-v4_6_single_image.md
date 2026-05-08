# Single Image (MiniCPM-V 4.6)

> MiniCPM-V 4.6 is registered upstream in `transformers>=5.7.0` as the standalone architecture `MiniCPMV4_6ForConditionalGeneration`, so the standard HuggingFace `Processor` + `model.generate` flow works out of the box.

## Initialize model

```python
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

# Pick the variant you want:
#   "openbmb/MiniCPM-V-4_6"        — Instruct
#   "openbmb/MiniCPM-V-4_6-Thinking"  — Thinking
model_path = "openbmb/MiniCPM-V-4_6"

processor = AutoProcessor.from_pretrained(model_path)
model = AutoModelForImageTextToText.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    attn_implementation="sdpa",  # or "flash_attention_2"
).eval().cuda()
```

## Chat with a single image

```python
image = Image.open("./assets/single.png").convert("RGB")

# First round
question = "What is the landform in the picture?"
messages = [{
    "role": "user",
    "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": question},
    ],
}]

inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(model.device)

out_ids = model.generate(**inputs, max_new_tokens=512)
answer = processor.decode(
    out_ids[0][inputs["input_ids"].shape[-1]:],
    skip_special_tokens=True,
)
print(answer)
```

## Second round

```python
messages.append({"role": "assistant", "content": [{"type": "text", "text": answer}]})
messages.append({
    "role": "user",
    "content": [{"type": "text", "text": "What should I pay attention to when traveling here?"}],
})

inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(model.device)

out_ids = model.generate(**inputs, max_new_tokens=512)
answer = processor.decode(
    out_ids[0][inputs["input_ids"].shape[-1]:],
    skip_special_tokens=True,
)
print(answer)
```

## Sample image

![alt text](./assets/single.png)

## Notes on the Thinking variant

If `model_path` points to `openbmb/MiniCPM-V-4_6-Thinking`, the chat template prepends a `<think>\n` block to the assistant turn — the model returns `<reasoning>\n</think>\n<final answer>`. To skip the leading `<think>` block, pass `enable_thinking=False`:

```python
inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
    chat_template_kwargs={"enable_thinking": False},
).to(model.device)
```

The Instruct checkpoint never emits `<think>` blocks; pick the appropriate checkpoint for your task instead of toggling at request time.
