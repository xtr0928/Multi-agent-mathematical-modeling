#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""q2_q3_q4.py — Q2 规则对比 + Q3 因素模型 + Q4 新系统（基于路线 A 份额）
Q2: 同一份额回放 rank vs percent → 分歧周数、fan-save、争议案例
Q3: 双因变量回归（评委分 / logit 份额）→ 特征影响对比
Q4: RDF 稳健双融合新系统 + α 扫描
"""
import json
import numpy as np
import pandas as pd

BASE = '/tmp/solve_mcm2026C_v5/analysis'

def load():
    ra = json.load(open(f'{BASE}/route_a_results.json'))
    panel = json.load(open(f'{BASE}/panel.json'))
    df = pd.read_csv(f'{BASE}/2026_MCM_Problem_C_Data.csv', encoding='utf-8-sig')
    return ra, panel, df

def rule_of(season):
    if season <= 2:
        return 'rank'
    if season <= 27:
        return 'percent'
    return 'rank_b2'

def q2_compare(ra, panel):
    """全周反事实回放"""
    # share_map: 淘汰周优先（route_a 记录无 elims 字段，elims 从 panel join）
    share_map = {}
    for r in ra['results']:
        key = f"{r['season']}|{r['week']}"
        ev = next((e for e in panel['events']
                   if e['season'] == r['season'] and e['week'] == r['week']), None)
        has_elim = bool(ev and ev['elims'])
        if key in share_map and not has_elim:
            continue
        share_map[key] = (dict(zip(r['names'], r['shares'])), r['names'])
    n_pct_ok = n_rank_ok = 0
    disagree = 0
    fan_saves = 0
    n_jw = 0
    cases = {}
    for ev in panel['events']:
        key = f"{ev['season']}|{ev['week']}"
        if key not in share_map:
            continue
        sm, names = share_map[key]
        elims = ev['elims']
        if not elims:
            continue
        j = np.array(ev['judge_sums'], dtype=float)
        j = j / j.sum()
        s = np.array([sm.get(nm, 0.0) for nm in names])
        # percent 回放
        comb_p = j + s
        pred_p = names[int(np.argmin(comb_p))]
        ok_p = pred_p in elims
        # rank 回放
        fr = (-s).argsort().argsort() + 1
        jr = (-j).argsort().argsort() + 1
        rr = fr + jr
        pred_r = names[int(np.argmax(rr))]
        ok_r = pred_r in elims
        n_pct_ok += int(ok_p)
        n_rank_ok += int(ok_r)
        if pred_p != pred_r:
            disagree += 1
        # fan-save：judge 最差者没被淘汰
        jw = names[int(np.argmin(j))]
        if jw not in elims:
            fan_saves += 1
        n_jw += 1
        # 争议案例
        for nm in ['Jerry Rice', 'Billy Ray Cyrus', 'Bristol Palin', 'Bobby Bones']:
            if nm in names:
                i = names.index(nm)
                cases.setdefault(nm, {'season': ev['season'], 'week': ev['week'],
                                      'judge_rank': int(jr[i]),
                                      'fan_rank': int(fr[i]),
                                      'eliminated': nm in elims,
                                      'survives_p': nm not in elims and pred_p == nm})
    n_elim_weeks = sum(1 for ev in panel['events'] if ev['elims'])
    out = {
        'percent_exact': n_pct_ok, 'percent_rate': round(n_pct_ok / n_elim_weeks, 4),
        'rank_exact': n_rank_ok, 'rank_rate': round(n_rank_ok / n_elim_weeks, 4),
        'n_elim_weeks': n_elim_weeks,
        'disagree_weeks': disagree,
        'fan_save_count': fan_saves,
        'fan_save_rate': round(fan_saves / n_jw, 4),
        'n_judge_worst': n_jw,
        'cases': cases,
    }
    json.dump(out, open(f'{BASE}/q2_compare.json', 'w'), ensure_ascii=False, indent=1)
    return out

def q3_factors(ra, panel, df):
    """双因变量：judge_z（每周评委标准化分）与 logit_share（份额 logit）"""
    rows = []
    feat = df.set_index('celebrity_name')
    for ev in panel['events']:
        j = np.array(ev['judge_sums'], dtype=float)
        if len(j) < 2:
            continue
        jz = (j - j.mean()) / (j.std() + 1e-9)
        for i, nm in enumerate(ev['names']):
            if nm not in feat.index:
                continue
            r = feat.loc[nm]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            age = r['celebrity_age_during_season']
            ind = str(r['celebrity_industry'])
            if pd.isna(age) or age == '':
                continue
            # 份额（从路线 A）
            sm = dict(zip(ev['names'],
                          next(x['shares'] for x in ra['results']
                               if x['season'] == ev['season'] and x['week'] == ev['week']
                               and nm in x['names'])))
            share = max(min(sm[nm], 1 - 1e-6), 1e-6)
            rows.append({'season': ev['season'], 'week': ev['week'], 'name': nm,
                         'age': float(age), 'industry': ind,
                         'judge_z': float(jz[i]),
                         'logit_share': float(np.log(share / (1 - share)))})
    d = pd.DataFrame(rows)
    d['age2'] = d['age'] ** 2
    # 周内标准化：logit_share 与 judge_z 都是周内相对量，先周内 demean 再回归
    d['judge_z'] = d.groupby(['season', 'week'])['judge_z'].transform(lambda x: x - x.mean())
    d['logit_share'] = d.groupby(['season', 'week'])['logit_share'].transform(lambda x: x - x.mean())
    # 行业哑变量（出现次数>=30 的行业）
    top_ind = d['industry'].value_counts()
    top_ind = top_ind[top_ind >= 30].index
    for ind in top_ind:
        d[f'ind_{ind}'] = (d['industry'] == ind).astype(float)
    def ols(yvar, xvars):
        X = d[['age', 'age2', 'season', 'week']].astype(float).copy()
        for ind in top_ind:
            X[f'ind_{ind}'] = d[f'ind_{ind}']
        y = d[yvar].values
        Xm = np.column_stack([np.ones(len(X)), X.values.astype(float)])
        beta, *_ = np.linalg.lstsq(Xm, y, rcond=None)
        yhat = Xm @ beta
        ss_res = np.sum((y - yhat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot
        return {'age': float(beta[1]), 'age2': float(beta[2]),
                'r2': float(r2), 'n': len(y),
                'industry': {ind: float(beta[5 + k]) for k, ind in enumerate(top_ind)}}
    judge_m = ols('judge_z', ['age', 'age2', 'industry', 'season', 'week'])
    fan_m = ols('logit_share', ['age', 'age2', 'industry', 'season', 'week'])
    out = {'judge_model': judge_m, 'fan_model': fan_m, 'n_rows': len(d)}
    json.dump(out, open(f'{BASE}/q3_factors.json', 'w'), ensure_ascii=False, indent=1)
    return out

def q4_new_system(ra, panel):
    """RDF 稳健双融合：z_judge/z_fan 的 MAD 标准化 + α 加权"""
    share_map = {}
    for r in ra['results']:
        key = f"{r['season']}|{r['week']}"
        ev = next((e for e in panel['events']
                   if e['season'] == r['season'] and e['week'] == r['week']), None)
        has_elim = bool(ev and ev['elims'])
        if key in share_map and not has_elim:
            continue
        share_map[key] = (dict(zip(r['names'], r['shares'])), r['names'])
    alphas = ['0.2', '0.3', '0.4', '0.5', '0.6', '0.7', '0.8']
    results = {a: {'exact': 0, 'n': 0} for a in alphas}
    finals = {'percent': 0, 'rdf': 0, 'n': 0}
    n_elim_weeks = 0
    for ev in panel['events']:
        key = f"{ev['season']}|{ev['week']}"
        if key not in share_map:
            continue
        sm, names = share_map[key]
        elims = ev["elims"]
        if not elims:
            continue
        n_elim_weeks += 1
        j = np.array(ev['judge_sums'], dtype=float)
        jp = j / j.sum()
        s = np.array([sm.get(nm, 0.0) for nm in names])
        jz = (jp - np.median(jp)) / (np.median(np.abs(jp - np.median(jp))) + 1e-9)
        ls = np.log(np.maximum(s, 1e-6) / (1 - np.maximum(s, 1 - 1e-6)))
        fz = (ls - np.median(ls)) / (np.median(np.abs(ls - np.median(ls))) + 1e-9)
        for astr in alphas:
            a = float(astr)
            comb = a * jz + (1 - a) * fz
            pred = names[int(np.argmin(comb))]
            results[astr]['n'] += 1
            results[astr]['exact'] += int(pred in elims)
    for f in panel['finals']:
        key = f"{f['season']}|{f['week']}"
        if key not in share_map:
            continue
        sm, names = share_map[key]
        j = np.array(f['judge_sums'], dtype=float)
        jp = j / j.sum()
        s = np.array([sm.get(nm, 0.0) for nm in names])
        jz = (jp - np.median(jp)) / (np.median(np.abs(jp - np.median(jp))) + 1e-9)
        ls = np.log(np.maximum(s, 1e-6) / (1 - np.maximum(s, 1 - 1e-6)))
        fz = (ls - np.median(ls)) / (np.median(np.abs(ls - np.median(ls))) + 1e-9)
        champ = f['champion']
        # 冠军 = 组合分最高者（1st place）；决赛周份额不可识别（无淘汰约束，均匀）→ 诚实标注
        pred_p = names[int(np.argmax(jp + s))]
        finals['percent'] += int(pred_p in champ)
        # RDF 冠军（α=0.5）：同样取最高
        comb = 0.5 * jz + 0.5 * fz
        pred_r = names[int(np.argmax(comb))]
        finals['rdf'] += int(pred_r in champ)
        finals['n'] += 1
    out = {
        'alphas': {a: {'exact': v['exact'], 'n': v['n'],
                       'exact_rate': round(v['exact'] / v['n'], 4)} for a, v in results.items()},
        'finals': finals,
        'n_elim_weeks': n_elim_weeks,
    }
    json.dump(out, open(f'{BASE}/q4_new_system.json', 'w'), ensure_ascii=False, indent=1)
    return out

if __name__ == '__main__':
    ra, panel, df = load()
    q2 = q2_compare(ra, panel)
    print('Q2:', json.dumps({k: q2[k] for k in ['percent_exact', 'rank_exact', 'disagree_weeks', 'fan_save_count', 'fan_save_rate']}))
    q3 = q3_factors(ra, panel, df)
    print('Q3: judge age', round(q3['judge_model']['age'], 3), '| fan age', round(q3['fan_model']['age'], 3),
          '| R²:', round(q3['judge_model']['r2'], 3), '/', round(q3['fan_model']['r2'], 3))
    q4 = q4_new_system(ra, panel)
    print('Q4: alpha 扫描', {a: v['exact_rate'] for a, v in q4['alphas'].items()})
    print('Q4: 决赛冠军', q4['finals'])
