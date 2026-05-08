# AWQ

::::{Note}
**支持版本：** MiniCPM-V 4.5
::::

## 方法 1（用预量化模型 + vLLM 推理）

### 1. 下载模型
<!-- 下载量化模型
https://huggingface.co/openbmb/MiniCPM-V-4_5-AWQ
 -->

从 [HuggingFace](https://huggingface.co/openbmb/MiniCPM-V-4_5-AWQ) 下载 AutoAWQ 量化的 4-bit MiniCPM-V-4_5 模型。

```Bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_5-AWQ
```

### 2. 用 vLLM 运行

```python
import os
from PIL import Image
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams


# 量化模型名称或本地路径
MODEL_NAME = "openbmb/MiniCPM-V-4_5-AWQ"

# 图片文件列表
IMAGES = [
    "image.png",
]

# 加载并转换图片
image = Image.open(IMAGES[0]).convert("RGB")

# 初始化 tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

# 初始化 LLM
llm = LLM(
    model=MODEL_NAME, 
    # gpu_memory_utilization=0.9,
    max_model_len=2048,
    trust_remote_code=True,
    # disable_mm_preprocessor_cache=True,
    # limit_mm_per_prompt={"image": 5}
)

# 构建消息
messages = [{
    "role": "user",
    "content": "(<image>./</image>)\n请描述这张图片的内容",
    # "content": "(<image>./</image>)\nPlease describe the content of this image",
}]

# 应用 chat template
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

# 设置 stop token IDs
stop_tokens = ['<|im_end|>', '</s>']
stop_token_ids = [tokenizer.convert_tokens_to_ids(i) for i in stop_tokens]

# 采样参数
sampling_params = SamplingParams(
    stop_token_ids=stop_token_ids,
    temperature=0.7,
    # detokenize=True,
    top_p=0.8,
    # top_k=100,
    # seed=3472,
    max_tokens=1024,
    # min_tokens=150,
)

# 推理
outputs = llm.generate({
    "prompt": prompt,
    "multi_modal_data": {
        "image": image
    }
}, sampling_params=sampling_params)
print(outputs[0].outputs[0].text)
```

## 方法 2（直接用 AWQ 量化模型推理）

### 1. 下载模型
<!-- 下载模型
https://huggingface.co/openbmb/MiniCPM-V-4_5
 -->

从 [HuggingFace](https://huggingface.co/openbmb/MiniCPM-V-4_5) 下载 MiniCPM-V 4.5 模型。

```Bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_5
```

### 2. 从源码安装 AutoAWQ
官方 AutoAWQ 仓库已不再维护，请下载并从源码安装我们的 fork。
```Bash
git clone https://github.com/tc-mb/AutoAWQ.git
cd AutoAWQ
pip install -e .
```

### 3. 推理脚本
直接使用 AWQ 量化模型推理：

```python
import os
from PIL import Image
from transformers import AutoTokenizer, TextStreamer
from awq import AutoAWQForCausalLM
import torch

# 量化模型名称或本地路径
model_path = "openbmb/MiniCPM-V-4_5-AWQ"
device = 'cuda'
# 图片文件路径
image_path = './assets/airplane.jpeg'

model = AutoAWQForCausalLM.from_quantized(model_path, trust_remote_code=True).to('cuda')
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

gpu_usage = GPUtil.getGPUs()[0].memoryUsed  
response = model.chat(
    image=Image.open(image_path).convert("RGB"),
    msgs=[
        {
            "role": "user",
            "content": "图中是什么？"
        }
    ],
    tokenizer=tokenizer
) # 模型推理

print('输出:', response)
```


## 方法 3（自己进行 AWQ 量化）

### 1. 下载模型
<!-- 下载模型
https://huggingface.co/openbmb/MiniCPM-V-4_5
 -->

从 [HuggingFace](https://huggingface.co/openbmb/MiniCPM-V-4_5) 下载 MiniCPM-V 4.5 模型。

```Bash
git clone https://huggingface.co/openbmb/MiniCPM-V-4_5
```

### 2. 从源码安装 AutoAWQ
官方 AutoAWQ 仓库已不再维护，请下载并从源码安装我们的 fork。
```Bash
git clone https://github.com/tc-mb/AutoAWQ.git
cd AutoAWQ
pip install -e .
```

### 3. 量化脚本

执行下方量化脚本（按需替换 `model_path` 和 `quant_path` 为原始模型与量化模型保存路径）：

```python
import os
from datasets import load_dataset, load_from_disk
from awq import AutoAWQForCausalLM
import torch
from transformers import AutoTokenizer
import shutil

# 原始模型路径（可以是本地路径或 HF 模型 ID）
model_path = '/openbmb/MiniCPM-V-4_5'

# 量化模型保存路径
quant_path = '/model_quantized/minicpmv4_5_awq'

# 量化配置：4-bit 权重，group size 128，GEMM 后端
quant_config = { "zero_point": True, "q_group_size": 128, "w_bit": 4, "version": "GEMM" } # "w_bit":4 or 8	


# 加载原始模型与 tokenizer
model = AutoAWQForCausalLM.from_pretrained(model_path, trust_remote_code=True, torch_dtype=torch.bfloat16)
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

# 把 model_path 中存在但 quant_path 中没有的文件复制过去（跳过权重文件）
def copy_files_not_in_B(A_path, B_path):
    """
    如果文件在 A 中存在但 B 中不存在，则从 A 拷贝到 B。

    :param A_path: 源目录 (A)
    :param B_path: 目标目录 (B)
    """
    # 确保源目录存在
    if not os.path.exists(A_path):
        raise FileNotFoundError(f"The directory {A_path} does not exist.")
    if not os.path.exists(B_path):
        os.makedirs(B_path)

    # 列出 A 中所有文件，排除权重文件 (.bin / safetensors)
    files_in_A = os.listdir(A_path)
    files_in_A = set([file for file in files_in_A if not (".bin" in file or "safetensors" in file )])
    # 列出 B 中所有文件
    files_in_B = set(os.listdir(B_path))

    # 计算需要复制的文件
    files_to_copy = files_in_A - files_in_B

    # 逐个复制
    for file in files_to_copy:
        src_file = os.path.join(A_path, file)
        dst_file = os.path.join(B_path, file)
        if os.path.isfile(src_file):
            shutil.copy2(src_file, dst_file)

# 数据加载方法
# 加载 Alpaca 数据集
def load_alpaca():
    data = load_dataset("tatsu-lab/alpaca", split="train")

    # 把每条样本转换成 chat 风格的 prompt
    def concatenate_data(x):
        if x['input'] and x['instruction']:
            msgs = [
                    {"role": "system", "content": x['instruction']},
                    {"role": "user", "content": x['input']},
                    {"role": "assistant", "content": x['output']},
            ]
        elif x['input']:
            msgs = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": x['input']},
                {"role": "assistant", "content": x['output']}
            ]
        else:
            msgs = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": x['instruction']},
                {"role": "assistant", "content": x['output']}
            ]
        
        data = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        return {"text": data}
    
    concatenated = data.map(concatenate_data)
    return [text for text in concatenated["text"]][:1024]

# 加载 Wikitext 数据集
def load_wikitext():
    data = load_dataset('wikitext', 'wikitext-2-raw-v1', split="train")
    return [text for text in data["text"] if text.strip() != '' and len(text.split(' ')) > 20]


# 加载校准数据
calib_data = load_alpaca()
# 量化
model.quantize(tokenizer, quant_config=quant_config, calib_data=calib_data)

# shutil.rmtree(quant_path, ignore_errors=True)

# 保存量化模型
model.save_quantized(quant_path)
tokenizer.save_pretrained(quant_path)

copy_files_not_in_B(model_path, quant_path)
print(f'Model is quantized and saved at "{quant_path}"')
```
