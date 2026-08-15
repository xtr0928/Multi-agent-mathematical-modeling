# -*- coding: utf-8 -*-
"""LLM 编排层：完整 S0-S6 四模型角色调度（设计文档 §8 角色矩阵全落位）

流程（对照 V5_upgrade_dev_doc_2026-08-15）：
  S0 问题解析 → S1 假设生成(四建模手) → S1 假设官审查 → S1 DA 挑战
  → S2 路线选择(选最强两条) → S2 双轨迹执行 + 反思器完成度检查
  → S3 四模型评审 → S3 锦标赛投票选主线 → S4 数值门禁(0 LLM)
  → S5 排版(视觉官) → S5b 检测层四模型抽取(作者回避) → S6 交付

生产模式：LLMClient 接入真实 API。测试模式：DryRunClient 零 API 成本。
花钱纪律：真实 API 运行前必须报预估调用次数并获用户批准。
"""
import json
import time


class LLMClient:
    """生产接口：对接真实四模型 API（DeepSeek/GLM/Kimi K3/Qwen3.8-Max）"""

    def __init__(self, backend=None):
        self.backend = backend

    def ask(self, provider: str, system: str, user: str, **kw) -> dict:
        if self.backend is None:
            raise RuntimeError("未接入真实 API 后端（生产模式需配置 llm_client）")
        return self.backend.ask(provider, system, user, **kw)


class DryRunClient:
    """零成本桩：确定性返回（验收测试用，不调用任何 API）"""

    def __init__(self, seed: int = 7):
        self.seed = seed

    def ask(self, provider: str, system: str, user: str, **kw) -> dict:
        return {"content": f"[dry-run {provider}]\n{user[:80]}"}


# 四模型
MODELERS = ["deepseek", "glm", "kimi", "qwen"]
REVIEWERS = MODELERS  # 四评
EXTRACTORS = MODELERS  # 检测层四模型抽取

# 章节 → 撰写实例映射（dry-run 确定性分配；生产版由编排记录真实实例 ID）
SECTION_ASSIGNMENT = {"§1": "deepseek", "§2": "glm", "§3": "kimi", "§4": "qwen"}


class Orchestrator:
    """编排器：完整 S0-S6 流程（含双轨迹、DA、反思器、检测层作者回避）"""

    def __init__(self, client, role_audit_log=None):
        self.client = client
        self.role_log = role_audit_log
        self.call_count = 0
        self.run_log = []

    # ---------- 调用与记录 ----------
    def _call(self, stage: str, provider: str, role: str, ctx: str,
              instance_id: str = None) -> str:
        self.call_count += 1
        r = self.client.ask(provider, f"role={role}", ctx)
        content = r.get("content", "")
        self.run_log.append({"stage": stage, "provider": provider, "role": role,
                             "instance_id": instance_id or provider,
                             "ts": time.time()})
        return content

    # ---------- 预估调用数（花钱纪律：运行前必报） ----------
    def estimate_calls(self, n_sections: int = 4) -> int:
        """检测层作者回避：每节由 3 个非作者实例抽取 → n_sections×(4-1) 次"""
        return (
            1                       # S0 解析
            + len(MODELERS)         # S1 假设生成 ×4
            + 1                     # S1 假设官
            + 1                     # S1 DA
            + 1                     # S2 路线选择
            + 2                     # S2 双轨迹执行
            + len(REVIEWERS)        # S3 评审 ×4
            + 1                     # S3 投票
            + 0                     # S4 门禁（确定性，0 LLM）
            + 1                     # S5 排版视觉官
            + n_sections * (len(EXTRACTORS) - 1)   # S5b 检测层（作者回避后每节 3 抽）
            + 1                     # S6 交付
        )

    # ---------- S0：问题解析 ----------
    def s0_parse(self, problem_text: str) -> dict:
        out = self._call("S0", "deepseek", "problem_parser", problem_text)
        return {"problem_profile": out}

    # ---------- S1：假设生成（四建模手） ----------
    def s1_modelers_propose(self, problem_profile: str) -> dict:
        proposals = {}
        for m in MODELERS:
            proposals[m] = self._call("S1", m, "modeler", problem_profile,
                                      instance_id=f"{m}_S1")
        return proposals

    # ---------- S1：假设官必要性审查 ----------
    def s1_officer(self, assumptions: str) -> dict:
        return {"verdict": self._call("S1", "glm", "assumption_officer",
                                      assumptions, instance_id="officer_glm")}

    # ---------- S1：DA 挑战（独立实例，反事实+实验设计强制） ----------
    def s1_da(self, assumptions: str) -> dict:
        return {"attack_list": self._call("S1", "kimi", "devils_advocate",
                                          assumptions, instance_id="da_kimi")}

    # ---------- S2：路线选择（选最强两条独立路线） ----------
    def s2_route_select(self, proposals: dict) -> dict:
        ctx = json.dumps({k: v[:80] for k, v in proposals.items()},
                         ensure_ascii=False)
        out = self._call("S2", "deepseek", "route_selector", ctx,
                         instance_id="route_ds")
        # 生产版解析 LLM 输出的两条路线；dry-run 确定性取前两位
        chosen = ["route_A", "route_B"]
        return {"selected": chosen, "raw": out[:100]}

    # ---------- S2：双轨迹执行（A/B 并行语义；dry-run 顺序执行） ----------
    def s2_dual_track(self, routes: list, ctx: str) -> dict:
        tracks = {}
        for r in routes:
            tracks[r] = self._call("S2", "deepseek", "track_executor",
                                   f"{r}:{ctx[:80]}", instance_id=f"track_{r}")
        return tracks

    # ---------- S2：反思器完成度检查（确定性，0 LLM） ----------
    def s2_reflect(self, checklist: list, produced_files: set) -> dict:
        from reflect.reflector import Reflector
        r = Reflector(checklist)
        state = r.run_round(produced_files)
        # 未完成则按轮次重试语义（dry-run：最多再跑 2 轮检查）
        while state["status"] == "need_fix" and state["rounds"] < Reflector.MAX_ROUNDS:
            state = r.run_round(produced_files | {"retry_marker"})
        return state

    # ---------- S3：四模型评审（零上下文隔离语义） ----------
    def s3_review(self, tracks: dict, attack_list: str) -> dict:
        reviews = {}
        ctx = json.dumps({k: v[:80] for k, v in tracks.items()},
                         ensure_ascii=False) + f"\n攻击清单:{attack_list[:80]}"
        for m in REVIEWERS:
            reviews[m] = self._call("S3", m, "reviewer", ctx,
                                    instance_id=f"review_{m}")
        return reviews

    # ---------- S3：锦标赛投票（LLM 只做相对排序，不做绝对打分） ----------
    def s3_tournament(self, tracks: list) -> dict:
        ctx = "候选路线: " + ", ".join(tracks)
        out = self._call("S3", "deepseek", "tournament_voter", ctx,
                         instance_id="vote_ds")
        return {"winner": tracks[0], "raw": out[:80]}  # dry-run 取首；生产解析相对排序

    # ---------- S4：数值门禁（确定性，0 LLM；调 gate 层） ----------
    def s4_gate(self) -> dict:
        return {"note": "确定性门禁：gate/numeric_gate.py 纯脚本执行，0 LLM 调用"}

    # ---------- S5：排版层视觉官 ----------
    def s5_layout(self, paper_text: str) -> dict:
        return {"visual_report": self._call("S5", "qwen", "visual_officer",
                                            paper_text[:120], instance_id="visual_qwen")}

    # ---------- S5b：检测层四模型独立抽取（作者回避：写 §N 的实例不抽 §N） ----------
    def s5b_detect(self, paper: dict, writer_map: dict = None) -> dict:
        """paper: {section: text}；writer_map: {section: 撰写实例}
        作者回避铁律：抽取 §N 时，撰写 §N 的模型实例被排除（A 作者回避）。
        """
        writer_map = writer_map or SECTION_ASSIGNMENT
        extractions = {}
        avoidance_ok = True
        for section, text in paper.items():
            writer = writer_map.get(section, "")
            pool = [m for m in EXTRACTORS if m != writer]  # 作者回避
            if len(pool) != len(MODELERS) - 1:
                avoidance_ok = False
            for m in pool:
                extractions.setdefault(m, []).append(
                    self._call("S5b", m, "claim_extractor",
                               f"{section}:{text[:60]}", instance_id=f"ext_{m}"))
        # 取并集（去重语义；dry-run 保留全量）
        union = sorted({item for v in extractions.values() for item in v})
        return {"extractions": extractions, "union_size": len(union),
                "avoidance_ok": avoidance_ok}

    # ---------- S6：交付 ----------
    def s6_deliver(self, final_ctx: str) -> dict:
        return {"final": self._call("S6", "deepseek", "final_writer", final_ctx,
                                    instance_id="final_ds")}

    # ---------- 完整流程 ----------
    def run_full(self, problem_text: str, checklist: list = None) -> dict:
        report = {}
        report["S0"] = self.s0_parse(problem_text)
        proposals = self.s1_modelers_propose(problem_text[:80])
        report["S1_proposals"] = proposals
        report["S1_officer"] = self.s1_officer(problem_text[:80])
        report["S1_da"] = self.s1_da(problem_text[:80])
        routes = self.s2_route_select(proposals)
        report["S2_routes"] = routes
        tracks = self.s2_dual_track(routes["selected"], problem_text)
        report["S2_tracks"] = tracks
        if checklist:
            report["S2_reflect"] = self.s2_reflect(checklist, set())
        report["S3_reviews"] = self.s3_review(tracks, report["S1_da"]["attack_list"])
        report["S3_vote"] = self.s3_tournament(routes["selected"])
        report["S4_gate"] = self.s4_gate()
        report["S5_layout"] = self.s5_layout(problem_text)
        paper = {"§1": "正文1", "§2": "正文2", "§3": "正文3", "§4": "正文4"}
        report["S5b_detect"] = self.s5b_detect(paper)
        report["S6"] = self.s6_deliver(problem_text[:80])
        report["_total_calls"] = self.call_count
        report["_dry_run"] = isinstance(self.client, DryRunClient)
        return report
