# -*- coding: utf-8 -*-
"""跨语言对照工具（阶段3 补全，D15）：预生成随机数文件协议 + KS 分布比较

铁律：跨语言禁止指望 RNG 流一致——随机性指标用分布比较（KS 检验），不比较逐点。
"""
import json
import os
import random


def gen_rng_file(path: str, n: int, seed: int = 42):
    """预生成随机数文件协议：两边喂同一文件，隔离 RNG 差异"""
    rng = random.Random(seed)
    vals = [rng.random() for _ in range(n)]
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for v in vals:
            f.write("%.17g\n" % v)
    os.rename(tmp, path)
    return path


def load_rng_file(path: str) -> list:
    with open(path) as f:
        return [float(line) for line in f if line.strip()]


def ks_stat(a: list, b: list) -> float:
    """两样本 Kolmogorov-Smirnov 统计量 D（无 scipy 依赖，确定性实现）"""
    a_sorted, b_sorted = sorted(a), sorted(b)
    n1, n2 = len(a_sorted), len(b_sorted)
    if n1 == 0 or n2 == 0:
        return 1.0
    i = j = 0
    d_max = 0.0
    while i < n1 and j < n2:
        if a_sorted[i] <= b_sorted[j]:
            x = a_sorted[i]
            while i < n1 and a_sorted[i] == x:
                i += 1
            cdf1 = i / n1
        else:
            x = b_sorted[j]
            while j < n2 and b_sorted[j] == x:
                j += 1
            cdf2 = j / n2
        # 同步推进另一方到 >= x
        while j < n2 and b_sorted[j] == x:
            j += 1
        while i < n1 and a_sorted[i] == x:
            i += 1
        cdf1 = i / n1
        cdf2 = j / n2
        d = abs(cdf1 - cdf2)
        if d > d_max:
            d_max = d
    return d_max


def ks_compare(a: list, b: list, alpha: float = 0.05) -> dict:
    """KS 分布比较：返回是否拒绝「两分布相同」"""
    D = ks_stat(a, b)
    n1, n2 = len(a), len(b)
    # 临界值近似：c(α) * sqrt((n1+n2)/(n1*n2))，α=0.05 → 1.358
    c = 1.358 if alpha == 0.05 else 1.628 if alpha == 0.01 else 1.358
    critical = c * ((n1 + n2) / (n1 * n2)) ** 0.5
    reject = D > critical
    return {"D": D, "critical": critical, "reject_same_distribution": reject,
            "alpha": alpha, "n1": n1, "n2": n2}
