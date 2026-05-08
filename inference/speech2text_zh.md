# 语音转文本

### 加载模型

```python
import torch
import librosa
from transformers import AutoModel, AutoTokenizer

model_path = 'openbmb/MiniCPM-o-2_6'
model = AutoModel.from_pretrained(model_path, trust_remote_code=True,
                                  # sdpa 或 flash_attention_2，不要用 eager
                                  attn_implementation='sdpa', torch_dtype=torch.bfloat16)
model = model.eval().cuda()
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

model.init_tts()
model.tts.float()
```

### 使用示例

<audio controls>
  <source src="./assets/recongize.wav" type="audio/wav">
  example audio case
</audio>

```python
audio_input, _ = librosa.load('./assets/recongize.wav', sr=16000, mono=True)
msgs = [{'role': 'user', 'content': [audio_input]}]
res = model.chat(
    msgs=msgs,
    image=None,
    tokenizer=tokenizer,
    sampling=True,
    max_new_tokens=4096,
    use_tts_template=True,
    temperature=0.3,
    generate_audio=True,
)

print("asr 结果:", res)
```

### 示例输出

```
asr 结果: 你好！我是MiniCPM 3 Omni，由面壁智能科技有限责任公司研发。我今天能为你提供什么帮助？
```
