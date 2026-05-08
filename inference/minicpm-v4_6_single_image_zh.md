# 单图问答（MiniCPM-V 4.6）

> MiniCPM-V 4.6 已经在 `transformers>=5.7.0` 中以独立架构 `MiniCPMV4_6ForConditionalGeneration` 注册，标准的 HuggingFace `Processor` + `model.generate` 流程开箱即用。

## 加载模型

```python
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

# 选择需要的 checkpoint：
#   "openbmb/MiniCPM-V-4_6"        — Instruct
#   "openbmb/MiniCPM-V-4_6-Thinking"  — Thinking（思考模式）
model_path = "openbmb/MiniCPM-V-4_6"

processor = AutoProcessor.from_pretrained(model_path)
model = AutoModelForImageTextToText.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    attn_implementation="sdpa",  # 也可设为 "flash_attention_2"
).eval().cuda()
```

## 单图对话

```python
image = Image.open("./assets/single.png").convert("RGB")

# 第一轮
question = "图片中的地貌是什么？"
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

## 第二轮对话

```python
messages.append({"role": "assistant", "content": [{"type": "text", "text": answer}]})
messages.append({
    "role": "user",
    "content": [{"type": "text", "text": "去这里旅行需要注意什么？"}],
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

## 示例图片

![alt text](./assets/single.png)

## 关于 Thinking 版本的说明

如果 `model_path` 指向 `openbmb/MiniCPM-V-4_6-Thinking`，chat template 会在 assistant 起始位置插入一个 `<think>\n` 块——模型会先输出 `<推理过程>\n</think>\n<最终回答>`。如需跳过开头的 `<think>` 块，传入 `enable_thinking=False`：

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

Instruct checkpoint 永远不会输出 `<think>` 块——按业务需求选择对应的 checkpoint，**无需在请求级别切换**。
