# -*- coding: utf-8 -*-
"""内部基准反馈环（阶段9）：C++ 重写收益 / 假设官失职统计 / predicate 覆盖率

设计原则（诚实边界）：决策记录喂给基准，用数据回看机制是否值得——与「正确性>完整性>时间窗」同源。
"""
import json
import os
import time


class InternalBenchmark:
    """记录四类决策数据，产出反馈报告"""

    def __init__(self, path: str):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return {"cpp_decisions": [], "assumption_misses": [],
                "predicate_usage": {}, "registry_experiments": []}

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.rename(tmp, self.path)

    # ---------- C++ 重写收益（D30：重写决策公式 + 预估 vs 实测留档） ----------
    def record_cpp_decision(self, task_name: str, est_py_s: float, est_cpp_s: float,
                            rewrite_cost_h: float, calls_expected: int, decided: bool,
                            actual_py_s: float = None, actual_cpp_s: float = None,
                            speedup: float = None, accurate: bool = None):
        self.data["cpp_decisions"].append({
            "task": task_name, "est_py_s": est_py_s, "est_cpp_s": est_cpp_s,
            "rewrite_cost_h": rewrite_cost_h, "calls_expected": calls_expected,
            "decided": decided, "actual_py_s": actual_py_s, "actual_cpp_s": actual_cpp_s,
            "speedup": speedup, "estimate_accurate": accurate, "ts": time.time()})
        self.save()

    def cpp_should_rewrite(self, est_py_s: float, est_cpp_s: float,
                           rewrite_cost_h: float, calls: int, total_run_s: float) -> bool:
        """D30 重写决策公式：(T_py−T_cpp)×调用次数 > 3×重写成本 且 总运行 ≥1h"""
        gain = (est_py_s - est_cpp_s) * calls
        cost = rewrite_cost_h * 3600 * 3
        return gain > cost and total_run_s >= 3600

    def cpp_summary(self) -> dict:
        ds = self.data["cpp_decisions"]
        if not ds:
            return {"n": 0}
        decided = [d for d in ds if d["decided"]]
        accurate = [d for d in ds if d.get("accurate") is not None]
        return {"n": len(ds), "rewritten": len(decided),
                "estimate_accuracy": (sum(1 for d in accurate if d["accurate"]) / len(accurate))
                if accurate else None}

    # ---------- 假设官失职统计（D21 补充：评审暴露的问题若挑战期未提 = 失职） ----------
    def record_assumption_miss(self, assumption: str, stage_exposed: str, why_missed: str):
        self.data["assumption_misses"].append(
            {"assumption": assumption, "stage_exposed": stage_exposed,
             "why_missed": why_missed, "ts": time.time()})
        self.save()

    def assumption_summary(self) -> dict:
        return {"misses": len(self.data["assumption_misses"]),
                "by_stage": self._group(self.data["assumption_misses"], "stage_exposed")}

    # ---------- predicate 覆盖率（D27：状态词必须走词汇表） ----------
    def record_predicate(self, predicate: str):
        self.data["predicate_usage"][predicate] = \
            self.data["predicate_usage"].get(predicate, 0) + 1
        self.save()

    def predicate_coverage(self, registry_statuses: list) -> dict:
        """registry 实际状态词 vs 词汇表：自由文本状态 = 覆盖率漏洞"""
        from engine.registry import PREDICATE_STATUS
        legal = set(PREDICATE_STATUS)
        used = set(registry_statuses)
        illegal = used - legal
        return {"legal": sorted(used & legal), "illegal": sorted(illegal),
                "coverage": (len(used & legal) / len(used)) if used else 1.0}

    @staticmethod
    def _group(items, key):
        out = {}
        for it in items:
            out[it[key]] = out.get(it[key], 0) + 1
        return out
