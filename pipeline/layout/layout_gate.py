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


class TemplateGate:
    """官方模板清单门禁（用户指令 2026-08-15：「一定要先搜索论文模板，严格按模板排版」）

    流程：S5 开工先搜索官方模板（官网/官方发布渠道）→ 提取模板清单 → 逐条核对论文。
    本类含华数杯官方模板清单（huashu-template-layout.md 实测版）与 MCM 官方模板清单；
    清单可被搜索到的更新版覆盖（D23 不硬编码，但缺失清单时门禁直接阻断）。
    """

    # 华数杯官方模板清单（2026 实测）：每条 = (检查名, 阻断级, 描述)
    HUASHU_TEMPLATE = [
        ("first_page_info_table", True, "第一页基本信息表（类别/竞赛名/参赛编号）"),
        ("title_hei_15pt", True, "标题黑体 15pt"),
        ("abstract_one_page", True, "摘要限一页（含问题重述一句话+各问方法一句话+主要结果数字）"),
        ("page_footer_counter", False, "页码页脚中部、从 1 连续（@page @bottom-center）"),
        ("body_songti_12pt", True, "正文宋体小四 12pt"),
        ("body_le_20pages", True, "正文 ≤20 页（官方上限）"),
        ("ai_statement_before_refs", True, "AI 声明在参考文献前（官方句式）"),
        ("refs_include_ai_tool", True, "参考文献含 AI 工具条目"),
        ("appendix_software_cmd_src", False, "附录=软件+命令+源码"),
        ("web_resources_access_time", False, "网络资源写访问时间"),
    ]

    # MCM 官方模板清单（MCM-ICM_Summary.tex 实测版）
    MCM_TEMPLATE = [
        ("summary_sheet", True, "Summary Sheet 官方样式"),
        ("abstract_limited", True, "摘要限制（summary 一页内）"),
        ("solution_25_pages", True, "solution ≤25 页"),
        ("no_name_school", True, "正文禁出现姓名/学校"),
        ("ai_use_report", True, "AI 使用报告（2024 起官方要求）"),
        ("refs_citation", False, "参考文献规范引用"),
    ]

    TEMPLATES = {"华数杯": HUASHU_TEMPLATE, "MCM": MCM_TEMPLATE}

    def check(self, competition: str, paper_meta: dict) -> list:
        """paper_meta: {检查名: bool}。缺模板清单 / 阻断级缺失项 = fail。"""
        findings = []
        tpl = self.TEMPLATES.get(competition)
        if tpl is None:
            return [LayoutFinding("template", "fail",
                                  f"竞赛 {competition} 无模板清单——先搜索官方模板再排版")]
        for name, blocking, desc in tpl:
            ok = paper_meta.get(name, False)
            if not ok:
                findings.append(LayoutFinding(
                    "template", "fail" if blocking else "warn",
                    f"[{competition}模板] 缺失: {desc}"))
        if not any(f.verdict == "fail" for f in findings):
            findings.append(LayoutFinding("template", "pass",
                                          f"{competition} 官方模板 {len(tpl)} 项全部符合"))
        return findings


class LengthGate:
    """篇幅门禁（用户指令 2026-08-15：「内容门禁大概在上限要求的 75% 左右」）

    正文页数 ≥ 上限×75%：华数杯 20 页上限 → ≥15 页；低于 = blocking
    （评审第一印象「内容不足/不走心」，篇幅信号 2026-08-14 教训的程序化）。
    补内容 = 补公式推导/表格/灵敏度分析，不是注水。
    """

    def check(self, page_count: int, limit: int, percent: float = 0.75) -> list:
        need = max(1, int(round(limit * percent)))
        if page_count < need:
            return [LayoutFinding("length", "fail",
                    f"正文 {page_count} 页 < 上限 {limit} 页的 {int(percent*100)}%（需 ≥{need} 页）——"
                    f"内容不足显不走心，必须补公式推导/表格/灵敏度（非注水）")]
        if page_count > limit:
            return [LayoutFinding("length", "fail", f"正文 {page_count} 页超上限 {limit} 页")]
        return [LayoutFinding("length", "pass", f"篇幅 {page_count}/{limit} 页（≥75% 上限）达标")]


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
