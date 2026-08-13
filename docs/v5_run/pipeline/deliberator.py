#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PHASE 2 三 Agent 商议引擎（V5 核心）
流程：三模型独立提案 → 交换批评 → 各自修订 → 汇总
产物：proposals/{deepseek,glm,kimi}_r1.json, critiques.json, _r2.json, deliberation.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import ask

BASE = '/tmp/solve_mcm2026C_v5'
os.makedirs(f'{BASE}/proposals', exist_ok=True)

PROBLEM = open(f'{BASE}/analysis/c_problem.txt').read()
DATA_SCHEMA = """数据列（53 列，421 行）：
celebrity_name, ballroom_partner, celebrity_industry, celebrity_homestate,
celebrity_homecountry/region, celebrity_age_during_season, season, results, placement,
week1_judge1_score .. week11_judge4_score（44 列评委分，每季最多 11 周）
注意：无粉丝票列（粉丝票是保密未知量）；results 列含淘汰信息；placement 列含决赛名次。"""

SYSTEM = """你是数学建模竞赛（MCM）的顶级建模手。你的任务是针对给定赛题提出完整的建模方案。
要求：
1. 只给思路和模型，禁止给代码
2. 每个问题（Q1-Q4）给出：建模思路、关键公式、求解方法、验证计划
3. 特别注意可识别性（哪些量可估计、哪些不可）、验证方案（如何证明模型正确）
4. 输出 JSON 格式：{"q1": {...}, "q2": {...}, "q3": {...}, "q4": {...}, "overall_route": "一句话总结你的技术路线"}
5. 深度推理，不要套模板——针对这道题的独特结构设计"""

def extract_json(text):
    """从模型输出提取 JSON（容忍 markdown 围栏）"""
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        if text.rstrip().endswith('```'):
            text = text.rsplit('```', 1)[0]
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            return None
    return None

def round1():
    """三模型独立提案"""
    user = f"""# 赛题
{PROBLEM}

# 数据结构
{DATA_SCHEMA}

# 你的任务
独立提出完整建模方案（Q1 粉丝票估计、Q2 规则对比、Q3 特征影响、Q4 新系统）。
输出 JSON（字段：q1/q2/q3/q4/overall_route，每问含 idea 思路、formulas 关键公式、solving 求解方法、validation 验证计划）。"""
    results = {}
    for provider in ['deepseek', 'glm', 'kimi']:
        print(f'[{provider}] 独立提案中...', flush=True)
        r = ask(provider, SYSTEM, user, reasoning='high' if provider == 'deepseek' else None,
                max_tokens=32000 if provider == 'deepseek' else 12000)
        if 'error' in r or not r.get('content'):
            # 空内容（reasoning 吃光预算）→ 重试一次，降低 reasoning
            print(f'[{provider}] 空输出/错误，重试（reasoning=low）...', flush=True)
            r = ask(provider, SYSTEM, user, reasoning='low' if provider == 'deepseek' else None,
                    max_tokens=32000 if provider == 'deepseek' else 12000)
        if 'error' in r:
            print(f'[{provider}] ERROR: {r["error"][:100]}', flush=True)
            results[provider] = {'error': r['error']}
            continue
        parsed = extract_json(r['content'])
        out = {'content': r['content'], 'parsed': parsed, 'elapsed': r['elapsed']}
        results[provider] = out
        with open(f'{BASE}/proposals/{provider}_r1.json', 'w') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f'[{provider}] 完成 {r["elapsed"]}s, parsed={"OK" if parsed else "FAIL"}', flush=True)
    return results

def round_critique(results):
    """交换批评：每个模型看到其他两方案，写批评"""
    critiques = {}
    for provider in ['deepseek', 'glm', 'kimi']:
        others = {p: results[p]['content'][:6000] for p in results if p != provider}
        user = f"""以下是另外两个独立建模手的方案。请针对它们写出尖锐批评（JSON 格式，按 q1-q4 组织）：
=== 方案 1 ===
{others.get('deepseek', '（无）')}
=== 方案 2 ===
{others.get('glm', '（无）')}
=== 方案 3 ===
{others.get('kimi', '（无）')}

批评要点：可识别性问题、循环验证风险、基线缺失、求解可行性、验证方案缺陷。
输出 JSON：{{"critiques": [{{"target": "deepseek|glm|kimi", "issue": "...", "severity": "critical|major|minor", "suggestion": "..."}}]}}"""
        print(f'[{provider}] 写批评中...', flush=True)
        r = ask(provider, '你是数学建模评审专家，职责是找出方案的方法论缺陷。', user,
                reasoning='high' if provider == 'deepseek' else None, max_tokens=16000)
        if 'error' in r:
            critiques[provider] = {'error': r['error']}
            continue
        critiques[provider] = {'content': r['content'],
                               'parsed': extract_json(r['content'])}
        with open(f'{BASE}/proposals/{provider}_critique.json', 'w') as f:
            json.dump(critiques[provider], f, ensure_ascii=False, indent=1)
        print(f'[{provider}] 批评完成', flush=True)
    return critiques

def round2(results, critiques):
    """各自修订（回应批评）"""
    revised = {}
    for provider in ['deepseek', 'glm', 'kimi']:
        crit_text = critiques.get(provider, {}).get('content', '（无批评）')[:5000]
        user = f"""你之前的方案：
{results[provider]['content'][:6000]}

其他模型对你的批评：
{crit_text}

请修订你的方案：逐条回应批评（接受并修改 / 拒绝并说明理由），输出修订后的完整方案（JSON，字段同第一轮）。"""
        print(f'[{provider}] 修订中...', flush=True)
        r = ask(provider, SYSTEM, user, reasoning='high' if provider == 'deepseek' else None,
                max_tokens=32000 if provider == 'deepseek' else 12000)
        if 'error' in r:
            revised[provider] = {'error': r['error']}
            continue
        revised[provider] = {'content': r['content'], 'parsed': extract_json(r['content'])}
        with open(f'{BASE}/proposals/{provider}_r2.json', 'w') as f:
            json.dump(revised[provider], f, ensure_ascii=False, indent=1)
        print(f'[{provider}] 修订完成', flush=True)
    return revised

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='r1', choices=['r1', 'critique', 'r2'])
    args = parser.parse_args()
    if args.stage == 'r1':
        res = round1()
        json.dump(res, open(f'{BASE}/proposals/_round1.json', 'w'), ensure_ascii=False, indent=1)
    elif args.stage == 'critique':
        res = json.load(open(f'{BASE}/proposals/_round1.json'))
        crits = round_critique(res)
        json.dump(crits, open(f'{BASE}/proposals/_critiques.json', 'w'), ensure_ascii=False, indent=1)
    elif args.stage == 'r2':
        res = json.load(open(f'{BASE}/proposals/_round1.json'))
        crits = json.load(open(f'{BASE}/proposals/_critiques.json'))
        rev = round2(res, crits)
        json.dump(rev, open(f'{BASE}/proposals/_round2.json', 'w'), ensure_ascii=False, indent=1)
