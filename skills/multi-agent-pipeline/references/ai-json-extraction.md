# _extract_json — AI API 响应 JSON 提取器

## 问题

调用 Kimi / GLM / GPT 等 LLM API 时，即使 prompt 明确要求"只返回 JSON"，模型仍可能返回：
- 空字符串
- markdown 代码块包裹（```json ... ```）
- 前后附带解释文字（"这是分析结果：{...}"）
- 纯文本而非 JSON

## 方案

三层容错提取：

```python
def _extract_json(raw: str) -> dict:
    text = raw.strip()

    # 1) 去除 markdown 代码块（```json / ```）
    for prefix in ('```json', '```'):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            if text.endswith('```'):
                text = text[:-3].strip()
            break

    # 2) 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3) 括号匹配找第一个 { } 包裹的 JSON
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0: start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try: return json.loads(text[start:i+1])
                except json.JSONDecodeError: continue
                finally: start = -1

    raise json.JSONDecodeError('No valid JSON found', text, 0)
```

## 配合 API 调用的完整模式

```python
def _call_ai(...) -> dict:
    resp = requests.post(...)
    data = resp.json()
    content = data['choices'][0]['message']['content']

    if not content:
        finish = data['choices'][0].get('finish_reason')
        if finish == 'length': raise Exception('token不足，回复被截断')
        if finish == 'content_filter': raise Exception('内容审核拦截')
        raise Exception('API 返回空内容')

    return {'content': content, ...}

# 调用处
result = _call_ai(...)
try:
    parsed = _extract_json(result['content'])
except json.JSONDecodeError:
    # 透传原始回复给用户，方便定位
    return {'found': False, 'raw_response': result['content'][:200]}
```

## 适配场景

- Kimi / GLM 视觉分析返回坐标 JSON
- 任何要求 LLM 返回结构化 JSON 的场景
- OCR 文字区域提取
