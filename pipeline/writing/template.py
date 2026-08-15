# -*- coding: utf-8 -*-
"""微单元写作模板（阶段8）：段落结构模板 + claim_id 绑定 + stale 检测

D6：论文正文每个数字必须引用 registry 条目 ID——排版门禁扫描引用新鲜度，
引用已作废条目即阻断。段落 stale 时按模板重渲染。
"""
import json
import os
import re
import uuid

# 微单元模板：章节/段落/句级结构（十大差距点 #10）
PARAGRAPH_TEMPLATES = {
    "模型建立": "针对{question}，我们建立{model_name}模型：{formula_refs}。"
                "其核心机制是{mechanism}（引用 {claim_refs}）。",
    "结果呈现": "{metric_name} 达到 {value}（{uncertainty}），"
                "相比基线 {baseline_name} 的 {baseline_value}，{comparison}。",
    "验证": "为验证{hypothesis}，我们进行{experiment}：{result}。"
            "该结果{robustness_statement}。",
    "局限性": "{limitation}。该局限不影响主结论，因为{mitigation}。",
}

CLAIM_REF_PATTERN = re.compile(r"\[claim:([a-f0-9]{8,32})\]")


class ParagraphUnit:
    """一个绑定 registry 条目的段落单元"""

    def __init__(self, template_key: str, variables: dict, claim_ids: list):
        if template_key not in PARAGRAPH_TEMPLATES:
            raise ValueError(f"未知模板: {template_key}")
        self.id = "P" + uuid.uuid4().hex[:8]
        self.template_key = template_key
        self.variables = variables
        self.claim_ids = claim_ids      # 本段引用的 registry 条目
        self.rendered = None

    def render(self) -> str:
        text = PARAGRAPH_TEMPLATES[self.template_key].format(**self.variables)
        # 段落数字焊接：claim 引用显式内嵌（D6）
        refs = "".join(f"[claim:{cid}]" for cid in self.claim_ids)
        self.rendered = text + refs
        return self.rendered

    def to_dict(self):
        return {"id": self.id, "template_key": self.template_key,
                "variables": self.variables, "claim_ids": self.claim_ids}


class WritingTemplateEngine:
    """模板引擎：渲染 + 新鲜度扫描（引用已作废条目即阻断，A6）"""

    def __init__(self, registry):
        self.registry = registry      # ClaimRegistry 实例
        self.units = {}

    def add(self, unit: ParagraphUnit):
        self.units[unit.id] = unit

    def scan_stale_refs(self, unit_id: str) -> list:
        """A6/A19：扫描段落引用的 claim——已作废/过期/experiment 产物/非确定性 → 阻断

        experiment 状态禁入论文引用池（D19 敏感度产物隔离：A19）。"""
        unit = self.units[unit_id]
        stale = []
        for cid in unit.claim_ids:
            c = self.registry.get_claim(cid)
            if c is None:
                stale.append({"claim_id": cid, "reason": "missing"})
            elif c["status"] not in ("fresh", "final"):
                stale.append({"claim_id": cid, "reason": c["status"]})
        return stale

    def scan_all(self) -> dict:
        return {pid: self.scan_stale_refs(pid) for pid in self.units}

    def rerender_stale(self, unit_id: str, new_claim_ids: list,
                       variables: dict = None) -> str:
        """段落 stale → 按模板重渲染（D6 的修复回路）"""
        unit = self.units[unit_id]
        unit.claim_ids = new_claim_ids
        if variables:
            unit.variables.update(variables)
        return unit.render()
