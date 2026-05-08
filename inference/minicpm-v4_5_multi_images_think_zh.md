# 多图问答（思考模式）

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
# question = 'Compare the two images, tell me about the differences between them.'

msgs = [{'role': 'user', 'content': [image1, image2, question]}]

answer = model.chat(
    image=None,
    msgs=msgs,
    tokenizer=tokenizer,
    enable_thinking=True
)
print(answer)
```

### 第二轮对话

```python
# 第二轮对话，带上多轮历史上下文
msgs.append({"role": "assistant", "content": [answer]})
msgs.append({"role": "user", "content": ["告诉我它们的相似之处。"]})
# msgs.append({"role": "user", "content": ["Tell me about the similarities between them."]})
answer = model.chat(
    image=None,
    msgs=msgs,
    tokenizer=tokenizer,
    enable_thinking=True
)
print(answer)
```

### 示例图片

![alt text](./assets/multi1.png)

![alt text](./assets/multi2.png)

### 示例输出

#### 中文回答

第一轮

```
<think>
那么，让我们从分析每个花瓶的细节开始。首先看第一个花瓶（the first image）：它是一个白色底色的葫芦形花瓶，上面有红色的图案。图案包括人物和云朵，可能还有植物或花卉元素。形状是经典的葫芦形，上下两个球体。

第二个花瓶（the second image）：也是葫芦形，但颜色和图案不同。它有绿色、蓝色、红色和橙色的多彩图案。上半部分有绿色图案，带有红色和橙色的圆形元素。下半部分有绿色藤蔓和花卉设计，更复杂。颜色更丰富，图案种类更多。

所以不同点包括：颜色（第一个是单一红色，第二个是多种颜色：绿、蓝、红、橙）、图案主题（第一个有红色人物和云朵，第二个有绿色藤蔓、花卉和不同形状）、整体设计风格（第一个更简洁的红色图案，第二个更多彩且复杂的图案）。
</think>

要比较这两张图片，可以观察以下不同之处：  

1. **颜色方案**：第一个花瓶（the first image）主要是白色底色，上面有红色图案。第二个花瓶（the second image）有绿色、蓝色、红色和橙色等多种颜色的图案。  

2. **图案设计**：第一个花瓶的图案包括红色的人物、云朵和植物等元素。第二个花瓶的图案包括绿色藤蔓、花卉、几何形状（如圆形）和不同的装饰元素，整体设计更复杂且色彩丰富。  

3. **视觉风格**：第一个花瓶的图案更简约、单色（红色在白色上），而第二个花瓶的图案更复杂、多元（多种颜色和更精致的细节）。  


简而言之，不同之处在于颜色方案（第一个是红色，第二个是多种颜色）、图案主题（第一个有红色人物/云朵，第二个有绿色藤蔓/花卉/几何形状）以及整体设计风格（第一个更简约，第二个更复杂）。
```

第二轮

```
<think>
明白了，让我们找出它们的相似之处。首先，观察两个花瓶的形状。两者的形状都是双球体（gourd-shaped），由一个较细的上部（neck）和一个较宽的底部（bulbous body）组成。颜色方案？等等，第一个是白色底色上有红色图案，第二个是白色底色上有多种颜色的图案，但它们都是白色底色。等等，是形状吗？是的，形状都是"葫芦形"或双球体花瓶。图案的分布方式？两者都有复杂的装饰图案，覆盖了花瓶的表面。材质？看起来都是陶瓷，可能是瓷器。等等，形状：都是gourd-shaped（双球体），一个较细的上部和一个较宽的底部。颜色方面，都是白色底色，但第一个是红色图案，第二个是多种颜色。但它们都具有双球体形状。图案：两者都有装饰图案，覆盖了花瓶的表面。材质：都是陶瓷。总结相似点：都具有双球体（葫芦形）形状，都有装饰图案，材质可能是瓷器（或类似的陶瓷），都是花瓶。让我们再确认一下。形状：两者的形状都是gourd-shaped（双球体），一个较细的上部和一个较宽的底部。颜色：都是白色底色，尽管第一个是红色图案，第二个是多种颜色，但底色都是白色。图案：两者都有复杂的装饰图案，覆盖了花瓶的表面。材质：看起来都是陶瓷（瓷器）。

因此，它们的相似之处：两者都是双球体花瓶（gourd-shaped），都有装饰图案，材质可能是瓷器或类似的陶瓷，形状都具有类似的葫芦形结构，都用于装饰（花瓶）。
</think>

它们的相似之处：  
- 形状：两者都是双球体（葫芦形）花瓶，由一个较细的上部和一个较宽的底部组成。  
- 材质：都看起来是陶瓷（可能是瓷器），有白色底色。  
- 功能：两者都作为装饰花瓶使用。  
- 装饰：都具有复杂的表面图案，虽然图案设计和颜色不同，但都覆盖了花瓶的表面。
```

#### English Answer

First Round

```
<think>
So, let's analyze the two images. First, look at the colors: the first vase (the first image) is red and white, while the second one (the second image) is green, blue, and maybe other colors. Then check the patterns: the first has red cloud-like designs and possibly figures, the second has green floral patterns and different motifs. Also, the shapes might be similar (gourd-shaped) but the decoration styles are different. Wait, the first image's vase has red on white, the second uses green, blue, red, and other colors. The patterns are different too. Let me list the differences:

1. Color scheme: the first image is predominantly red on white, the second is green, blue, and multicolor with floral and geometric patterns.
2. Design patterns: the first has cloud motifs and maybe mythical figures in red, the second has floral designs with green vines, blue borders, and different symbols.
3. Overall style: the first appears to be a classic red-decorated porcelain, the second has a more colorful and possibly multi-colored palette with intricate floral arrangements.
</think>

To compare the two images, we analyze the following differences:  

1. **Color Scheme**:  
   - The first vase  features a monochromatic red design on a white background.  
   - The second vase  uses a multicolored palette, including green, blue, and red, with intricate floral and geometric patterns.  

2. **Design Motifs**:  
   - The first vase displays red cloud-like patterns and what appears to be a central figure (possibly a mythical or historical character) surrounded by red clouds.  
   - The second vase has green vine-like patterns, blue decorative elements, and multicolored floral designs (e.g., red, orange flowers with green leaves) arranged in vertical bands.  

3. **Overall Aesthetic Style**:  
   - The first vase has a more traditional, single-color red-and-white aesthetic typical of certain classical porcelain styles.  
   - The second vase exhibits a vibrant, multi-color decorative style with complex floral and symbolic motifs, reflecting a different artistic tradition.  


These differences highlight variations in color, pattern complexity, and design themes between the two vases.
```

Second Round

```
<think>
To identify the similarities between the two vases, let's analyze their shared features:

1. **Shape and Form**:  
   Both vases have a distinctive double-gourd (or gourd-shaped) silhouette, with a narrower neck and a bulbous, rounded body that tapers into a smaller upper section. This classic gourd shape is a common design element in traditional porcelain.

2. **Material and Finish**:  
   Both appear to be made of porcelain, characterized by their smooth, glossy white backgrounds. This indicates a high-quality ceramic material typical of fine Chinese vases.

3. **Decorative Style**:  
   Each vase features intricate, hand-painted patterns. The first vase uses a red monochromatic design, while the second uses multiple colors. Despite the difference in color schemes, both vases exhibit detailed, artisanal decoration, showcasing skilled craftsmanship.

4. **Cultural Context**:  
   The gourd shape and elaborate painted designs suggest both are influenced by traditional Chinese ceramic art, where such forms and decorative themes are prevalent.

These similarities highlight their shared cultural roots, material quality, and artistic tradition, even as they differ in color and specific motifs.
```
