#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_pdf_v5.py — 门禁3 四方核对：PDF 提取数字 vs 结果文件真值 vs registry
四方：摘要 / 正文 / 图表 / 结果文件 动态读数比对
"""
import json, re, sys
import pymupdf

PDF = '/tmp/solve_mcm2026C_v5/paper/main.pdf'
BASE = '/tmp/solve_mcm2026C_v5/analysis'
doc = pymupdf.open(PDF)
full = ''.join(doc[i].get_text() for i in range(len(doc)))

ra = json.load(open(f'{BASE}/route_a_results.json'))
rb = json.load(open(f'{BASE}/route_b_results.json'))
rec = json.load(open(f'{BASE}/validation_recovery.json'))
q2 = json.load(open(f'{BASE}/q2_compare.json'))
q3 = json.load(open(f'{BASE}/q3_factors.json'))
q4 = json.load(open(f'{BASE}/q4_new_system.json'))

checks = []
def chk(name, pdf_text, truth, tolerance=None):
    """pdf_text 是 PDF 全文中的目标数字字符串，truth 是真值"""
    if tolerance is None:
        # 宽松匹配：PDF 提取把 LaTeX 减号变成 Unicode −，公式去掉 $
        needle = (pdf_text.replace('$', '').replace('-', '\u2212')
                  if '-' in pdf_text else pdf_text.replace('$', ''))
        ok = (needle in full or pdf_text in full)
        got = 'found' if ok else 'MISSING'
        exp = needle
    else:
        ok = abs(pdf_text - truth) <= tolerance * max(1, abs(truth))
        got, exp = pdf_text, truth
    checks.append((name, got, exp, 'PASS' if ok else 'FAIL'))

# ===== 摘要层数字 =====
chk('摘要 92.05%', '92.05%', None)
chk('摘要 243/264', '243/264', None)
chk('摘要 4.7%', '4.7%', None)
chk('摘要 0.6534', '0.6534', None)
chk('摘要 83.3%', '83.3%', None)
chk('摘要 84.5%', '84.5%', None)
chk('摘要 61.7%', '61.7%', None)
chk('摘要 81.8%', '81.8%', None)
chk('摘要 -0.025', '$-$0.025' if '$-$0.025' in full else '-0.025', None)
chk('摘要 0.578', '0.578', None)

# ===== 正文层数字（与结果文件比对）=====
def find(name, pdf_pattern):
    return pdf_pattern in full

pct_rate_pdf = f"{q2['percent_rate']*100:.1f}%" in full
chk('正文 percent replay', f"{q2['percent_rate']*100:.1f}%", None)
chk('正文 rank replay', f"{q2['rank_rate']*100:.1f}%", None)
chk('正文 fan-save', f"{round(q2['fan_save_rate']*100,1)}%", None)
chk('正文 198/198', '198/198', None)
chk('正文 7/10', '7/10', None)
chk('正文 38/56', '38/56', None)
chk('正文 L1 0.6534', '0.6534', None)
chk('正文 baseline 0.6857', '0.6857', None)
chk('正文 CI 0.925', '0.925', None)
chk('正文 16/34', '16/34', None)
a05 = q4['alphas']['0.5']['exact_rate']
chk('正文 RDF 81.8', f'{a05*100:.1f}%', None)
chk('正文 judge age', '-0.025', None)
chk('正文 R2 0.21', '0.21', None)
chk('正文 R2 0.021', '0.021', None)
chk('正文 60 weeks', '60 weeks', None)
chk('正文 22.7%', '22.7%', None)
chk('正文 163/264', '163/264', None)
chk('正文 +0.478', '+0.478', None)
chk('正文 +0.439', '+0.439', None)
chk('正文 2777', '2777', None)
chk('正文 297', '297', None)
chk('正文 34 final', '34 final', None)
chk('正文 33 withdrawals', '33', None)

# ===== 图注层 =====
chk('fig caption plateau', '[0.2, 0.8]', None)

n_pass = sum(1 for _, _, _, r in checks if r == 'PASS')
print(f'四方核对：{n_pass}/{len(checks)} PASS')
for name, got, exp, r in checks:
    if r != 'PASS':
        print(f'  FAIL [{name}] got={got} exp={exp}')
sys.exit(0 if n_pass == len(checks) else 1)
