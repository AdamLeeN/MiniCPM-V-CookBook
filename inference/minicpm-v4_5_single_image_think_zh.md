# 单图问答（思考模式）

### 加载思考模型

```python
from PIL import Image
import torch
from transformers import AutoModel, AutoTokenizer

model_path = 'openbmb/MiniCPM-V-4_5'
model = AutoModel.from_pretrained(model_path, trust_remote_code=True,
                                  # sdpa 或 flash_attention_2，不要用 eager
                                  attn_implementation='sdpa', torch_dtype=torch.bfloat16)
model = model.eval().cuda()
tokenizer = AutoTokenizer.from_pretrained(
    model_path, trust_remote_code=True)
```

### 单图对话

```python
image = Image.open('./assets/single.png').convert('RGB')

# 第一轮对话
question = "图片中的地貌是什么？"
msgs = [{'role': 'user', 'content': [image, question]}]

# 启用思考模式
answer = model.chat(
    msgs=msgs,
    image=image,
    tokenizer=tokenizer,
    enable_thinking=True
)
print(answer)
```

### 第二轮对话

```python
# 第二轮对话，带上多轮历史上下文
msgs.append({"role": "assistant", "content": [answer]})
msgs.append({"role": "user", "content": [
            "去这里旅行需要注意什么？"]})

answer = model.chat(
    msgs=msgs,
    image=None,
    tokenizer=tokenizer,
    enable_thinking=True
)
print(answer)
```

### 示例图片

![alt text](./assets/single.png)

### 示例输出

第一轮
```
<think>
So, let me analyze the image. The scene shows a long stone staircase winding through lush green mountains, with a pavilion at the top. This looks like a famous mountain path in China. The architectural style and the mountain path are characteristic of Mount Heng (also known as Songshan), which is part of the Hunan province. Wait, or maybe Mount Tai? No, Mount Heng's paths are known for steep steps. Wait, the image might be of the "Heng Mountain's ancient paths" or similar. Wait, the structure at the top is a pavilion, and the winding path through the mountains with such greenery... Let me think. Mount Heng (Hengshan) is one of the Five Sacred Mountains of China, and it has famous ancient paths. Alternatively, maybe Mount Lu? No, the landscape here seems more like Heng Mountain. Wait, the question is asking for the location. Since the image is of a mountain path with traditional Chinese architecture, and the steep steps between mountains, this is likely Mount Heng (Hengshan) in Hunan Province, China. Wait, but I should confirm. Another possibility is Mount Song (Songshan), but Songshan's paths are also steep. Wait, the pavilion at the top—maybe the South Sky Pavilion? Wait, maybe the image is of the "Tianping Steps" or something similar. But given the typical Chinese mountain scenery with such paths, the most famous is Mount Heng. Alternatively, maybe Mount Tai? No, Mount Tai's paths are different. Wait, the greenery and the steep stone steps winding up the mountain suggest this is a well-known sacred mountain path in China. After considering, the location is likely Mount Heng (Hengshan), Hunan Province, China.
</think>

To determine the location, analyze the image: it shows a steep, winding stone path through lush green mountains with traditional Chinese architecture (a pavilion at the top). This landscape is characteristic of Mount Heng (Hengshan), one of China's Five Sacred Mountains, known for its ancient stone steps and mountainous scenery. Thus, the place is located in Hunan Province, China.  
Ultimately, the answer is \boxed{Mount Heng (Hengshan), Hunan Province, China}.
```

第二轮
```
<think>
So, let's think about what travelers should pay attention to when visiting Mount Heng. First, consider the terrain: the stone steps are steep and may be slippery, so wear comfortable, sturdy shoes and be cautious while climbing. The area is mountainous, so weather can change quickly—bring layers and rain gear. Also, respect local customs and rules, especially around the temples and pavilions. Be prepared for physical exertion since the ascent is long. Maybe also check opening hours and plan accordingly. Plus, the natural beauty is stunning, so allow time to enjoy the scenery.  
Ultimately, the answer should cover safety, weather, physical readiness, and cultural respect.
</think>

To determine the location, observe the image's features: a steep stone pathway winding through lush green mountains, accompanied by traditional Chinese architectural elements (such as a pavilion at the top). This landscape is characteristic of **Mount Heng (Hengshan)**, one of China's Five Sacred Mountains, renowned for its ancient stone steps and mountainous terrain.  

For precautions when traveling here:  
- Wear sturdy, comfortable footwear due to the steep, uneven stone steps.  
- Prepare for physical exertion, as the ascent is long and challenging.  
- Check weather conditions in advance (mountains can have sudden weather changes) and pack appropriate clothing (layers for temperature shifts, rain gear if necessary).  
- Respect local customs and the natural environment (e.g., avoid littering, follow rules around temples/pavilions).  
- Plan your visit to allow time for the ascent/descent and to appreciate the scenic views.  

Ultimately, the answer is \boxed{Mount Heng (Hengshan), Hunan Province, China}.
```
