# -*- coding: utf-8 -*-
"""排版层（阶段7）：图清单/公式清单 + 四维密度检查 + 直观性规则检查（A21/A22）

数量标准来源：O 奖语料 IQR 基线（baseline.py 产出），默认值仅作先验（D23 不硬编码）。
"""
import json
import os
import re
from dataclasses import dataclass, field


@dataclass
class LayoutFinding:
    check: str
    verdict: str   # pass / fail / warn
    detail: str = ""


# 临时默认值（先验基线；正式值由 corpus_baseline.py 从 O 奖语料产出后覆盖）
DEFAULT_STANDARDS = {
    "12页": {"fig_min": 8, "fig_max": 14, "tab_max": 6},
    "15页": {"fig_min": 10, "fig_max": 18, "tab_max": 8},
    "公式密度": {"评价类": (15, 25), "优化类": (20, 35), "预测类": (10, 20)},
}


class FigureInventory:
    """图清单（A22：未登记图触发门禁失败；data_source_hash 衔接作废引擎）"""

    def __init__(self):
        self.figures = []   # {id, caption, section, data_source_hash, script_hash,
                            #  intuitiveness_rating, page_ref, claim_refs, info_gain}

    def register(self, **kw):
        required = ("id", "caption", "section", "data_source_hash", "script_hash",
                    "claim_refs", "info_gain")
        for k in required:
            if k not in kw or not kw[k]:
                raise ValueError(f"图登记缺少必填字段: {k}")
        self.figures.append(kw)

    def check_orphan(self, used_in_text: set) -> list:
        """孤儿图检测：登记了但正文无引用（A22 注入 1 张无引用图 → 阻断率 100%）"""
        orphans = [f for f in self.figures if f["id"] not in used_in_text]
        return orphans

    def dirty_figures(self, live_hashes: dict) -> list:
        """数据作废 → 图条目 dirty → 排版门禁阻断（作废引擎衔接）"""
        return [f for f in self.figures
                if f["data_source_hash"] not in live_hashes.values()]

    def info_gain_duplicates(self) -> list:
        """chart junk 检测：info_gain 相同的图对（防换画法凑数）"""
        seen = {}
        dups = []
        for f in self.figures:
            key = (f["info_gain"], f["claim_refs"][0] if f["claim_refs"] else "")
            if key in seen:
                dups.append((seen[key], f["id"]))
            seen[key] = f["id"]
        return dups


class FormulaInventory:
    """公式清单：编号连续 + 引用完整 + LaTeX 合法（孤儿公式 = blocking）"""

    @staticmethod
    def extract_numbers(tex_or_md_text: str) -> list:
        return [int(m) for m in re.findall(r"\\begin\{equation\}|\((\d+)\)", tex_or_md_text) if m]

    def check(self, formula_numbers: list, cited_numbers: set) -> list:
        findings = []
        if formula_numbers:
            # 编号连续性
            for a, b in zip(sorted(formula_numbers), sorted(formula_numbers)[1:]):
                if b - a != 1:
                    findings.append(LayoutFinding(
                        "formula_seq", "fail", f"公式编号断裂: {a} → {b}"))
                    break
        # 引用完整性：每条编号公式必须被引用
        for n in formula_numbers:
            if n not in cited_numbers:
                findings.append(LayoutFinding(
                    "formula_cite", "fail", f"公式 ({n}) 无正文引用（孤儿公式）"))
        if not findings:
            findings.append(LayoutFinding("formula", "pass",
                                          f"{len(formula_numbers)} 条公式编号连续且引用完整"))
        return findings


class DensityChecker:
    """四维密度检查（D24）：总量 / section 分布 / 图:表:公式配比 / 引用闭环"""

    def __init__(self, standards: dict = None):
        self.standards = standards or DEFAULT_STANDARDS

    def check(self, page_count: int, n_fig: int, n_tab: int, n_formula: int,
              section_counts: dict, qtype: str = "优化类") -> list:
        findings = []
        key = "12页" if page_count <= 13 else "15页"
        s = self.standards[key]
        # 总量密度
        if n_fig < s["fig_min"]:
            findings.append(LayoutFinding("density_total", "fail",
                f"图数 {n_fig} 低于 {key} 下限 {s['fig_min']}（O 奖语料 IQR）"))
        elif n_fig > s["fig_max"]:
            findings.append(LayoutFinding("density_total", "warn",
                f"图数 {n_fig} 高于 {key} 上限 {s['fig_max']}，警惕 chart junk"))
        if n_tab > s["tab_max"]:
            findings.append(LayoutFinding("density_total", "warn",
                f"表数 {n_tab} 超过上限 {s['tab_max']}"))
        # 公式密度（题型分档）
        lo, hi = self.standards["公式密度"].get(qtype, (15, 25))
        if not (lo <= n_formula <= hi):
            findings.append(LayoutFinding("formula_density", "warn",
                f"公式数 {n_formula} 超出 {qtype} 区间 [{lo},{hi}]"))
        # section 分布均衡：单节图数方差约束（任一节 ≥60% 总量 = 失衡）
        total_fig = max(1, n_fig)
        for sec, cnt in section_counts.items():
            if cnt / total_fig >= 0.6:
                findings.append(LayoutFinding("section_balance", "warn",
                    f"章节 {sec} 集中了 {cnt}/{n_fig} 张图（≥60%，分布失衡）"))
        if not any(f.verdict == "fail" for f in findings):
            findings.append(LayoutFinding("density", "pass",
                f"{n_fig}图/{n_tab}表/{n_formula}式 密度达标"))
        return findings


class IntuitiveCheck:
    """直观性规则检查（D25 枚举化）：轴标签/图例/单位/字号/子图上限/图题相关性"""

    RULES = [
        ("axis_label", lambda m: bool(m.get("axis_labels"))),
        ("legend", lambda m: bool(m.get("legend")) or m.get("single_series")),
        ("unit", lambda m: bool(m.get("unit"))),
        ("title", lambda m: bool(m.get("title")) and len(m["title"]) >= 4),
        ("subplot_limit", lambda m: m.get("subplots", 1) <= 6),
        ("fontsize", lambda m: m.get("fontsize", 10) >= 8),
    ]

    def check(self, figure_meta: dict) -> list:
        findings = []
        for rule, fn in self.RULES:
            if not fn(figure_meta):
                findings.append(LayoutFinding("intuitive", "fail",
                                              f"图 {figure_meta.get('id')} 违反规则 {rule}"))
        return findings

    def run(self, figures: list, max_blocking: int = 5) -> list:
        """收敛目标（D25）：每次检查 blocking ≤5 个/次，防告警疲劳"""
        all_findings = []
        for f in figures:
            all_findings += self.check(f)
        fails = [x for x in all_findings if x.verdict == "fail"]
        if len(fails) > max_blocking:
            return fails[:max_blocking] + [LayoutFinding(
                "intuitive", "warn", f"本次 blocking 截断至 {max_blocking} 条（共 {len(fails)}）")]
        return all_findings
