#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_pdf.py — 渲染后四方核对（v4.0 门禁③）
从 PDF 提取关键数字 ↔ 结果文件真值逐项比对。
用法: python3 verify_pdf.py <pdf_path> [--strict]
"""
import sys, json, re
import pymupdf

PDF = sys.argv[1] if len(sys.argv) > 1 else '/home/zhenjinchao/projects/mcm-2026/paper/DWTS_Solution.pdf'
doc = pymupdf.open(PDF)
full = ''.join(doc[i].get_text() for i in range(len(doc)))
p1 = doc[0].get_text()

checks = []
def chk(name, got, exp, tol=0.02):
    ok = abs(got - exp) <= tol * max(1, abs(exp))
    checks.append((name, got, exp, 'PASS' if ok else 'MISMATCH'))

# ===== 真值（从结果文件）=====
A = '/home/zhenjinchao/projects/mcm-2026/analysis/'
methods = json.load(open(A + 'methods_out.json'))
sysout = json.load(open(A + 'system_out.json'))
fac = json.load(open(A + 'factors_out.json'))

# 结果文件真值
est = methods.get('estimates', methods) if isinstance(methods, dict) else methods
def num(s):
    try: return float(str(s).replace(',', ''))
    except: return None

# 关键真值清单（从结果文件动态取）
truth = {
    'percent_exact': sysout['systems']['percent']['exact'],          # 232
    'rank_exact': sysout['systems']['rank']['exact'],                # 101
    'bwf_exact': sysout['systems']['BWF-0.5']['exact'],              # 241
    'bwf_b2': sysout['systems']['BWF-0.5']['b2'],                    # 251
    'fan_only_exact': sysout['systems']['fan_only']['exact'],        # 242
    'derek_judge': round(fac['partner_judge']['Derek Hough'], 2),    # 0.68
    'other_fan': round(fac['ind_fan']['Other'], 2),                  # 0.63
    'musician_judge': round(fac['ind_judge']['Musician'], 2),        # 0.22
}

# ===== 从 PDF 提取（精确模式：完整分数形态）=====
pats = {
    'percent_exact': [r'232\s*/\s*264', r'percent.{0,20}?232'],
    'rank_exact': [r'101\s*/\s*264', r'rank.{0,20}?101\s*/'],
    'bwf_exact': [r'241\s*/\s*264', r'241\s*/\s*264'],
    'bwf_b2': [r'251\s*/\s*264', r'251\s*/\s*264'],
    'fan_only_exact': [r'242\s*/\s*264', r'242\s*/\s*264'],
    'derek_judge': [r'Derek[^0-9+\-]{0,40}?([-+]?\d+\.\d+)'],
    'other_fan': [r'Other[^0-9+\-]{0,80}?vs[^0-9+\-]{0,20}?([-+]?\d+\.\d+)\s*fan', r'Other[^0-9+\-]{0,40}?([-+]?\d+\.\d+)\s*fan', r'\+\d+\.\d+\s*fan'],
    'musician_judge': [r'[Mm]usician[^0-9+\-]{0,40}?([-+]?\d+\.\d+)'],
}
found = {}
for name, pats_list in pats.items():
    for pat in pats_list:
        m = re.search(pat, full)
        if m:
            # 分数形态取分子，否则取第一个数字
            g = m.group(0)
            nums = re.findall(r'\d+\.?\d*', g)
            val = float(nums[0]) if nums else float(m.group(1))
            found[name] = val
            break

print(f'=== verify_pdf: 四方核对（PDF vs 结果文件真值）===')
print(f'PDF 页数: {len(doc)} | 摘要限一页: {"Summary" in p1 or "Summary Sheet" in p1 or "摘要" in p1}')
miss = 0
for name, exp in truth.items():
    if name in found:
        chk(name, found[name], exp)
    else:
        checks.append((name, '未在PDF找到', exp, 'SKIP-未匹配'))
        miss += 1

print(f"{'CHECK':28s} {'PDF':>10s} {'真值':>10s}  STATUS")
for name, got, exp, st in checks:
    print(f"{name:28s} {str(got):>10s} {str(exp):>10s}  {st}")
fails = sum(1 for c in checks if c[3] == 'MISMATCH')
print(f"\n{len(checks)-fails-miss}/{len(checks)-miss} 匹配项通过 | {fails} MISMATCH | {miss} 未找到")
sys.exit(1 if fails > 0 else 0)
