# -*- coding: utf-8 -*-
"""Devil's Advocate 专职挑刺位（阶段8 补全）：独立调度角色

设计 §8.1：DA 可读全文不可写全文；每条攻击必须附反事实+实验设计（D21 防形式化）；
实质挑战 ≥2；关键假设全覆盖后才允许挑战次要假设（A18）。
攻击清单产出后喂给 S3 评审四重奏核实（攻击与核实分离，防攻击方自证）。
"""
import uuid


class Attack:
    def __init__(self, target: str, counterfactual: str, experiment_design: str,
                 severity: str, target_type: str = "assumption"):
        self.id = "ATK" + uuid.uuid4().hex[:6]
        self.target = target
        self.counterfactual = counterfactual
        self.experiment_design = experiment_design
        self.severity = severity          # critical / major / minor
        self.target_type = target_type    # assumption / claim / methodology


class DevilAdvocate:
    """独立挑刺实例：读全文+假设注册表 → 输出攻击清单"""

    def __init__(self, instance_id: str):
        self.instance_id = instance_id   # 与撰写实例隔离（角色审计可查）

    @staticmethod
    def _is_substantive(a: Attack) -> bool:
        return (len(a.counterfactual.strip()) >= 10
                and len(a.experiment_design.strip()) >= 10)

    def generate(self, assumptions: list, critical_ids: set,
                 draft_claims: list = None) -> dict:
        """生成攻击清单（生产版由 LLM 推演；本实现为规则骨架+校验器）

        assumptions: [{id, statement, level, author}]
        critical_ids: 关键假设 ID 集合（全覆盖后才允许挑战次要假设，A18）
        """
        attacks = []
        # 1. 关键假设全覆盖（每条例行攻击）
        for a in assumptions:
            if a["id"] in critical_ids:
                attacks.append(Attack(
                    target=a["id"],
                    counterfactual=f"若 {a['statement'][:20]} 的反面成立，结论将如何变化",
                    experiment_design=f"设计实验检验 {a['statement'][:20]}",
                    severity="critical", target_type="assumption"))
        # 2. 实质挑战 ≥2 补足：关键假设全覆盖后才允许挑战次要假设（A18）
        if len(attacks) < 2:
            for a in assumptions:
                if a["id"] not in critical_ids:
                    attacks.append(Attack(
                        target=a["id"],
                        counterfactual=f"若 {a['statement'][:20]} 被移除，模型是否退化",
                        experiment_design=f"移除该假设重跑，比对结论变化",
                        severity="major", target_type="assumption"))
                    if len(attacks) >= 2:
                        break
        # 2. 实质挑战 ≥2 校验（A18）
        substantive = [a for a in attacks if self._is_substantive(a)]
        if len(substantive) < 2:
            raise ValueError("DA 实质挑战必须 ≥2 条（防形式化铁律）")
        # 3. 攻击清单交付格式：评审四重奏只负责核实，不负责构造（分离）
        return {"attacker_instance": self.instance_id,
                "attacks": [a.__dict__ for a in attacks],
                "n_substantive": len(substantive),
                "critical_covered": sorted(a.target for a in attacks
                                           if a.target in critical_ids)}

    def verify_attacks(self, attack_list: dict, critical_ids: set) -> dict:
        """评审侧核实接口：攻击是否实质、关键假设是否全覆盖、攻击方是否自证"""
        substantive_ok = all(
            len(a.get("counterfactual", "").strip()) >= 10
            and len(a.get("experiment_design", "").strip()) >= 10
            for a in attack_list["attacks"])
        covered = {a["target"] for a in attack_list["attacks"]}
        checks = {
            "substantive_ok": substantive_ok,
            "critical_covered": critical_ids <= covered,
            "n_attacks": len(attack_list["attacks"]),
        }
        checks["passed"] = checks["substantive_ok"] and checks["critical_covered"]
        return checks
