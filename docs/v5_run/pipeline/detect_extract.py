#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""detect_extract.py — 检测层：三模型独立抽取 PDF 数值声明 vs registry
目的：①registry 里的声明 PDF 里都能找到（一致性）②PDF 里的关键数值声明
是否全被 registry 覆盖（漏注册检测）
"""
import json, sys
import pymupdf
sys.path.insert(0, '/tmp/solve_mcm2026C_v5/pipeline')
from llm_client import ask

PDF = '/tmp/solve_mcm2026C_v5/paper/main.pdf'
BASE = '/tmp/solve_mcm2026C_v5/analysis'
doc = pymupdf.open(PDF)
full_text = ''.join(doc[i].get_text() for i in range(len(doc)))
reg = json.load(open(f'{BASE}/claims_registry.json'))['claims']

SYSTEM = """你是论文数值声明抽取器。从给定论文文本中抽取所有带具体数字的关键声明。
输出 JSON：{"claims": [{"predicate": "简短标识", "value": 数字或字符串, "section_hint": "上下文片段"}]}
规则：只抽取有具体数值的声明（百分比、计数、系数、区间宽度）；不要改写数字。"""

def extract_one(provider):
    # 论文 15 页全文约 25KB 字符，取前 18000 字符（主体内容）
    user = f"论文全文（前 18000 字符）：\n{full_text[:18000]}"
    r = ask(provider, SYSTEM, user, reasoning='high' if provider == 'deepseek' else None,
            max_tokens=32000 if provider == 'deepseek' else 12000)
    if 'error' in r or not r.get('content'):
        r = ask(provider, SYSTEM, user, max_tokens=32000 if provider == 'deepseek' else 12000)
    txt = r.get('content', '')
    if txt.startswith('```'):
        txt = txt.split('\n', 1)[1]
        txt = txt.rsplit('```', 1)[0] if txt.rstrip().endswith('```') else txt
    s, e = txt.find('{'), txt.rfind('}')
    try:
        return json.loads(txt[s:e+1]).get('claims', [])
    except Exception:
        return []

if __name__ == '__main__':
    results = {}
    for p in ['deepseek', 'glm', 'kimi']:
        claims = extract_one(p)
        results[p] = claims
        print(f'[{p}] 抽取 {len(claims)} 条声明')
        for c in claims[:3]:
            print(f"  - {c.get('predicate','?')}: {c.get('value','?')}")
    json.dump(results, open(f'{BASE}/extraction_3models.json', 'w'), ensure_ascii=False, indent=1)
    # 并集覆盖检查：registry 中的关键值是否被至少一个模型抽出
    union_values = set()
    for p, claims in results.items():
        for c in claims:
            v = str(c.get('value', ''))
            if v:
                union_values.add(v)
    reg_vals = [str(c['value']) for c in reg]
    missed = [v for v in reg_vals if v not in union_values and v not in full_text]
    print(f'registry 值被三模型并集覆盖: {len(reg_vals) - len(missed)}/{len(reg_vals)}')
    print('完成')
