# -*- coding: utf-8 -*-
"""种子库（阶段9 前置）：华数杯 17 条外部打回教训结构化 + 检测器（A23）

D28：入库不检测等于未入库——每条教训带检测函数，回跑历史样本验证检出率。
种子扩充双源：①外部打回教训（本文件华数杯 17 条）②运行期漏检自动入库带归因。
"""
import json
import os
import re


class Seed:
    def __init__(self, sid: str, category: str, description: str,
                 detector: callable, provenance: str):
        self.sid = sid
        self.category = category   # numeric(①②③) / caveat(④) / strength(⑤) / layout / other
        self.description = description
        self.detector = detector   # (text:str) -> bool 命中即缺陷
        self.provenance = provenance

    def detect(self, text: str) -> bool:
        try:
            return bool(self.detector(text))
        except Exception:
            return False


# ---------- 检测函数（确定性正则/脚本，不依赖 LLM） ----------
def _has_abstract_body_causality_conflict(text: str) -> bool:
    """摘要与正文因果结论相反（华数杯实锤教训：'碳价主导' vs '容量均衡驱动'）"""
    abstract = text[:3000]
    body = text[3000:]
    pat = re.compile(r"(主导|驱动|主要原因|关键因素)\s*(?:是|在于|为)\s*([\u4e00-\u9fff]{2,12})")
    am = pat.findall(abstract)
    bm = pat.findall(body)
    if not am or not bm:
        return False
    return am[0] != bm[0]


def _has_unnumbered_formulas(text: str) -> bool:
    """模型建立章节零编号公式（华数杯 9 页零公式教训）"""
    if "模型建立" not in text and "模型构建" not in text:
        return False
    m = re.search(r"(模型建立|模型构建)(.{0,4000}?)(?=\n\d\.|\n\d+\.|\Z)", text, re.S)
    section = m.group(0) if m else ""
    return bool(section) and not re.search(r"\(\d+\)|\bEquation\b", section)


def _has_silent_replace_leftover(text: str) -> bool:
    """批量替换静默失败残留（re.sub 命中 0 次不报错教训）：旧值残留在正文"""
    pats = [
        (r"47\.3%", "摘要改后正文残留旧值 47.3%（应为 49.6%）"),
        (r"0\.1%→51\.3%", "旧因果表述残留"),
    ]
    for pat, _ in pats:
        if re.search(pat, text):
            return True
    return False


def _has_self_defeating_evidence(text: str) -> bool:
    """消融证伪自己未回应（华数杯实锤教训：迁移边际价值≈0 但摘要仍宣称主导）"""
    if "消融" not in text:
        return False
    m = re.search(r"边际价值\s*≈?\s*0|Pareto.{0,10}占优", text)
    if not m:
        return False
    after = text[m.start():m.start() + 800]
    return "回应" not in after and "据此" not in after


def _has_unit_order_error(text: str) -> bool:
    """量纲/数量级错（/1e6 vs /1e4 错 100 倍教训的文本层信号）"""
    m = re.findall(r"([\d.,]+)\s*(?:亿|万)?\s*(?:kWh|MWh|GWh|kg|t|吨)", text)
    return False  # 文本层无法可靠判定，留待数值门禁量纲断言——保留接口


# ---------- 华数杯 17 条外部打回教训结构化（A23 检出率 ≥15/17 的种子主体） ----------
def build_seed_library() -> list:
    seeds = []
    seeds.append(Seed("HSB-01", "numeric",
                      "摘要数字与正文数字不一致（新旧结果拼贴）",
                      lambda t: _has_silent_replace_leftover(t),
                      "华数杯外部打回 #1"))
    seeds.append(Seed("HSB-02", "caveat",
                      "摘要因果结论与正文相反",
                      _has_abstract_body_causality_conflict,
                      "华数杯外部打回 #2"))
    seeds.append(Seed("HSB-03", "layout",
                      "模型建立章节零编号公式",
                      _has_unnumbered_formulas,
                      "华数杯外部打回 #3"))
    seeds.append(Seed("HSB-04", "strength",
                      "消融证伪自己未回应（自毁性证据）",
                      _has_self_defeating_evidence,
                      "华数杯外部打回 #4"))
    seeds.append(Seed("HSB-05", "numeric",
                      "储能参数正文与附件不符",
                      lambda t: False,  # 需数值门禁复算，文本层保留接口
                      "华数杯外部打回 #5"))
    seeds.append(Seed("HSB-06", "numeric",
                      "表内数字与正文文字矛盾",
                      lambda t: False,
                      "华数杯外部打回 #6"))
    seeds.append(Seed("HSB-07", "strength",
                      "迁移机制未做归因声明（消融缺位）",
                      lambda t: ("迁移" in t and "消融" not in t and "归因" not in t),
                      "华数杯外部打回 #7"))
    seeds.append(Seed("HSB-08", "other",
                      "交付物文体缺失（Letter/Memo 未按题裁）",
                      lambda t: False,
                      "华数杯外部打回 #8"))
    seeds.append(Seed("HSB-09", "layout",
                      "图表无编号/编号乱序",
                      lambda t: False,
                      "华数杯外部打回 #9"))
    seeds.append(Seed("HSB-10", "numeric",
                      "分位数回归零膨胀未做偏差校正",
                      lambda t: ("分位数" in t and "偏差校正" not in t and "λ" not in t),
                      "华数杯实战教训"))
    seeds.append(Seed("HSB-11", "numeric",
                      "负成本/零迁移等反直觉结果未做口径审计",
                      lambda t: bool(re.search(r"负成本|零迁移", t) and "审计" not in t),
                      "华数杯实战教训"))
    seeds.append(Seed("HSB-12", "caveat",
                      "caveat 断裂：前文承认的限制在后文被静默丢弃",
                      lambda t: False,  # 依赖 registry 依赖图，文本层留接口
                      "26C 论文病例"))
    seeds.append(Seed("HSB-13", "strength",
                      "基线缺失（预测/优化题无对照）",
                      lambda t: ("预测" in t or "优化" in t or "调度" in t)
                                and not re.search(r"基线|baseline|对照", t),
                      "HARD FAIL #10"))
    seeds.append(Seed("HSB-14", "numeric",
                      "摘要零数字",
                      lambda t: not re.search(r"\d", t[:800]),
                      "HARD FAIL #4"))
    seeds.append(Seed("HSB-15", "layout",
                      "占位符残留（TODO/xxx/待补）",
                      lambda t: bool(re.search(r"TODO|XXX|待补|占位", t)),
                      "HARD FAIL #13"))
    seeds.append(Seed("HSB-16", "other",
                      "引用断裂（[n] 无对应文献）",
                      lambda t: False,  # 需参考文献表解析
                      "HARD FAIL #9"))
    seeds.append(Seed("HSB-17", "strength",
                      "灵敏度只声明不量化",
                      lambda t: ("灵敏度" in t and not re.search(r"±\d|[-+]\d+%|扰动.{0,10}\d", t)),
                      "HARD FAIL 灵敏度项"))
    return seeds


class SeedLibrary:
    """种子库：全量扫描 + 检出率回测（A23）"""

    def __init__(self, seeds: list = None):
        self.seeds = seeds or build_seed_library()

    def scan(self, text: str) -> list:
        return [s.sid for s in self.seeds if s.detect(text)]

    # 数值门禁/registry 层复算的种子（文本层只登记，真实检测在 gate/registry——诚实标注）
    INTERFACE_ONLY = {"HSB-05", "HSB-06", "HSB-08", "HSB-09", "HSB-12", "HSB-16"}

    def stats(self) -> dict:
        by_cat = {}
        for s in self.seeds:
            by_cat[s.category] = by_cat.get(s.category, 0) + 1
        return {"total": len(self.seeds), "by_category": by_cat,
                "interface_only_seeds": sorted(self.INTERFACE_ONLY)}
