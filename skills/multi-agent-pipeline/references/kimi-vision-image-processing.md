# Kimi Vision API 图像处理模式

## 背景

Moonshot 的 Kimi 模型（kimi-k2.6 / moonshot-v1-8k-vision-preview）支持视觉理解。
可用于：根据自然语言描述定位图中区域、OCR 文字识别、色卡文字-色块配对。

## API 关键信息

- **Base URL**: `https://api.moonshot.cn/v1`
- **视觉模型**: `moonshot-v1-8k-vision-preview`（支持图片输入）
- **认证**: `Authorization: Bearer sk-xxxx`
- **计费**: 按 token 计，图片按分辨率折算 token（~85 tokens per 512x512 tile）

## 图像编码

```python
import base64
from io import BytesIO
from PIL import Image

def encode_image(image: Image.Image, max_size: int = 1024) -> str:
    """缩放到 max_size，JPEG 85% 质量，返回 base64 data URL"""
    img = image.copy()
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.convert('RGB').save(buf, format='JPEG', quality=85)
    return base64.b64encode(buf.getvalue()).decode('utf-8')
```

**注意事项**：
- 图片缩放很关键——原图太大 Kimi 响应慢且 token 消耗暴增；1024px 日常够用，2048px 用于 OCR
- 必须 convert('RGB') 去掉 alpha 通道再存 JPEG；否则 4 通道图会报错
- 用 `data:image/jpeg;base64,{b64}` 格式传入 message content

## 三种取色模式

### 模式一：AI 视觉定位

让 Kimi 根据自然语言描述找出区域坐标：

```python
prompt = f"""请分析这张图片，找到图中"{description}"的位置。
图片尺寸为 {w}x{h} 像素。坐标原点在左上角。
用 JSON 返回：{{"found": true, "region": {{"x":0,"y":0,"w":100,"h":100}}, "confidence": "high"}}
找不到返回：{{"found": false, "reason": "..."}}
只返回 JSON，不要有其他文字。"""
```

**关键 prompt 技巧**：
- 必须告知图片尺寸（`{w}x{h}`），否则 Kimi 可能返回归一化坐标
- 强调"只返回 JSON"防止 markdown 包裹（` ```json ... ``` `）
- temperature=0.1 保证坐标稳定
- 坐标返回后必须 clamp 到图片边界内

### 模式二：OCR 文字识别

识别图中文字并返回位置：

```python
prompt = f"""请对这张图片进行 OCR 文字识别。图片尺寸为 {w}x{h} 像素。
识别所有可见文字，给出每个文字区块的内容和像素坐标。
JSON 格式：{{"text_regions": [{{"text":"...", "region":{{"x":...,"y":...,"w":...,"h":...}}, "confidence":0.95}}], "full_text":"..."}}"""
```

### 模式三：色卡文字-色块配对

用于调色板/色卡图片——找到文字标注对应的颜色样本区域：

```python
prompt = f"""请分析这张色卡图片。找到所有文字标注和对应的颜色色块位置。
特别关注与 "{text_query}" 相关的条目。
JSON：{{"entries": [{{"label":"颜色名", "text_region":{{...}}, "swatch_region":{{...}}, "matched":true}}]}}"""
```

## 响应解析

Kimi 经常在 JSON 外加 markdown 标记：

```python
content = result['choices'][0]['message']['content']
content = content.strip()
if content.startswith('```'):
    content = content.split('\n', 1)[-1]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()
parsed = json.loads(content)
```

## 成本优化

| 策略 | 效果 |
|------|------|
| 图片缩小到 1024px | token 减少 60-70% |
| temperature=0.1 + max_tokens=512 | 推理快，响应短 |
| 单次请求同时做多件事 | 减少请求次数 |
| 缓存识别结果 | 避免重复请求 |

## 与 Hermes 集成

使用 `kimi-ocr` profile（kimi-k2.6）做推理/分析，`kimi-coder`（kimi-k2.7）只做编码。

```bash
# 通过 hermes -p kimi-ocr 调用视觉分析
hermes -p kimi-ocr chat -q "分析这张图..."
```

但实测中，通过 Python requests 直接调 Moonshot API 更可控（base64 传图、解析 JSON 响应），不需要走 hermes agent 层。

---

## 进阶：通用 JSON 提取器（2026-07-11 新增）

Kimi 经常不按指令返回纯 JSON，可能夹杂 markdown、解释文字、或完全返回自然语言。用三层容错提取：

```python
def _extract_json(raw: str) -> dict:
    """从 Kimi 返回的文本中提取 JSON"""
    text = raw.strip()

    # 第1层：去 markdown 代码块 (```json 或 ```)
    for prefix in ('```json', '```'):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            if text.endswith('```'):
                text = text[:-3].strip()
            break

    # 第2层：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 第3层：括号匹配——从文本中找第一个 { } 包裹的 JSON
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    continue
                finally:
                    start = -1

    raise json.JSONDecodeError('No valid JSON found', text, 0)
```

**用法**：所有 Kimi 调用都用这个解析，替换原来的手动 strip + json.loads。

---

## 进阶：API 调用错误透传（2026-07-11 新增）

**问题**：Kimi 返回 200 但 content 为空、或被截断、或被审核拦截时，旧代码会掉到 JSON 解析失败，用户看到模糊的"解析失败"而非真实原因。

**修复**：在 `_call_kimi` 内检查响应结构：

```python
def _call_kimi(api_key, messages, ...) -> dict:
    resp = requests.post(...)

    if resp.status_code != 200:
        err = resp.json().get('error', {}).get('message', resp.text[:200])
        raise Exception(f'Kimi API 错误 ({resp.status_code}): {err}')

    data = resp.json()
    choices = data.get('choices', [])
    if not choices:
        raise Exception('Kimi 返回空响应（未生成任何内容）')

    msg = choices[0].get('message', {})
    content = (msg.get('content') or '').strip()
    finish = choices[0].get('finish_reason', 'unknown')

    if not content:
        if finish == 'length':
            raise Exception('Kimi 回复被截断（token 不足），请缩小图片或简化描述')
        elif finish == 'content_filter':
            raise Exception('Kimi 内容审核拦截，请修改描述后重试')
        else:
            raise Exception(f'Kimi 返回空内容（finish_reason={finish}），请重试')

    return {'content': content, 'finish_reason': finish}
```

**调用方简化为**：`content = result['content']`（而非 `result['choices'][0]['message']['content']`）

---

## 进阶：强制 JSON 输出的 Prompt（2026-07-11 新增）

**问题**：用户输入"手套"，Kimi 有时返回自然语言"我看到了红色手套在..."而非 JSON 坐标。

**修复要点**：
1. 加 `system` 角色消息强调身份："你是一个精确的图像坐标分析器。你只输出 JSON，绝不输出其他内容。"
2. `temperature=0.0`（不是 0.1）——需要最高确定性
3. `max_tokens=1024`（不是 512）——给坐标留够空间
4. 在 prompt 中给出**一行紧凑 JSON 示例**，而非多行格式
5. `found=false` 也用一行紧凑 JSON 示例

```python
prompt = f"""你是一个图像分析专家。请精确分析这张 {w}x{h} 像素的图片。
任务：找到图中"{description}"的精确像素位置。

⚠️ 严格规则：
- 必须只返回纯 JSON，不能有任何解释、前缀或后缀
- 坐标原点在左上角，x向右，y向下
- 所有数字必须是整数

正确格式示例：
{{"found":true,"description":"红色手套在画面左下方","region":{{"x":120,"y":380,"w":80,"h":60}},"confidence":"high"}}
{{"found":false,"reason":"未在图片中发现{description}"}}

现在开始分析，只返回 JSON："""

messages = [
    {'role': 'system', 'content': '你是一个精确的图像坐标分析器。你只输出 JSON，绝不输出其他内容。'},
    {'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
        {'type': 'text', 'text': prompt}
    ]}
]
```
