#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_figures.py — V5 论文图（matplotlib，英文标签）
fig1: 分时代回代率柱状（双路线对比）
fig2: 份额区间宽度分布（Route A CI vs Route B LP 宽度）
fig3: 四争议案例 judge vs fan rank 散点/柱
fig4: RDF α 扫描曲线（回代率 + 平台期标注）
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = '/tmp/solve_mcm2026C_v5/analysis'
FIG = '/tmp/solve_mcm2026C_v5/paper/figures'
import os
os.makedirs(FIG, exist_ok=True)

ra = json.load(open(f'{BASE}/route_a_results.json'))
rb = json.load(open(f'{BASE}/route_b_results.json'))
q2 = json.load(open(f'{BASE}/q2_compare.json'))
q4 = json.load(open(f'{BASE}/q4_new_system.json'))

plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'figure.dpi': 150})

# fig1: 分时代回代率
fig, ax = plt.subplots(figsize=(6.5, 3.2))
eras = ['percent\n(S3-27)', 'rank\n(S1-2)', 'rank+save\n(S28+)', 'All']
a_rates = [1.0, 0.7, 0.679, 0.9205]
b_rates = [1.0, None, None, None]
x = np.arange(len(eras))
w = 0.35
bars_a = ax.bar(x - w/2, [r if r else 0 for r in a_rates], w, label='Route A: max-entropy', color='#b3562e')
for xi, r in zip(x - w/2, a_rates):
    ax.text(xi, r + 0.02, f'{r*100:.1f}%', ha='center', fontsize=9)
bars_b = ax.bar(x + w/2, [1.0, 0, 0, 0], w, label='Route B: set ID (weak ID elsewhere)', color='#2f6b5e')
ax.text(x[0] + w/2, 1.02, '100%', ha='center', fontsize=9)
for xi in x[1:]:
    ax.text(xi + w/2, 0.05, 'weak ID', ha='center', fontsize=8, style='italic')
ax.set_ylabel('Replay rate')
ax.set_ylim(0, 1.15)
ax.set_xticks(x)
ax.set_xticklabels(eras)
ax.legend(fontsize=8, loc='upper right')
ax.set_title('Elimination replay by era (both routes agree where data is strong)')
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig(f'{FIG}/fig1_replay.png', bbox_inches='tight')
plt.close(fig)

# fig2: CI/LP 区间宽度分布
fig, axes = plt.subplots(1, 2, figsize=(7, 3))
w_a = [b - a for r in ra['results'] for a, b in r['ci']]
w_b = [w for r in rb['results'] for w in r['width']]
axes[0].hist(w_a, bins=30, color='#b3562e', alpha=0.8)
axes[0].axvline(np.mean(w_a), color='k', ls='--', lw=1)
axes[0].set_title(f'Route A: CI width (mean {np.mean(w_a):.2f})')
axes[1].hist(w_b, bins=30, color='#2f6b5e', alpha=0.8)
axes[1].axvline(np.mean(w_b), color='k', ls='--', lw=1)
axes[1].set_title(f'Route B: LP interval width (mean {np.mean(w_b):.2f})')
for ax in axes:
    ax.set_xlabel('width')
fig.tight_layout()
fig.savefig(f'{FIG}/fig2_width.png', bbox_inches='tight')
plt.close(fig)

# fig3: 争议案例 judge vs fan rank
cases = q2['cases']
names = list(cases.keys())
jr = [cases[n]['judge_rank'] for n in names]
fr = [cases[n]['fan_rank'] for n in names]
fig, ax = plt.subplots(figsize=(6.5, 3))
x = np.arange(len(names))
w = 0.35
ax.bar(x - w/2, jr, w, label='judge rank (lower=better)', color='#a63a2a')
ax.bar(x + w/2, fr, w, label='fan rank (lower=better)', color='#3a5a8c')
for xi, j, f in zip(x, jr, fr):
    ax.text(xi - w/2, j + 0.15, str(j), ha='center', fontsize=9)
    ax.text(xi + w/2, f + 0.15, str(f), ha='center', fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels([n.replace(' ', '\n') for n in names], fontsize=8)
ax.set_ylabel('rank in week')
ax.set_title('Controversy cases: fan support offsets judge scores (early-week snapshot)')
ax.legend(fontsize=8)
ax.invert_yaxis()
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig(f'{FIG}/fig3_cases.png', bbox_inches='tight')
plt.close(fig)

# fig4: RDF α 扫描
alphas = sorted(q4['alphas'].keys(), key=float)
rates = [q4['alphas'][a]['exact_rate'] for a in alphas]
fig, ax = plt.subplots(figsize=(6.5, 3))
ax.plot([float(a) for a in alphas], rates, 'o-', color='#6b4a8c', lw=2)
ax.axhspan(0.78, 0.83, color='#6b4a8c', alpha=0.12, label='plateau')
ax.axhline(q2['rank_rate'], color='#2f6b5e', ls='--', lw=1, label=f'rank replay ({q2["rank_rate"]*100:.1f}%)')
ax.axhline(q2['percent_rate'], color='#b3562e', ls='--', lw=1, label=f'percent replay ({q2["percent_rate"]*100:.1f}%)')
ax.set_xlabel('RDF fusion weight α (judge weight)')
ax.set_ylabel('elimination replay rate')
ax.set_title('RDF: stable over a wide α plateau')
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(f'{FIG}/fig4_rdf.png', bbox_inches='tight')
plt.close(fig)

print('4 figures saved')
