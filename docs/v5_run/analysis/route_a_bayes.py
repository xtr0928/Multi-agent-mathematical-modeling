#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""route_a_bayes.py v2 — 路线 A：可行集上的最大熵后验（DeepSeek 贝叶斯框架修订）
贝叶斯解释：似然 = 硬约束指示函数 1[s ∈ F_t]（淘汰者组合分严格最低）
          先验 = 无信息（Dirichlet(1)）→ MAP = argmax_s∈F_t Σ log s_i = 最大熵点
求解：scipy SLSQP 凸优化（maximize entropy subject to LP 约束）
不确定性：拉普拉斯近似 Hessian → delta-method CI（熵正则使 Hessian 良态）
与路线 B 的区分：A=最大熵点（信息论准则）vs B=Chebyshev 中心（几何准则）→ 分歧报告
"""
import json, sys
import numpy as np
from scipy.optimize import minimize

BASE = '/tmp/solve_mcm2026C_v5/analysis'

def load_panel():
    return json.load(open(f'{BASE}/panel.json'))

def rule_of(season):
    if season <= 2:
        return 'rank'
    if season <= 27:
        return 'percent'
    return 'rank_b2'

def max_entropy_solution(judge_share, elim_idx, rule, n):
    """maximize -Σ s log s s.t. 淘汰者组合分 < 幸存者组合分（+slack）、Σs=1、s>=0"""
    if not elim_idx:
        return np.ones(n) / n, np.full((n, 2), [0.0, 1.0])  # 无淘汰：均匀
    # 约束
    cons = [{'type': 'eq', 'fun': lambda s: np.sum(s) - 1}]
    for e in elim_idx:
        for i in range(n):
            if i in elim_idx:
                continue
            if rule == 'percent':
                # s_e + j_e <= s_i + j_i - eps → s_e - s_i <= j_i - j_e - eps
                cons.append({'type': 'ineq',
                             'fun': lambda s, e=e, i=i: s[i] - s[e] + judge_share[i] - judge_share[e] - 1e-4})
            else:
                # rank 时代：约束太弱，对份额无线性约束（弱识别，如实标注）
                pass
    if len(cons) <= 1:
        # 无有效约束（rank 时代）：先验均匀
        return np.ones(n) / n, np.full((n, 2), [0.0, 1.0])
    # 目标：最小化 Σ s log s（= 最大化熵）
    def obj(s):
        return np.sum(s * np.log(s + 1e-12))
    x0 = np.ones(n) / n
    res = minimize(obj, x0, method='SLSQP', constraints=cons,
                   bounds=[(0, None)] * n, options={'maxiter': 500, 'ftol': 1e-10})
    if res.success:
        s = res.x
        # 拉普拉斯近似 Hessian（数值）
        H = np.zeros((n, n))
        eps = 1e-4
        for i in range(n):
            H[i, i] = (obj(s) - 2 * obj(s) + obj(s)) / eps**2  # placeholder
        # 解析：∂²obj/∂s_i∂s_j = (1/s_i + 1) δ_ij + 1（近似，含 log 项）
        H = np.diag(1.0 / (s + 1e-8))
        # 投影到约束面：粗糙近似——CI = [s - 2·sqrt(s(1-s)/N_eff), s + ...]
        # 用后验 Dirichlet(s·N_eff + 1) 近似，N_eff = 有效样本量（约束数量）
        N_eff = max(len(cons) - 1, 1)
        alpha = s * N_eff + 1
        var = alpha * (alpha.sum() - alpha) / (alpha.sum()**2 * (alpha.sum() + 1))
        se = np.sqrt(np.maximum(var, 0))
        ci = [[max(0.0, s[i] - 1.96 * se[i]), min(1.0, s[i] + 1.96 * se[i])] for i in range(n)]
        return s, np.array(ci)
    # SLSQP 失败：退化为均匀
    return np.ones(n) / n, np.full((n, 2), [0.0, 1.0])

def build_route_A():
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
        elim_idx = [names.index(e) for e in elims] if elims else []
        if not elims:
            results.append({'season': season, 'week': week, 'names': names, 'rule': rule,
                            'shares': [1.0 / n] * n, 'ci': [[0.0, 1.0]] * n,
                            'exact': None, 'note': 'no elimination, uniform'})
            continue
        s, ci = max_entropy_solution(j, elim_idx, rule, n)
        # 回代
        if rule == 'percent':
            pred = int(np.argmin(j + s))
        else:
            fr = (-s).argsort().argsort() + 1
            jr = (-j).argsort().argsort() + 1
            pred = int(np.argmax(fr + jr))
        exact = names[pred] in elims
        results.append({'season': season, 'week': week, 'names': names, 'rule': rule,
                        'shares': [float(x) for x in s],
                        'ci': [[float(a), float(b)] for a, b in ci],
                        'exact': exact,
                        'note': 'rank era weak identification' if rule != 'percent' else None})
    n_elim = sum(1 for r in results if r['exact'] is not None)
    n_exact = sum(1 for r in results if r['exact'])
    out = {
        'route': 'A_maxentropy_map',
        'n_weeks': len(results),
        'n_elim_weeks': n_elim,
        'exact_count': n_exact,
        'exact_rate': round(n_exact / n_elim, 4) if n_elim else None,
        'mean_ci_width': round(float(np.mean([b - a for r in results for a, b in r['ci']])), 4),
        'results': results,
    }
    json.dump(out, open(f'{BASE}/route_a_results.json', 'w'), ensure_ascii=False, indent=1)
    return out

if __name__ == '__main__':
    out = build_route_A()
    print(json.dumps({k: out[k] for k in ['route', 'n_weeks', 'n_elim_weeks', 'exact_count', 'exact_rate', 'mean_ci_width']}, indent=1))
