#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PHASE 4 三模型独立评审 results bundle + 投票选主线"""
import json, os, sys
sys.path.insert(0, '/tmp/solve_mcm2026C_v5/pipeline')
from llm_client import ask

BASE = '/tmp/solve_mcm2026C_v5'

def load_bundle():
    b = {}
    for f, key in [('analysis/route_a_results.json', 'route_a'),
                   ('analysis/route_b_results.json', 'route_b'),
                   ('analysis/validation_recovery.json', 'recovery'),
                   ('analysis/q2_compare.json', 'q2'),
                   ('analysis/q3_factors.json', 'q3'),
                   ('analysis/q4_new_system.json', 'q4')]:
        d = json.load(open(f'{BASE}/{f}'))
        if key == 'route_a':
            b[key] = {k: d[k] for k in ['route', 'n_elim_weeks', 'exact_count', 'exact_rate', 'mean_ci_width']}
        elif key == 'route_b':
            b[key] = {k: d[k] for k in ['route', 'n_elim_weeks', 'exact_count', 'exact_rate', 'mean_width']}
        else:
            b[key] = d
    return b

SYSTEM = """你是数学建模竞赛的评审专家。你的任务是对一份建模结果的证据包做对抗性评审。
评审原则：
1. 证据是否真的回答了赛题的四问（Q1 估计粉丝票+确定性、Q2 规则对比+争议案例、Q3 特征影响、Q4 新系统）
2. 方法论缺陷：循环验证、可识别性混淆、未检验假设
3. 两条路线（A 最大熵 vs B 集合识别）的分歧在哪、说明什么
4. 输出 JSON：{"q1_verdict": "...", "q2_verdict": "...", "q3_verdict": "...", "q4_verdict": "...",
   "critical_issues": ["..."], "route_choice": "A|B|merge", "route_reason": "...",
   "ranking": {"route_a": 0-10, "route_b": 0-10}}"""

def review_bundle():
    bundle = load_bundle()
    summary = json.dumps(bundle, ensure_ascii=False, indent=1)
    user = f"""# 赛题
2026 MCM Problem C (DWTS)：Q1 估计粉丝票（一致性与确定性）Q2 rank vs percent 对比+4 争议案例 Q3 特征影响 Q4 新系统

# 证据包
{summary[:9000]}

# 你的评审任务
按系统要求输出 JSON 评审意见。特别注意：模拟恢复实验显示回代 100% 但份额 L1 恢复仅比随机好 4.7%——这说明了什么？"""
    reviews = {}
    for provider in ['deepseek', 'glm', 'kimi']:
        print(f'[{provider}] 评审中...', flush=True)
        r = ask(provider, SYSTEM, user, reasoning='high' if provider == 'deepseek' else None,
                max_tokens=32000 if provider == 'deepseek' else 12000)
        if 'error' in r or not r.get('content'):
            print(f'[{provider}] 错误/空，重试低推理...', flush=True)
            r = ask(provider, SYSTEM, user, reasoning='low' if provider == 'deepseek' else None,
                    max_tokens=32000 if provider == 'deepseek' else 12000)
        if 'error' in r:
            reviews[provider] = {'error': r['error']}
            continue
        # 提取 JSON
        txt = r['content']
        if txt.startswith('```'):
            txt = txt.split('\n', 1)[1]
            txt = txt.rsplit('```', 1)[0] if txt.rstrip().endswith('```') else txt
        s, e = txt.find('{'), txt.rfind('}')
        parsed = json.loads(txt[s:e+1]) if s >= 0 and e > s else None
        reviews[provider] = {'content': txt, 'parsed': parsed, 'elapsed': r['elapsed']}
        with open(f'{BASE}/proposals/{provider}_review.json', 'w') as f:
            json.dump(reviews[provider], f, ensure_ascii=False, indent=1)
        print(f'[{provider}] 评审完成, parsed={"OK" if parsed else "FAIL"}', flush=True)
    # 汇总：route_choice 投票
    votes = {'A': 0, 'B': 0, 'merge': 0}
    for p, rv in reviews.items():
        if rv.get('parsed'):
            c = rv['parsed'].get('route_choice', '')
            if c in votes:
                votes[c] += 1
    summary_out = {'reviews': reviews, 'votes': votes}
    json.dump(summary_out, open(f'{BASE}/proposals/_phase4_reviews.json', 'w'),
              ensure_ascii=False, indent=1)
    print('投票:', votes)
    return summary_out

if __name__ == '__main__':
    review_bundle()
