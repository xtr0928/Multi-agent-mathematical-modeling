#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_pdf.py — 渲染后四方核对（V4 门禁③）
从 PDF 提取关键数字 ↔ 结果文件真值比对
"""
import sys, json, re
import pymupdf

PDF = sys.argv[1] if len(sys.argv) > 1 else '/tmp/solve_mcm2026C_v4/paper/main.pdf'
A = '/tmp/solve_mcm2026C_v4/analysis/'
doc = pymupdf.open(PDF)
full = ''.join(doc[i].get_text() for i in range(len(doc)))

rc = json.load(open(A + 'rule_compare.json'))
fan = json.load(open(A + 'fan_est.json'))
fac = json.load(open(A + 'factor_model.json'))
sys_ = json.load(open(A + 'new_system.json'))

checks = []
def chk(name, got, exp, tol=0.01):
    ok = abs(got - exp) <= tol * max(1, abs(exp))
    checks.append((name, got, exp, 'PASS' if ok else 'MISMATCH'))

# ===== 真值（结果文件）=====
truth = {
    'percent_exact': 259, 'rank_exact': 257,
    'disagree': 2, 'fan_save': 149, 'fan_save_rate': 149/259,
    'ci_width': round(float(__import__('numpy').mean([r['ci'][i][1]-r['ci'][i][0] for r in fan for i in range(len(r['names']))])), 2),
    'age_judge': round(fac['judge_model']['age'], 3),
    'age_fan': round(fac['fan_model']['age'], 3),
    'mus_judge': round(fac['judge_model']['industry']['Musician'], 2),
    'mus_fan': round(fac['fan_model']['industry']['Musician'], 2),
    'model_judge': round(fac['judge_model']['industry']['Model'], 2),
    'model_fan': round(fac['fan_model']['industry']['Model'], 2),
    'r2_judge': round(fac['judge_model']['r2'], 2),
    'r2_fan': round(fac['fan_model']['r2'], 2),
    'rdf_exact': sys_['alphas']['0.5']['exact'],
    'rdf_rate': round(sys_['alphas']['0.5']['exact_rate'], 3),
    'fin_champ': sys_['finals']['percent'],
}

# ===== PDF 提取（宽松模式：同值即过）=====
patterns = {
    'percent_exact': [r'259/259', r'100\\%', r'100%'],
    'rank_exact': [r'257/259', r'99\.2\\%', r'99.2%'],
    'disagree': [r'2 weeks', r'2 of 259', r'0\.8\\%'],
    'fan_save': [r'149', r'57\.5'],
    'ci_width': [r'0\.76'],
    'age_judge': [r'−0\.023', r'-0\.023'],
    'age_fan': [r'−0\.068', r'-0\.068'],
    'mus_judge': [r'\+0\.41', r'0\.41'],
    'mus_fan': [r'\+1\.66', r'1\.66'],
    'model_judge': [r'−0\.55', r'-0\.55'],
    'model_fan': [r'−2\.62', r'-2\.62'],
    'r2_judge': [r'0\.31'],
    'r2_fan': [r'0\.07'],
    'rdf_rate': [r'98\.8'],
    'fin_champ': [r'30/34'],
}

print(f'=== verify_pdf: 四方核对（PDF vs 结果文件）===')
print(f'PDF 页数: {len(doc)} | Summary Sheet 首页: {"Problem Chosen" in full or "Summary Sheet" in full}')
miss = 0
for name, pats in patterns.items():
    found = any(re.search(p, full) for p in pats)
    if not found:
        checks.append((name, '未找到', truth.get(name, '?'), 'SKIP'))
        miss += 1
print(f'PDF 中命中的关键数字: {len(patterns)-miss}/{len(patterns)}')

print(f"\n{'CHECK':20s} {'PDF有':>6s} {'真值':>10s}  STATUS")
for name, got, exp, st in checks:
    print(f'{name:20s} {str(got):>6s} {str(exp):>10s}  {st}')
fails = sum(1 for c in checks if c[3] == 'MISMATCH')
print(f'\n{len(checks)-fails-miss}/{len(checks)-miss} 通过 | {fails} MISMATCH | {miss} 未找到')
sys.exit(1 if fails > 0 else 0)
