# BNB

:::{Note}
**Support:** MiniCPM-V 4.6 / MiniCPM-V 4.5 / MiniCPM-V 4.0 / MiniCPM-V 2.6 / MiniCPM-V 2.5
:::

## 1. Download the Model

Download the MiniCPM-V-4_6 model from [HuggingFace](https://huggingface.co/openbmb/MiniCPM-V-4_6) (or `openbmb/MiniCPM-V-4_6-Thinking` for the think variant) and extract it to a local directory.

## 2. Quantization Script

The following script loads the original model, quantizes it to 4-bit using bitsandbytes, runs a sanity-check inference, and saves the quantized model.

> Requires `transformers>=5.7.0` (where MiniCPM-V 4.6 is registered as a standalone architecture).

```python
import os
import time
import torch
from transformers import (
    AutoProcessor,
    AutoModelForImageTextToText,
    BitsAndBytesConfig,
)
from PIL import Image

assert torch.cuda.is_available(), "CUDA is not available, but this code requires a GPU."

device = "cuda"
model_path = "/model/MiniCPM-V-4_6"  # Original model path
save_path = "./model/MiniCPM-V-4_6-int4"  # Path to save quantized model
image_path = "./assets/airplane.jpeg"

# 4-bit quantization configuration
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    load_in_8bit=False,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_storage=torch.uint8,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    llm_int8_enable_fp32_cpu_offload=False,
    llm_int8_has_fp16_weight=False,
    llm_int8_skip_modules=["lm_head"],
    llm_int8_threshold=6.0,
)

processor = AutoProcessor.from_pretrained(model_path)
model = AutoModelForImageTextToText.from_pretrained(
    model_path,
    device_map=device,
    quantization_config=quantization_config,
)

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
).to(model.device)

start = time.time()
out_ids = model.generate(**inputs, max_new_tokens=256)
response = processor.decode(
    out_ids[0][inputs["input_ids"].shape[-1]:],
    skip_special_tokens=True,
)

print("Output after quantization:", response)
print("Inference time after quantization:", time.time() - start)

# Save the quantized model and tokenizer/processor
os.makedirs(save_path, exist_ok=True)
model.save_pretrained(save_path, safe_serialization=True)
processor.save_pretrained(save_path)
```

## 3. Expected Output

After quantization you should see something like:

```text
Output after quantization: The image depicts an Airbus A380-800 aircraft in mid-flight against a clear blue sky. The airplane is predominantly white with a distinctive blue tail fin featuring a red and white logo. ...
Inference time after quantization: ~9 s on a single A100/4090
```

The quantized model will be saved at `save_path` and can be reloaded with `AutoModelForImageTextToText.from_pretrained(save_path)` for further inference or fine-tuning.

---
To customize the model path, image, or save path, edit the variables at the top of the script.
