#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""route_b_ident.py — 路线 B：集合识别（Kimi 提案）
(A) 确定层：LP 可行集 → 每选手×周份额可行区间 + Chebyshev 中心（最大裕度点）
(B) 概率层：可行集内均匀后验的均值/SD（简化版层级贝叶斯）
可识别性：只有份额可识别；淘汰者上界；无淘汰周不可识别；拯救时代约束最弱
"""
import json, sys
import numpy as np
from scipy.optimize import linprog

BASE = '/tmp/solve_mcm2026C_v5/analysis'

def load_panel():
    return json.load(open(f'{BASE}/panel.json'))

def rule_of(season):
    if season <= 2:
        return 'rank'
    if season <= 27:
        return 'percent'
    return 'rank_b2'

def chebyshev_center(A_ub, b_ub, A_eq=None, b_eq=None, slack=1e-4):
    """max 裕度点：max r s.t. A_ub x + r·norm(A_ub) <= b_ub, Σx=1, x>=r"""
    n = A_ub.shape[1]
    # vars: x (n) + r (1)
    c = np.zeros(n + 1)
    c[n] = -1  # 最大化 r
    # 约束: A_ub x + ||A_ub_i|| r <= b_ub_i
    A = np.zeros((A_ub.shape[0], n + 1))
    A[:, :n] = A_ub
    A[:, n] = np.linalg.norm(A_ub, axis=1)
    res = linprog(c, A_ub=A, b_ub=b_ub,
                  A_eq=np.hstack([np.ones((1, n)), [[0]]]) if A_eq is None else A_eq,
                  b_eq=np.ones(1) if b_eq is None else b_eq,
                  bounds=[(0, None)] * n + [(None, None)],
                  method='highs')
    if res.success:
        return res.x[:n], res.x[n]
    return None, None

def build_route_B():
    panel = load_panel()
    results = []
    for ev in panel['events']:
        season, week = ev['season'], ev['week']
        names = ev['names']
        n = len(names)
        j = np.array(ev['judge_sums'], dtype=float)
        j = j / j.sum()
        elims = ev['elims']
        rule = rule_of(season)
        if not elims:
            results.append({'season': season, 'week': week, 'names': names, 'rule': rule,
                            'center': [1.0 / n] * n, 'lo': [0.0] * n, 'hi': [1.0] * n,
                            'width': [1.0] * n, 'exact': None,
                            'note': 'no elimination, unidentifiable'})
            continue
        e_idx = [names.index(e) for e in elims]
        # 约束：每个淘汰者的组合分 < 每个幸存者的组合分
        rows, bs = [], []
        for ei in e_idx:
            for si in range(n):
                if si in e_idx:
                    continue
                row = np.zeros(n)
                if rule == 'percent':
                    # j[ei] + s[ei] < j[si] + s[si]  →  s[ei] - s[si] < j[si] - j[ei]
                    row[ei] = 1
                    row[si] = -1
                    bs.append(j[si] - j[ei] - 1e-4)
                else:
                    # rank 时代约束太弱（仅序关系），对份额不加约束 → 只留归一化
                    # 说明：rank 时代份额弱识别（Kimi 提案可识别性结论 ⑤）
                    continue
                rows.append(row)
        # 归一化 + 非负
        if rule == 'percent' and rows:
            A_ub = np.array(rows)
            b_ub = np.array(bs)
            center, r = chebyshev_center(A_ub, b_ub, slack=1e-4)
            # 区间：对每个选手单独 min/max s_i
            lo, hi = [], []
            for i in range(n):
                cmin = np.zeros(n); cmin[i] = 1
                r1 = linprog(cmin, A_ub=A_ub, b_ub=b_ub,
                             A_eq=np.ones((1, n)), b_eq=[1],
                             bounds=[(0, None)] * n, method='highs')
                cmax = -cmin
                r2 = linprog(cmax, A_ub=A_ub, b_ub=b_ub,
                             A_eq=np.ones((1, n)), b_eq=[1],
                             bounds=[(0, None)] * n, method='highs')
                lo.append(r1.x[i] if r1.success else 0.0)
                hi.append(-r2.fun if r2.success else 1.0)
            if center is None:
                center = [(a + b) / 2 for a, b in zip(lo, hi)]
            width = [h - l for l, h in zip(lo, hi)]
            # 回代：中心点组合分最低者 = 淘汰者
            ccomb = j + np.array(center)
            pred = names[int(np.argmin(ccomb))]
            exact = pred in elims
            results.append({'season': season, 'week': week, 'names': names, 'rule': rule,
                            'center': [float(x) for x in center],
                            'lo': [float(x) for x in lo], 'hi': [float(x) for x in hi],
                            'width': [float(x) for x in width], 'exact': exact})
        else:
            # rank 时代或无约束：均匀先验
            results.append({'season': season, 'week': week, 'names': names, 'rule': rule,
                            'center': [1.0 / n] * n, 'lo': [0.0] * n, 'hi': [1.0] * n,
                            'width': [1.0] * n, 'exact': None,
                            'note': 'rank era: weak identification (order only)'})
    n_elim = sum(1 for r in results if r['exact'] is not None)
    n_exact = sum(1 for r in results if r['exact'])
    out = {
        'route': 'B_set_identification',
        'n_weeks': len(results),
        'n_elim_weeks': n_elim,
        'exact_count': n_exact,
        'exact_rate': round(n_exact / n_elim, 4) if n_elim else None,
        'mean_width': round(float(np.mean([w for r in results for w in r['width']])), 4),
        'results': results,
    }
    json.dump(out, open(f'{BASE}/route_b_results.json', 'w'), ensure_ascii=False, indent=1)
    return out

if __name__ == '__main__':
    out = build_route_B()
    print(json.dumps({k: out[k] for k in ['route', 'n_weeks', 'n_elim_weeks', 'exact_count', 'exact_rate', 'mean_width']}, indent=1))
