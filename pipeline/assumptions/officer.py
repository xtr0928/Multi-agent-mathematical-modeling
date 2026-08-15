# -*- coding: utf-8 -*-
"""假设官（阶段6）：假设生命周期四步 + 三级分类 + 隐式假设映射 + 作者回避

铁律：提交者不参与审查/挑战/敏感度判定（作者回避，A18）。
登记是 build 钩子门禁（D19）：论文中"假设/assume/不妨设"语句必须与登记表比对。
"""
import json
import os
import time
import uuid

ASSUMPTION_STATUS = ("draft", "necessity_passed", "challenged",
                     "sensitivity_passed", "frozen", "rejected", "unverified")
ASSUMPTION_LEVELS = ("critical", "important", "marginal")  # 关键/重要/边缘


class Assumption:
    def __init__(self, statement: str, author: str, basis: str = "",
                 level: str = "important"):
        if level not in ASSUMPTION_LEVELS:
            raise ValueError(f"非法假设级别: {level}")
        self.id = "H" + uuid.uuid4().hex[:6]
        self.statement = statement
        self.author = author          # 提交者（作者回避：审查/挑战/判定不得是此人）
        self.basis = basis
        self.level = level
        self.status = "draft"
        self.necessity_verdict = None
        self.challenge_log = []       # [{reviewer, counterfactual, experiment_design, verdict}]
        self.sensitivity_result = None

    def to_dict(self):
        return {"assumption_id": self.id, "statement": self.statement,
                "author": self.author, "basis": self.basis, "level": self.level,
                "status": self.status, "necessity_verdict": self.necessity_verdict,
                "challenge_log": self.challenge_log,
                "sensitivity_result": self.sensitivity_result}


class AssumptionOfficer:
    """假设官：独立实例（不参与方案撰写）执行四步生命周期"""

    def __init__(self, registry_path: str):
        self.registry_path = registry_path
        self.assumptions = {}
        self._load()

    def _load(self):
        if os.path.exists(self.registry_path):
            with open(self.registry_path, encoding="utf-8") as f:
                data = json.load(f)
            for a in data:
                obj = Assumption(a["statement"], a["author"], a.get("basis", ""),
                                 a.get("level", "important"))
                obj.id = a["assumption_id"]; obj.status = a["status"]
                obj.necessity_verdict = a.get("necessity_verdict")
                obj.challenge_log = a.get("challenge_log", [])
                obj.sensitivity_result = a.get("sensitivity_result")
                self.assumptions[obj.id] = obj

    def save(self):
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        tmp = self.registry_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([a.to_dict() for a in self.assumptions.values()],
                      f, ensure_ascii=False, indent=2)
        os.rename(tmp, self.registry_path)

    # ---------- 第一步：生成登记 ----------
    def register(self, statement: str, author: str, basis: str = "",
                 level: str = "important") -> Assumption:
        a = Assumption(statement, author, basis, level)
        self.assumptions[a.id] = a
        self.save()
        return a

    # ---------- 第二步：必要性审查（假设官独立实例，作者回避） ----------
    def necessity_review(self, assumption_id: str, reviewer: str,
                         keep: bool, reason: str):
        a = self.assumptions[assumption_id]
        self._assert_not_author(a, reviewer, "必要性审查")
        a.necessity_verdict = {"keep": keep, "reason": reason, "reviewer": reviewer}
        a.status = "necessity_passed" if keep else "rejected"
        self.save()

    # ---------- 第三步：主动挑战（Devil's Advocate，反事实+实验设计强制） ----------
    def challenge(self, assumption_id: str, reviewer: str, counterfactual: str,
                  experiment_design: str, verdict: str):
        """D21：每条挑战必须附反事实陈述 + 可执行实验设计，空话视为未挑战"""
        a = self.assumptions[assumption_id]
        self._assert_not_author(a, reviewer, "挑战")
        if len(counterfactual.strip()) < 10 or len(experiment_design.strip()) < 10:
            raise ValueError("挑战必须有实质反事实与实验设计（防形式化，A18）")
        a.challenge_log.append({"reviewer": reviewer,
                                "counterfactual": counterfactual,
                                "experiment_design": experiment_design,
                                "verdict": verdict})
        a.status = "challenged"
        self.save()

    # ---------- 第四步：敏感度实验（关键假设强制；产物进 experiment/ 隔离） ----------
    def sensitivity(self, assumption_id: str, result: dict, reviewer: str):
        a = self.assumptions[assumption_id]
        self._assert_not_author(a, reviewer, "敏感度判定")
        if a.level == "critical" and not result.get("performed"):
            raise ValueError("关键假设必须执行敏感度实验（A18 覆盖率 100%）")
        a.sensitivity_result = result
        a.status = "sensitivity_passed" if result.get("robust") else "unverified"
        self.save()

    def freeze(self, assumption_id: str, reviewer: str):
        a = self.assumptions[assumption_id]
        self._assert_not_author(a, reviewer, "冻结")
        if a.level == "critical" and a.status != "sensitivity_passed":
            raise ValueError(f"关键假设未过敏感度实验不可冻结: {a.id}")
        a.status = "frozen"
        self.save()

    @staticmethod
    def _assert_not_author(a: Assumption, reviewer: str, action: str):
        if reviewer == a.author:
            raise ValueError(f"作者回避铁律：提交者不得执行{action}（{a.id}）")

    # ---------- 隐式假设检查（D20：方法→隐式假设映射表） ----------
    def implicit_check(self, methods: list, author: str) -> list:
        """选用方法自动带出隐式假设，逐条确认或显式豁免；漏登记即打回（A17）"""
        from .implicit_map import IMPLICIT_MAP
        hits = []
        for m in methods:
            for implicit in IMPLICIT_MAP.get(m, []):
                if not any(a.statement == implicit for a in self.assumptions.values()):
                    hits.append({"method": m, "implicit_assumption": implicit})
        return hits  # 非空 = 有隐式假设漏登记 → build 钩子打回

    # ---------- 报告 ----------
    def stats(self) -> dict:
        n = len(self.assumptions)
        frozen = sum(1 for a in self.assumptions.values() if a.status == "frozen")
        critical_covered = sum(1 for a in self.assumptions.values()
                               if a.level == "critical"
                               and a.status in ("sensitivity_passed", "frozen"))
        critical_total = sum(1 for a in self.assumptions.values() if a.level == "critical")
        empty_challenges = sum(1 for a in self.assumptions.values()
                               for c in a.challenge_log if len(c["counterfactual"]) < 10)
        return {"total": n, "frozen": frozen, "critical_sensitivity_covered":
                f"{critical_covered}/{critical_total}",
                "empty_challenges": empty_challenges}
