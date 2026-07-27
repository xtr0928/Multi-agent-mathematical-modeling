# Flask 大文件上传 + Kimi API 集成模式

## Flask 大图上传防爆

```python
from flask import Flask
from PIL import Image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
Image.MAX_IMAGE_PIXELS = 100_000_000                  # 1亿像素上限

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': '文件过大，最大支持 200MB'}), 413

def save_upload(file, max_dim=4096):
    file.save(path)
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        img.save(path, quality=90)  # 覆盖原文件
    return img.convert('RGBA')
```

**关键点**：
- `MAX_CONTENT_LENGTH` 在 `app.config` 里设，不是全局常量
- PIL 像素上限直接设 `Image.MAX_IMAGE_PIXELS`
- 413 handler 返回 JSON（前端 fetch 才能解析）
- `Image.open()` 是惰性加载，不会立即解码大图，`convert()` 才会

## Kimi / Moonshot API 错误处理

**反模式**：直接 `return resp.json()` 然后上层解析 → 错误信息丢失

**正确模式**：API 调用层就做结构校验，抛明确的异常

```python
def _call_kimi(api_key, messages):
    resp = requests.post(url, headers=..., json=..., timeout=60)
    
    if resp.status_code != 200:
        err = resp.json().get('error', {}).get('message', resp.text[:200])
        raise Exception(f'Kimi API 错误 ({resp.status_code}): {err}')
    
    data = resp.json()
    choices = data.get('choices', [])
    if not choices:
        raise Exception('Kimi 返回空响应')
    
    content = (choices[0]['message'].get('content') or '').strip()
    finish = choices[0].get('finish_reason', 'unknown')
    
    if not content:
        if finish == 'length':
            raise Exception('回复被截断（token 不足）')
        elif finish == 'content_filter':
            raise Exception('内容审核拦截')
        else:
            raise Exception(f'空内容 (finish={finish})')
    
    return {'content': content, 'finish_reason': finish}
```

## Kimi 返回 JSON 的三层容错提取

Kimi 经常不按 prompt 要求返回纯 JSON，需要三层处理：

```python
def _extract_json(raw):
    text = raw.strip()
    
    # 1) 去 markdown 代码块（```json / ```）
    for prefix in ('```json', '```'):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            if text.endswith('```'):
                text = text[:-3].strip()
            break
    
    # 2) 直接解析
    try: return json.loads(text)
    except: pass
    
    # 3) 括号匹配找第一个 {...}
    depth = 0; start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0: start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try: return json.loads(text[start:i+1])
                except: continue
                start = -1
    
    raise json.JSONDecodeError('No valid JSON found', text, 0)
```

## numpy 除零警告

`np.where(cond, a, b)` 会**先求值 a 和 b 两个分支**，即使 cond 全 False。当 `a` 包含除法时，即使被 mask 掉也会触发 RuntimeWarning：

```python
# ❌ 错误：diff=0 的像素也会计算 除以 diff
h = np.where(mask & (max_rgb == r), ((g - b) / diff) % 6, h)

# ✅ 正确：用 safe_diff 替换掉零值
safe_diff = np.where(diff < 1e-10, 1.0, diff)
h = np.where(mask & (max_rgb == r), ((g - b) / safe_diff) % 6, h)
```
