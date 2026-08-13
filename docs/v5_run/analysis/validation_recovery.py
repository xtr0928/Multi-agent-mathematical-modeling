#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validation_recovery.py — 模拟恢复实验（V5 验证产物，反演类）
合成真值份额 → 仿真淘汰 → 跑路线 A 最大熵求解器 → 报恢复误差
判据：L1 恢复误差远小于随机基线 = 反演有信息；否则份额不可恢复
"""
import json, sys
import numpy as np
sys.path.insert(0, '/tmp/solve_mcm2026C_v5/analysis')
from route_a_bayes import max_entropy_solution

def run_recovery(n_weeks=200, n_active=8, seed=42, noise=0.3, eras=('percent',)):
    rng = np.random.default_rng(seed)
    errs = []
    replay_ok = 0
    n_tot = 0
    for w in range(n_weeks):
        # 真值份额（有结构：一半选手粉丝多）
        true = rng.dirichlet(np.r_[np.ones(n_active // 2) * 3, np.ones(n_active - n_active // 2)])
        # 评委分与真值相关 + 噪声
        j = 7 + 3 * true + rng.normal(0, noise, n_active)
        j = np.clip(j, 1, 10)
        jp = j / j.sum()
        # 仿真：percent 规则淘汰组合分最低者
        comb = jp + true
        elim = int(np.argmin(comb))
        # 反演：只给评委分 + 淘汰者
        s_hat, ci = max_entropy_solution(jp, [elim], 'percent', n_active)
        # 恢复误差 L1
        err = float(np.sum(np.abs(s_hat - true)))
        errs.append(err)
        # 回代
        pred = int(np.argmin(jp + s_hat))
        replay_ok += int(pred == elim)
        n_tot += 1
    # 随机基线：均匀猜测的期望 L1 = E|uniform - true|
    base_errs = [float(np.sum(np.abs(np.ones(n_active) / n_active - rng.dirichlet(np.ones(n_active)))))
                 for _ in range(500)]
    out = {
        'n_weeks': n_weeks, 'n_active': n_active,
        'share_l1_mean': round(float(np.mean(errs)), 4),
        'share_l1_p95': round(float(np.percentile(errs, 95)), 4),
        'random_baseline_l1_mean': round(float(np.mean(base_errs)), 4),
        'improvement_vs_random': round(1 - float(np.mean(errs)) / float(np.mean(base_errs)), 4),
        'replay_rate': round(replay_ok / n_tot, 4),
    }
    json.dump(out, open('/tmp/solve_mcm2026C_v5/analysis/validation_recovery.json', 'w'),
              ensure_ascii=False, indent=1)
    return out

if __name__ == '__main__':
    out = run_recovery()
    print(json.dumps(out, indent=1))
