# 视觉定位 Grounding

## 示例代码

```python
import re
from PIL import Image, ImageDraw
import torch
from transformers import AutoModel, AutoTokenizer

def setup_model_and_tokenizer(model_path):
    dtype = torch.bfloat16
    model = AutoModel.from_pretrained(model_path, torch_dtype=dtype, trust_remote_code=True)
    model = model.to(dtype=torch.bfloat16)
    model = model.eval().cuda()
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    return model, tokenizer

def extract_bbox_from_response(response):
    match = re.search(r"<box>([\d\s]+)</box>", response)
    if match:
        bbox_str = match.group(1)
        bbox = list(map(int, bbox_str.strip().split()))
        return bbox
    else:
        raise ValueError("Can't find bbox in response")

def draw_bbox_on_image(image, bbox):
    w, h = image.size
    x1 = int(bbox[0] / 1000 * w)
    y1 = int(bbox[1] / 1000 * h)
    x2 = int(bbox[2] / 1000 * w)
    y2 = int(bbox[3] / 1000 * h)
    draw = ImageDraw.Draw(image)
    draw.rectangle([x1, y1, x2, y2], outline="red", width=4)
    return image

def model_infer_and_draw(img_path, question, model, tokenizer):
    image = Image.open(img_path)
    msgs = [
        {'role': 'user', 'content': [question, image]},
    ]
    with torch.inference_mode():
        res = model.chat(
            image=None,
            msgs=msgs,
            tokenizer=tokenizer,
            sampling=True,
            max_new_tokens=1024,
            max_inp_length=8192,
            use_image_id=True,
        )
    print("模型输出:", res)
    bbox = extract_bbox_from_response(res)
    image_with_box = draw_bbox_on_image(image, bbox)
    return res, bbox, image_with_box

model_path = 'openbmb/MiniCPM-V-4_5'
img_path = './assets/airplane.jpeg'
question = 'Please provide the bounding box coordinate of the region this sentence describes: <ref>airplane</ref>'

model, tokenizer = setup_model_and_tokenizer(model_path)
res, bbox, image_with_box = model_infer_and_draw(img_path, question, model, tokenizer)

out_path = './assets/airplane_grounding.jpeg'
image_with_box.save(out_path)
```

## 效果展示

### 飞机

```python
model_path = 'openbmb/MiniCPM-V-4_5'
device = 'cuda'
img_path = './assets/airplane.jpeg'
question = 'Please provide the bounding box coordinate of the region this sentence describes: <ref>airplane</ref>'

model, tokenizer = setup_model_and_tokenizer(model_path, device)
res, bbox, image_with_box = model_infer_and_draw(img_path, question, model, tokenizer)

out_path = './assets/airplane-grounding.jpeg'
image_with_box.save(out_path)
```

原图：
![alt text](./assets/airplane.jpeg)

定位后：
![alt text](./assets/airplane-grounding.jpeg)

### 哆啦 A 梦

```python
model_path = 'openbmb/MiniCPM-V-4_5'
device = 'cuda'
img_path = './assets/doraemon.jpeg'
question = 'Please provide the bounding box coordinate of the region this sentence describes: <ref>doraemon</ref>'

model, tokenizer = setup_model_and_tokenizer(model_path, device)
res, bbox, image_with_box = model_infer_and_draw(img_path, question, model, tokenizer)

out_path = './assets/doraemon-grounding.jpeg'
image_with_box.save(out_path)
```

原图：
![alt text](./assets/doraemon.jpg)

定位后：
![alt text](./assets/doraemon-grounding.jpg)

### 多目标

```python
import re
from PIL import Image, ImageDraw
import torch
from transformers import AutoModel, AutoTokenizer
import json
def setup_model_and_tokenizer(model_path):
    dtype = torch.bfloat16
    model = AutoModel.from_pretrained(model_path, torch_dtype=dtype, trust_remote_code=True)
    model = model.to(dtype=torch.bfloat16)
    model = model.eval().cuda()
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    return model, tokenizer

def extract_bbox_from_json_response(response):
    response_json = json.loads(response)
    bbox_list = []
    name_list = []
    for item in response_json:
        bbox_str = item.get("box", "")
        # 去掉可能存在的 "<box>" / "</box>"
        bbox_str = re.sub(r"</?box>", "", bbox_str)
        name_list.append((item.get("name_en", ""), item.get("name_zh", "")))
        bbox = list(map(int, bbox_str.strip().split()))
        bbox_list.append(bbox)
    return bbox_list, name_list

def draw_multiple_bboxes_on_image(image, bbox_list, name_list):
    w, h = image.size
    draw = ImageDraw.Draw(image)
    for bbox, names in zip(bbox_list, name_list):
        x1 = int(bbox[0] / 1000 * w)
        y1 = int(bbox[1] / 1000 * h)
        x2 = int(bbox[2] / 1000 * w)
        y2 = int(bbox[3] / 1000 * h)
        draw.rectangle([x1, y1, x2, y2], outline="red", width=4)
        draw.text((x1, y1 - 10), f"{names[0]} / {names[1]}", fill="red")
    return image

def model_infer_and_draw(img_path, question, model, tokenizer):
    image = Image.open(img_path)
    msgs = [
        {'role': 'user', 'content': [question, image]},
    ]
    with torch.inference_mode():
        res = model.chat(
            image=None,
            msgs=msgs,
            tokenizer=tokenizer,
            sampling=True,
            max_new_tokens=1024,
            max_inp_length=8192,
            use_image_id=True,
        )
    print("模型输出:", res)
    bbox, name_list = extract_bbox_from_json_response(res)
    image_with_box = draw_multiple_bboxes_on_image(image, bbox, name_list)
    return res, bbox, image_with_box

model_path = 'openbmb/MiniCPM-V-4_5'
img_path = '/cache/liuqilin/draft/example/qwen2v4_5/assets/doraemon.jpg'
question = 'Identify all characters in the image and return their bounding boxes and English name and Chinese name in JSON format, a list of {"name_en": "Doraemon", "name_zh": "哆啦A梦","box", "x1 y1 x2 y2"}'

model, tokenizer = setup_model_and_tokenizer(model_path)
res, bbox, image_with_box = model_infer_and_draw(img_path, question, model, tokenizer)

out_path = './assets/doraemon_multi_grounding.jpg'
image_with_box.save(out_path)
```

原图：
![alt text](./assets/doraemon.jpg)

定位后：
![alt text](./assets/doraemon_multi_grounding.jpg)
