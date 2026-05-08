# OCR（MiniCPM-V 4.6）

## 加载模型

```python
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

model_path = "openbmb/MiniCPM-V-4_6"

processor = AutoProcessor.from_pretrained(model_path)
model = AutoModelForImageTextToText.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    attn_implementation="sdpa",
).eval().cuda()
```

## 使用示例

```python
ocr_image = Image.open("./assets/ocr.png").convert("RGB")

messages = [{
    "role": "user",
    "content": [
        {"type": "image", "image": ocr_image},
        {"type": "text",  "text":  "图中的文字是什么？"},
    ],
}]

inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(model.device)

out_ids = model.generate(**inputs, max_new_tokens=1024)
answer = processor.decode(
    out_ids[0][inputs["input_ids"].shape[-1]:],
    skip_special_tokens=True,
)
print(answer)
```

## 示例图片

![alt text](./assets/ocr.png)

> 对于中文密集或文本密集的页面，**Thinking** checkpoint（`openbmb/MiniCPM-V-4_6-Thinking`）通常能输出更忠实的转写结果，因为它会先分析版式再回答。Instruct checkpoint 速度更快，对于短文本 / 已经截好的文字图片通常已经够用。
