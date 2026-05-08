# 多图问答

### 加载模型

```python
from PIL import Image
import torch
from transformers import AutoModel, AutoTokenizer

model_path = 'openbmb/MiniCPM-V-4_5'
model = AutoModel.from_pretrained(model_path, trust_remote_code=True,
                                  attn_implementation='sdpa', torch_dtype=torch.bfloat16)  # sdpa 或 flash_attention_2，不要用 eager
model = model.eval().cuda()
tokenizer = AutoTokenizer.from_pretrained(
    model_path, trust_remote_code=True)
```

### 多图对话

```python
image1 = Image.open('assets/multi1.png').convert('RGB')
image2 = Image.open('assets/multi2.png').convert('RGB')
question = '比较这两张图片，告诉我它们之间的差异。'

msgs = [{'role': 'user', 'content': [image1, image2, question]}]

answer = model.chat(
    image=None,
    msgs=msgs,
    tokenizer=tokenizer
)
print(answer)
```

### 示例图片

![alt text](./assets/multi1.png)

![alt text](./assets/multi2.png)

### 示例输出

```
The vases have different shapes, with the first being rounder and more bulbous. The patterns on the vases are also distinct: the first vase has red designs against a white background, while the second features green and blue floral motifs. Additionally, the neck of the first vase is narrower than that of the second one.
```
