#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 管线 LLM 客户端：DeepSeek / GLM / Kimi 三模型统一接口
用法：from llm_client import ask
resp = ask('deepseek', 'system prompt', 'user prompt', reasoning='ultra')
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

CONFIG = {
    'deepseek': {
        'url': 'https://api.deepseek.com/chat/completions',
        'key': _ENV.get('DEEPSEEK_API_KEY', ''),
        'model': 'deepseek-v4-pro',
    },
    'glm': {
        'url': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
        'key': _ENV.get('GLM_API_KEY', ''),
        'model': 'glm-4.5-air',
    },
    'kimi': {
        'url': (_ENV.get('KIMI_BASE_URL', 'https://api.moonshot.cn/v1').rstrip('/')
                + '/chat/completions'),
        'key': _ENV.get('KIMI_API_KEY', ''),
        'model': 'kimi-k3',
    },
}

def ask(provider, system, user, reasoning=None, max_tokens=16384, temperature=0.3, timeout=600):
    """调用一个模型。reasoning 仅 deepseek 支持（ultra/high）。"""
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
    if reasoning and provider == 'deepseek':
        payload['reasoning_effort'] = reasoning  # none/minimal/low/medium/high/xhigh/max
    if provider == 'kimi':
        payload['temperature'] = 1.0  # kimi 系列只允许 temperature=1
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
        return {'provider': provider, 'error': str(e), 'elapsed': time.time() - t0}
    msg = data['choices'][0]['message']
    out = {'provider': provider, 'content': msg.get('content', ''), 'elapsed': round(time.time() - t0, 1)}
    rc = msg.get('reasoning_content')
    if rc:
        out['reasoning_chars'] = len(rc)
    return out

if __name__ == '__main__':
    for p in ['deepseek', 'glm', 'kimi']:
        r = ask(p, '你是数学建模助手。', '请用一句话说明你擅长什么。', reasoning='high')
        if 'error' in r:
            print(f'{p}: ERROR {r["error"][:120]}')
        else:
            c = (r['content'][:80] + '...') if len(r['content']) > 80 else r['content']
            rc = f' | reasoning={r.get("reasoning_chars", "N/A")} chars'
            print(f'{p}: OK {r["elapsed"]}s{rc} | {c}')
