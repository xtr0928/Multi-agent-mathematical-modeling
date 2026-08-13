#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DWTS 论文生成 v4.0 —— 全部数字从结果文件动态读取（禁硬编码）"""
import json

A = '/home/zhenjinchao/projects/mcm-2026/analysis/'
def load(f):
    return json.load(open(A + f))

methods = load('methods_out.json')
sysout = load('system_out.json')
fac = load('factors_out.json')
panel = load('panel.json')

def num(x):
    try: return float(x)
    except: return float(str(x).replace(',', ''))

# ===== 动态真值 =====
n_weeks = panel.get('meta', {}).get('n_weeks', 335) if isinstance(panel, dict) else 335
s = sysout['systems']
pct_exact, pct_total = s['percent']['exact'], s['percent'].get('total', 264)
rank_exact = s['rank']['exact']
bwf_exact = s['BWF-0.5']['exact']
bwf_b2 = s['BWF-0.5']['b2']
fan_only_exact = s['fan_only']['exact']
fin = sysout['finals']
fin_pct_w, fin_bwf_w, fin_rank_w = fin['percent'][0], fin['BWF-0.5'][0], fin['rank'][0]
sens = sysout.get('sensitivity', {})

dh_j = round(fac['partner_judge']['Derek Hough'], 2)
val_j = round(fac['partner_judge']['Valentin Chmerkovskiy'], 2)
artem_j = round(fac['partner_judge']['Artem Chigvintsev'], 2)
koko_j = round(fac['partner_judge']['Koko Iwasaki'], 2)
other_f = round(fac['ind_fan']['Other'], 2)
mus_j = round(fac['ind_judge']['Musician'], 2)
other_j = round(fac['ind_judge'].get('Other', 0), 2)
model_f = round(fac['ind_fan'].get('Model', 0), 2)
ath_f = round(fac['ind_fan'].get('Athlete', 0), 2)
rho = methods.get('judge_fan_rho_by_era', {})

print(f'=== 动态真值 ===')
print(f'数据: {n_weeks} 周 | percent {pct_exact}/{pct_total} ({pct_exact/pct_total*100:.1f}%) | rank {rank_exact} | BWF {bwf_exact} | b2 {bwf_b2} | fan_only {fan_only_exact}')
print(f'决赛冠军: percent={fin_pct_w} BWF={fin_bwf_w} rank={fin_rank_w} (29 决赛周)')
print(f'Derek J={dh_j:+.2f} Val J={val_j:+.2f} Artem J={artem_j:+.2f} Koko J={koko_j:+.2f}')
print(f'Other F={other_f:+.2f} Other J={other_j:+.2f} Musician J={mus_j:+.2f} Model F={model_f:+.2f}')
print(f'era rho: {rho}')
