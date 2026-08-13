#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_registry.py — 从结果文件生成 claims registry（V5 注册表驱动写作）
每条声明：predicate/value/scope/provenance（file+key，行级溯源）
"""
import json, sys
sys.path.insert(0, '/tmp/solve_mcm2026C_v5/pipeline')
from claims_registry import Registry

BASE = '/tmp/solve_mcm2026C_v5/analysis'

ra = json.load(open(f'{BASE}/route_a_results.json'))
rb = json.load(open(f'{BASE}/route_b_results.json'))
rec = json.load(open(f'{BASE}/validation_recovery.json'))
q2 = json.load(open(f'{BASE}/q2_compare.json'))
q3 = json.load(open(f'{BASE}/q3_factors.json'))
q4 = json.load(open(f'{BASE}/q4_new_system.json'))
panel = json.load(open(f'{BASE}/panel.json'))

r = Registry()

def reg(section, predicate, value, vd, scope, file, key):
    r.add(section=section, predicate=predicate, value=value, value_display=vd,
          scope=scope, provenance={'file': file, 'key': key})

# Q1 数据规模
reg('2.1', 'n_seasons', 34, '34 seasons', {'population': 'all'},
    'analysis/panel.json', 'stats.n_seasons')
reg('2.1', 'n_celebrities', 421, '421 celebrities', {'population': 'all'},
    'analysis/panel.json', 'stats.n_celebrities')
reg('2.2', 'n_elim_events', 297, '297 elimination events', {'population': '含退赛'},
    'analysis/panel.json', 'stats.n_elim_events')
reg('2.2', 'n_panel_rows', 2777, '2777 celebrity-week rows', {'population': 'all'},
    'analysis/panel.json', 'stats.n_panel_rows')

# Q1 路线 A（主线）
reg('3.1', 'route_a_exact_rate', 0.9205, '92.05% (243/264)', {'era': 'all', 'route': 'A'},
    'analysis/route_a_results.json', 'exact_rate')
reg('3.1', 'route_a_pct_exact', 1.0, '100% (198/198)', {'era': 'percent', 'route': 'A'},
    'analysis/route_a_results.json', 'exact_rate')
reg('3.1', 'route_a_ci_width', 0.5775, '0.578 mean CI width', {'era': 'all', 'route': 'A'},
    'analysis/route_a_results.json', 'mean_ci_width')
# Q1 路线 B（互证）
reg('3.2', 'route_b_pct_exact', 1.0, '100% (198/198)', {'era': 'percent', 'route': 'B'},
    'analysis/route_b_results.json', 'exact_rate')
reg('3.2', 'route_b_width', 0.9252, '0.925 mean interval width', {'era': 'percent', 'route': 'B'},
    'analysis/route_b_results.json', 'mean_width')

# Q1 模拟恢复实验（验证产物）
reg('4.1', 'recovery_l1', 0.6534, 'L1 0.6534 vs random 0.6857 (improve 4.7%)',
    {'n_active': 8, 'n_weeks': 200}, 'analysis/validation_recovery.json', 'share_l1_mean')
reg('4.1', 'recovery_replay', 1.0, '100% replay (construct artifact)',
    {'n_active': 8}, 'analysis/validation_recovery.json', 'replay_rate')

# Q2
reg('5.1', 'q2_pct_rate', round(q2['percent_rate'], 4), f"{q2['percent_exact']}/{q2['n_elim_weeks']} percent replay",
    {'rule': 'percent', 'all_weeks': True}, 'analysis/q2_compare.json', 'percent_rate')
reg('5.1', 'q2_rank_rate', round(q2['rank_rate'], 4), f"{q2['rank_exact']}/{q2['n_elim_weeks']} rank replay",
    {'rule': 'rank', 'all_weeks': True}, 'analysis/q2_compare.json', 'rank_rate')
reg('5.2', 'q2_disagree', q2['disagree_weeks'], f"{q2['disagree_weeks']} disagree weeks",
    {'rule': 'both'}, 'analysis/q2_compare.json', 'disagree_weeks')
reg('5.3', 'fan_save_rate', round(q2['fan_save_rate'], 4),
    f"{round(q2['fan_save_rate']*100, 1)}% ({q2['fan_save_count']}/{q2['n_judge_worst']})",
    {'population': 'all elim weeks'}, 'analysis/q2_compare.json', 'fan_save_rate')

# Q3
reg('6.1', 'age_judge_coef', round(q3['judge_model']['age'], 3), f"judge age coef {round(q3['judge_model']['age'], 3)}",
    {'model': 'judge_z'}, 'analysis/q3_factors.json', 'judge_model.age')
reg('6.1', 'age_fan_coef', round(q3['fan_model']['age'], 3), f"fan age coef {round(q3['fan_model']['age'], 3)}",
    {'model': 'logit_share'}, 'analysis/q3_factors.json', 'fan_model.age')
reg('6.1', 'r2_judge', round(q3['judge_model']['r2'], 3), f"judge R2 {round(q3['judge_model']['r2'], 3)}",
    {'model': 'judge_z'}, 'analysis/q3_factors.json', 'judge_model.r2')

# Q4
a05 = q4['alphas']['0.5']
reg('7.1', 'rdf_exact_rate', round(a05['exact_rate'], 4),
    f"{round(a05['exact_rate']*100, 1)}% ({a05['exact']}/{a05['n']})",
    {'alpha': 0.5}, 'analysis/q4_new_system.json', 'alphas.0.5.exact_rate')
reg('7.2', 'final_pct_champ', q4['finals']['percent'],
    f"{q4['finals']['percent']}/34 final champion match (percent)",
    {'rule': 'percent', 'note': '决赛周份额不可识别'}, 'analysis/q4_new_system.json', 'finals.percent')

issues, n = r.check()
path = r.save(f'{BASE}/claims_registry.json')
print(f'注册 {n} 条声明 → {path}')
print(f'冲突检测：{len(issues)} 个问题')
for it in issues:
    print(f"  [{it['rule']}] {it['msg']}")
