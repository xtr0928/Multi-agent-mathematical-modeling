# LLM JSON 安全提取 (`_extract_json`)

> 适用：任何调用 LLM API 并要求 JSON 回复的场景。Kimi/Vision 模型经常在 JSON 外包 markdown 或自然语言。

## 三层容错策略

```python
def _extract_json(raw: str) -> dict:
    """从 LLM 返回的文本中提取 JSON，容错各种格式"""
    text = raw.strip()

    # 1) 去除 markdown 代码块 (```json 或 ```)
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

## 前端配合

API 收到 LLM 返回但 JSON 解析失败时，**不要只返回 "解析失败"**。把 `raw_response` 透传给前端并在 toast / console 展示前 200 字符，让用户看到 LLM 实际说了什么。

```python
except json.JSONDecodeError as e:
    raw_preview = raw[:200] if raw else '(空)'
    return {
        'found': False,
        'description': f'LLM 返回非 JSON: {raw_preview}',
        'raw_response': raw
    }
```

```javascript
toast(data.message || '未找到', true);
if (data.raw_response) console.log('LLM原始回复:', data.raw_response);
```

## Prompt 强化技巧

让 LLM 更稳定返回 JSON：

1. **system 消息**：`'你只输出 JSON，绝不输出其他内容。'`
2. **temperature=0**：消除随机性
3. **单行示例**：用紧凑 JSON 作为格式示范，减少 token 消耗
4. **结尾重述**：`现在开始分析，只返回 JSON：` — 最后一遍强调

```python
messages = [
    {'role': 'system', 'content': '你只输出 JSON，绝不输出其他内容。'},
    {'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
        {'type': 'text', 'text': '...只返回 JSON：'}
    ]}
]
result = _call_kimi(api_key, messages, temperature=0.0, max_tokens=1024)
```

## Kimi 空响应处理

`_call_kimi` 应校验响应结构，空 content 按 `finish_reason` 分类报错：

| finish_reason | 含义 | 用户提示 |
|--------------|------|---------|
| `length` | token 不足截断 | "缩小图片或简化描述" |
| `content_filter` | 内容审核拦截 | "修改描述后重试" |
| 其他 | 未知空响应 | "请重试" |
