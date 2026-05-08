# BNB

:::{Note}
**支持版本：** MiniCPM-V4.5 / MiniCPM-V4.0 / MiniCPM-V2.6 / MiniCPM-V2.5
:::


## 1. 下载模型

从 [HuggingFace](https://huggingface.co/openbmb/MiniCPM-V-4_5) 下载 MiniCPM-V-4_5 模型，解压到本地目录。

## 2. 量化脚本

下方脚本会加载原始模型，使用 bitsandbytes 量化为 4-bit，并保存量化后的模型。

```python
import torch
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig
from PIL import Image
import time
import GPUtil
import os

assert torch.cuda.is_available(), "CUDA is not available, but this code requires a GPU."

device = 'cuda'  # 选择 GPU
model_path = '/model/MiniCPM-V-4_5' # 模型路径
save_path = './model/MiniCPM-V-4_5-int4' # 量化模型保存路径
image_path = './assets/airplane.jpeg'

# 量化配置
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    load_in_8bit=False,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_storage=torch.uint8,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    llm_int8_enable_fp32_cpu_offload=False,
    llm_int8_has_fp16_weight=False,
    llm_int8_skip_modules=["out_proj", "kv_proj", "lm_head"],
    llm_int8_threshold=6.0
)

tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModel.from_pretrained(
    model_path,
    device_map=device,
    quantization_config=quantization_config,
    trust_remote_code=True
)

gpu_usage = GPUtil.getGPUs()[0].memoryUsed  
start = time.time()
response = model.chat(
    image=Image.open(image_path).convert("RGB"),
    msgs=[
        {
            "role": "user",
            "content": "图中是什么？"
        }
    ],
    tokenizer=tokenizer
)
print('量化后输出：', response)
print('量化后推理耗时：', time.time() - start)
print(f"量化后 GPU 显存占用：{round(gpu_usage/1024, 2)}GB")

# 保存量化模型与 tokenizer
os.makedirs(save_path, exist_ok=True)
model.save_pretrained(save_path, safe_serialization=True)
tokenizer.save_pretrained(save_path)
```

## 3. 预期输出

量化完成后大致会看到：

```
量化后输出： The image depicts an Airbus A380-800 aircraft in mid-flight against a clear blue sky. The airplane is predominantly white with a distinctive blue tail fin featuring a red and white logo. The fuselage has the text "Airbus A380-800" written on it, and there are Chinese characters along the side of the aircraft. The landing gear is partially extended, indicating that the plane is either taking off or preparing to land. The engines are visible under the wings, and the overall design showcases the large size and advanced engineering of the Airbus A380 model.
量化后推理耗时： 9.316158771514893
量化后 GPU 显存占用：18.97GB
```

量化模型会保存到 `save_path` 指定的目录，可用于继续微调或推理。

---
要自定义模型路径、图片或保存路径，修改脚本中对应的变量即可。
