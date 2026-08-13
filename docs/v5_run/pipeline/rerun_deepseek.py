#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补跑 DeepSeek 提案（修好参数后）"""
import json, sys
sys.path.insert(0, '/tmp/solve_mcm2026C_v5/pipeline')
from llm_client import ask
from deliberator import PROBLEM, DATA_SCHEMA, SYSTEM, extract_json

user = f"""# 赛题
{PROBLEM}

# 数据结构
{DATA_SCHEMA}

# 你的任务
独立提出完整建模方案（Q1 粉丝票估计、Q2 规则对比、Q3 特征影响、Q4 新系统）。
输出 JSON（字段：q1/q2/q3/q4/overall_route，每问含 idea 思路、formulas 关键公式、solving 求解方法、validation 验证计划）。
要求：具体到公式和算法，不要泛泛而谈；特别注意可识别性分析。"""

for attempt, reasoning in [('high', 'high'), ('low', 'low')]:
    print(f'[{attempt}] 尝试中...', flush=True)
    r = ask('deepseek', SYSTEM, user, reasoning=reasoning, max_tokens=32000)
    if 'error' in r:
        print('ERROR:', r['error'][:120])
        continue
    content = r.get('content', '')
    print(f'content 长度: {len(content)}, elapsed {r["elapsed"]}s')
    if len(content) > 200:
        out = {'content': content, 'parsed': extract_json(content), 'elapsed': r['elapsed']}
        with open('/tmp/solve_mcm2026C_v5/proposals/deepseek_r1.json', 'w') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print('saved deepseek_r1.json, parsed =', 'OK' if out['parsed'] else 'FAIL')
        break
    print('内容过短，重试...')
