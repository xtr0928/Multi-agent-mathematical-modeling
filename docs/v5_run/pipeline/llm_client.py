#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 管线 LLM 客户端：四模型统一接口（DeepSeek / GLM / Kimi / Qwen）

用法：from llm_client import ask
    resp = ask('deepseek', 'system prompt', 'user prompt')            # 默认已是最强
    resp = ask('glm', system, user, reasoning='max', max_tokens=65536)

全开规格（2026-09-09 博士要求：所有模型全开 1M 上下文 + 最高推理，数模要用）：
  - 上下文：四模型均原生支持 1M tokens（模型端容量；客户端禁止任何 [:N] 截断）
      deepseek-v4-pro / glm-5.3 / kimi-k3 / qwen3.8-max
  - 推理强度：全部拉到最高档
      deepseek-v4-pro  reasoning_effort: none/minimal/low/medium/high/xhigh/max → 默认 max
      glm-5.3          reasoning_effort: low/high/max（始终思考，不支持 thinking.type=disabled）
      kimi-k3          reasoning_effort: max（始终最大强度；temperature 只允许 1.0）
      qwen3.8-max      enable_thinking=True + thinking_budget（推理过程最大 token 数）
  - 输出上限：max_tokens 默认 65536（glm 长生成 >15min 超时时按需降到 30000）
  - 超时：默认 900s（参谋组并行长任务经验值）
"""
import os, json, time
import urllib.request

def _load_env():
    env = {}
    with open('/home/zhenjinchao/.hermes/profiles/amiya/.env') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_ENV = _load_env()

# qwen3.8-max 思考预算（推理过程最大 token 数）；实测校验，若 API 拒绝则下调
QWEN_THINKING_BUDGET = 32768

CONFIG = {
    'deepseek': {
        'url': 'https://api.deepseek.com/chat/completions',
        'key': _ENV.get('DEEPSEEK_API_KEY', ''),
        'model': 'deepseek-v4-pro',        # 1M 上下文
    },
    'glm': {
        'url': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
        'key': _ENV.get('GLM_API_KEY', ''),
        'model': 'glm-5.3',                # 1M 上下文，始终思考
    },
    'kimi': {
        'url': (_ENV.get('KIMI_BASE_URL', 'https://api.moonshot.cn/v1').rstrip('/')
                + '/chat/completions'),
        'key': _ENV.get('KIMI_API_KEY', ''),
        'model': 'kimi-k3',                # 1M 上下文
    },
    'qwen': {
        'url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        'key': _ENV.get('QWEN_API_KEY', ''),
        'model': 'qwen3.8-max',            # 1M 上下文
    },
}

def ask(provider, system, user, reasoning='max', max_tokens=65536,
        temperature=0.3, timeout=900):
    """调用一个模型。默认已是最高推理档（reasoning='max'）+ 1M 上下文（不截断）。

    reasoning 取值：
      deepseek: none/minimal/low/medium/high/xhigh/max
      glm:      low/high/max
      kimi:     固定 max（传其他值也会被提升为 max）
      qwen:     布尔语义（'max'=开启思考+最大预算）
    """
    cfg = CONFIG[provider]
    payload = {
        'model': cfg['model'],
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'max_tokens': max_tokens,
        'temperature': temperature,
    }
    if provider == 'deepseek':
        payload['reasoning_effort'] = reasoning or 'max'
    elif provider == 'glm':
        payload['reasoning_effort'] = reasoning if reasoning in ('low', 'high', 'max') else 'max'
    elif provider == 'kimi':
        payload['reasoning_effort'] = 'max'   # 始终最大强度
        payload['temperature'] = 1.0          # kimi 系列只允许 temperature=1
    elif provider == 'qwen':
        payload['enable_thinking'] = True
        payload['thinking_budget'] = QWEN_THINKING_BUDGET
    req = urllib.request.Request(
        cfg['url'],
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json',
                 'Authorization': f'Bearer {cfg["key"]}'},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except Exception as e:
        return {'provider': provider, 'error': str(e), 'elapsed': round(time.time() - t0, 1)}
    msg = data['choices'][0]['message']
    out = {'provider': provider, 'content': msg.get('content', ''),
           'elapsed': round(time.time() - t0, 1)}
    rc = msg.get('reasoning_content')
    if rc:
        out['reasoning_chars'] = len(rc)
    usage = data.get('usage') or {}
    if usage:
        out['usage'] = {k: usage.get(k) for k in
                        ('prompt_tokens', 'completion_tokens',
                         'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens')
                        if usage.get(k) is not None}
    return out

if __name__ == '__main__':
    for p in ['deepseek', 'glm', 'kimi', 'qwen']:
        r = ask(p, '你是数学建模助手。', '请用一句话说明你擅长什么。')
        if 'error' in r:
            print(f'{p}: ERROR {r["error"][:160]}')
        else:
            c = (r['content'][:60] + '...') if len(r['content']) > 60 else r['content']
            rc = f' | reasoning={r.get("reasoning_chars", "N/A")} chars'
            print(f'{p}: OK {r["elapsed"]}s{rc} | {c}')
