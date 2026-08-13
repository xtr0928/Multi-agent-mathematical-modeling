#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""panel_builder.py — 基础面板构建（V5 PHASE 3 路线无关底座）
从官方 CSV 构建：活跃选手-周面板、淘汰事件、决赛周、特征表
活跃判定：该周任一评委给分 > 0（题面 Note：0 = 已淘汰）
"""
import json, re, csv
import numpy as np
import pandas as pd

BASE = '/tmp/solve_mcm2026C_v5/analysis'

def build():
    df = pd.read_csv(f'{BASE}/2026_MCM_Problem_C_Data.csv', encoding='utf-8-sig')
    judge_cols = [c for c in df.columns if re.match(r'week\d+_judge\d+_score', c)]
    week_cols = {}
    for c in judge_cols:
        w = int(re.search(r'week(\d+)_', c).group(1))
        week_cols.setdefault(w, []).append(c)
    n_weeks = max(week_cols)

    # 淘汰事件解析：results 列（文本：Eliminated - Week N 等）
    def parse_results(r):
        if pd.isna(r):
            return None
        r = str(r).strip()
        if 'Eliminated' in r:
            m = re.search(r'Week\s*(\d+)', r)
            return ('eliminated', int(m.group(1)) if m else None)
        return ('other', r)

    events = []          # {season, week, actives, elims} —— 注意：循环外初始化！
    finals = []          # {season, week, names, champion}
    panel_rows = []      # {season, week, name, judge_sum, n_active}

    for season, grp in df.groupby('season'):
        grp = grp.sort_values('placement')
        # 每季选手活跃状态矩阵
        for w in range(1, n_weeks + 1):
            cols = week_cols.get(w, [])
            if not cols:
                continue
            scores = grp[cols].sum(axis=1)
            active_mask = scores > 0
            active_names = grp.loc[active_mask, 'celebrity_name'].tolist()
            active_judge = scores[active_mask].values
            if not active_names:
                continue
            # 该周淘汰者：results 中 Eliminated - Week w 的选手
            elims = []
            for _, row in grp[active_mask].iterrows():
                pr = parse_results(row['results'])
                if pr and pr[0] == 'eliminated' and pr[1] == w:
                    elims.append(row['celebrity_name'])
            events.append({'season': int(season), 'week': w,
                                  'names': active_names,
                                  'judge_sums': active_judge.tolist(),
                                  'elims': elims})
            for nm, js in zip(active_names, active_judge):
                panel_rows.append({'season': int(season), 'week': w, 'name': nm,
                                   'judge_sum': float(js),
                                   'n_active': len(active_names)})
        # 决赛周：placement 有数字名次的最后活跃周
        fin_names = grp[grp['placement'].notna() & (grp['placement'] != 0)]['celebrity_name'].tolist()
        if fin_names:
            # 决赛周 = 这些选手最后共同活跃的周（active 集合恰好等于决赛名单）
            final_week = None
            for w in range(n_weeks, 0, -1):
                cols = week_cols.get(w, [])
                if not cols:
                    continue
                active = set(grp.loc[grp[cols].sum(axis=1) > 0, 'celebrity_name'])
                if all(nm in active for nm in fin_names) and len(active) == len(fin_names):
                    final_week = w
                    break
            if final_week:
                cols = week_cols[final_week]
                fin_df = grp[grp['celebrity_name'].isin(fin_names)]
                judge_sums = fin_df[cols].sum(axis=1).values
                champ = grp.loc[grp['placement'] == 1, 'celebrity_name'].tolist()
                finals.append({'season': int(season), 'week': final_week,
                               'names': fin_names, 'judge_sums': judge_sums.tolist(),
                               'champion': champ})

    out = {
        'n_seasons': int(df['season'].nunique()),
        'n_celebrities': int(df['celebrity_name'].nunique()),
        'n_weeks_max': n_weeks,
        'events': events,
        'finals': finals,
        'panel': panel_rows,
        'stats': {
            'n_elim_events': sum(len(e['elims']) for e in events),
            'n_event_weeks': len(events),
            'n_final_weeks': len(finals),
            'n_panel_rows': len(panel_rows),
        },
    }
    json.dump(out, open(f'{BASE}/panel.json', 'w'), ensure_ascii=False, indent=1)
    return out

if __name__ == '__main__':
    out = build()
    print(json.dumps(out['stats'], indent=1))
    # 规则时代划分
    events = out['events']
    s1_2 = sum(1 for e in events if e['season'] <= 2)
    s3_27 = sum(1 for e in events if 3 <= e['season'] <= 27)
    s28 = sum(1 for e in events if e['season'] >= 28)
    print(f'时代分布：S1-2 rank 时代 {s1_2} 周 | S3-27 percent 时代 {s3_27} 周 | S28+ rank+底二 {s28} 周')
