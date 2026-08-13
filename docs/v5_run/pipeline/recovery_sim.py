#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模拟恢复实验框架（V5 验证产物模板 · 反演/估计类）
原理：合成真值 → 按规则仿真观测（淘汰结果）→ 跑反演 → 报恢复误差
恢复误差小 = 模型能从"只有淘汰结果的观测"中恢复真值；误差大 = 反演不可行
这是判定"循环验证"的确定性手段：真值已知，回代率再高也不能证明恢复能力，
只有恢复实验能证明。
"""
import json
import numpy as np

def run_recovery(forward_model, inverse_model, n_weeks=200, n_active=6,
                 seed=42, noise_sigma=0.3):
    """
    forward_model(true_shares, judge_scores, week_info) -> dict(eliminated_idx, ...)
    inverse_model(judge_scores, eliminated_idx, week_info) -> estimated_shares
    返回恢复误差指标。
    """
    rng = np.random.default_rng(seed)
    errors = []
    replay_ok = 0
    n_total = 0
    for w in range(n_weeks):
        # 合成真值：Dirichlet 份额（有结构的粉丝票）
        true_shares = rng.dirichlet(np.ones(n_active) * 2.0)
        # 合成评委分：与真值相关 + 噪声
        judge_scores = 7 + 3 * true_shares + rng.normal(0, noise_sigma, n_active)
        judge_scores = np.clip(judge_scores, 1, 10)
        # 前向模型：percent 组合分最低者淘汰
        judge_pct = judge_scores / judge_scores.sum()
        combined = judge_pct + true_shares
        eliminated = int(np.argmin(combined))
        # 反演（inverse_model 只知道 judge_scores 和 eliminated）
        est = inverse_model(judge_scores, eliminated, n_active, rng)
        # 恢复误差：L1 距离
        err = float(np.sum(np.abs(est - true_shares)))
        errors.append(err)
        # 回代：估计份额下组合分最低者是否 = 淘汰者
        est_pct = est
        combined_est = judge_scores / judge_scores.sum() + est_pct
        pred = int(np.argmin(combined_est))
        replay_ok += int(pred == eliminated)
        n_total += 1
    return {
        'n_weeks': n_weeks,
        'share_l1_mean': float(np.mean(errors)),
        'share_l1_p95': float(np.percentile(errors, 95)),
        'replay_rate': replay_ok / n_total,
        'random_baseline_l1': 2.0 / n_active * 2,  # 均匀先验的期望 L1 参考
    }
