# -*- coding: utf-8 -*-
"""角色隔离审计（阶段8）：实例 ID 日志审计——写评分离/作者回避/评审零上下文（A28）

铁律：评审实例≠撰写实例；评审无撰写上下文；假设审查者≠提交者；Qwen 不查自己的排版。
系统强制：审查者由非作者池分配，日志层面使「作者=审查者」不可能发生。
"""
import json
import os
import time
from dataclasses import dataclass, field


@dataclass
class RoleEvent:
    instance_id: str
    role: str            # writer/reviewer/assumption_submitter/assumption_officer/da/visual
    model: str
    target: str          # 对象：章节 §N / claim_id / figure_id / assumption_id
    action: str
    ts: float = field(default_factory=time.time)


class RoleAuditLog:
    """append-only 角色事件日志"""

    def __init__(self, path: str):
        self.path = path

    def record(self, e: RoleEvent):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(e.__dict__, ensure_ascii=False) + "\n")

    def events(self) -> list:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(RoleEvent(**json.loads(line)))
        return out


class RoleAuditor:
    """A28：四类隔离检查"""

    @staticmethod
    def check_writer_reviewer_separation(events: list) -> list:
        """写 §N 的实例不得评审 §N（零上下文隔离的硬底线）"""
        violations = []
        writers = {(e.instance_id, e.target) for e in events if e.role == "writer"}
        for e in events:
            if e.role == "reviewer" and (e.instance_id, e.target) in writers:
                violations.append(
                    f"评审实例 {e.instance_id} 评审了自己撰写的 {e.target}")
        return violations

    @staticmethod
    def check_assumption_author_avoidance(events: list) -> list:
        """假设审查者 ≠ 提交者（A18 作者回避）"""
        violations = []
        submitters = {(e.instance_id, e.target) for e in events
                      if e.role == "assumption_submitter"}
        for e in events:
            if e.role in ("assumption_officer", "da") and \
                    (e.instance_id, e.target) in submitters:
                violations.append(
                    f"{e.role} 实例 {e.instance_id} 审查了自己提交的假设 {e.target}")
        return violations

    @staticmethod
    def check_visual_self_review(events: list) -> list:
        """Qwen 视觉官不检查自己的排版（视觉官实例与建模手实例隔离）"""
        violations = []
        for e in events:
            if e.role == "visual":
                writers = {(w.instance_id, w.target) for w in events
                           if w.role == "writer" and w.target.startswith("fig:")}
                # 视觉官审查的图必须是他人实例产出的图
                if (e.instance_id, e.target) in {(w[0], e.target) for w in
                                                 [(x.instance_id, x.target) for x in events
                                                  if x.role == "writer"]}:
                    violations.append(f"视觉官 {e.instance_id} 审查了自己的图 {e.target}")
        return violations

    @staticmethod
    def check_zero_context(events: list) -> list:
        """评审实例不携带撰写实例上下文：同一评审实例在同一 session 中
        不得先 writer 后 reviewer（跨角色实例复用即污染）"""
        violations = []
        by_instance = {}
        for e in events:
            by_instance.setdefault(e.instance_id, set()).add(e.role)
        for iid, roles in by_instance.items():
            if "writer" in roles and "reviewer" in roles:
                violations.append(f"实例 {iid} 同时承担 writer 与 reviewer（上下文污染）")
        return violations

    def audit(self, log: "RoleAuditLog") -> dict:
        """对一份角色事件日志执行四类隔离检查（A28）"""
        events = log.events()
        v = {}
        v["writer_reviewer"] = self.check_writer_reviewer_separation(events)
        v["assumption_avoidance"] = self.check_assumption_author_avoidance(events)
        v["visual_self_review"] = self.check_visual_self_review(events)
        v["zero_context"] = self.check_zero_context(events)
        v["passed"] = not any(v.values())
        return v
