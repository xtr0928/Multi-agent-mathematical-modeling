# -*- coding: utf-8 -*-
"""双状态机：断点恢复（进度状态机，唯一事实源）+ 72h 时间窗（只读不拥有）

铁律（D17/D18）：时间窗状态机只读不拥有；正确性 > 完整性 > 时间窗。
恢复协议（D16）：恢复第一步重放 append-only 变更日志重建 dirty 全集，不信完成标记。
"""
import json
import os
import time

# 72h 时间窗预算（秒）：商议 14% / 双轨迹 42% / 成文 25% 硬保底 / 纠错 ≤20%
TOTAL_BUDGET = 72 * 3600
PHASE_BUDGET = {
    "deliberation": int(TOTAL_BUDGET * 0.14),   # 10.08h
    "dual_track": int(TOTAL_BUDGET * 0.42),     # 30.24h
    "writing": int(TOTAL_BUDGET * 0.25),        # 18h 硬保底
    "correction": int(TOTAL_BUDGET * 0.20),     # 14.4h
}

# 预授权降级清单（D9/A27：凌晨事故不等用户确认）
DEGRADATION_PLAN = {
    "recalc_squeeze": ["dual_to_single", "skip_poly_sensitivity", "layout_to_rules"],
    "recovery_eta": ["cut_edge_sections", "keep_main_results", "risk_flag_submit"],
    "assumption_timeout": ["mark_unverified", "write_limitations", "no_full_scan"],
}


class ProgressStateMachine:
    """进度状态机：checkpoint + append-only 变更日志；唯一事实源"""

    def __init__(self, workdir: str):
        self.workdir = workdir
        os.makedirs(workdir, exist_ok=True)
        self.log_path = os.path.join(workdir, "change_log.jsonl")
        self.ckpt_path = os.path.join(workdir, "checkpoint.json")

    # ---------- append-only 日志 ----------
    def append_log(self, event: dict):
        """变更日志：只追加，禁止改写/删除"""
        event = dict(event)
        event.setdefault("ts", time.time())
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def replay_log(self) -> list:
        """重放日志（恢复第一步）"""
        if not os.path.exists(self.log_path):
            return []
        events = []
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    # ---------- checkpoint ----------
    def checkpoint(self, stage: str, artifact_hashes: dict):
        """每 stage 完成写 checkpoint（A13：恢复后 dirty 集与理论值一致）"""
        ck = {"stage": stage, "artifact_hashes": artifact_hashes,
              "ts": time.time(), "log_len": self._log_len()}
        tmp = self.ckpt_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ck, f, ensure_ascii=False)
        os.rename(tmp, self.ckpt_path)  # 原子发布
        self.append_log({"event": "checkpoint", "stage": stage,
                         "hashes": artifact_hashes})

    def load_checkpoint(self) -> dict:
        if not os.path.exists(self.ckpt_path):
            return None
        with open(self.ckpt_path, encoding="utf-8") as f:
            return json.load(f)

    def _log_len(self) -> int:
        if not os.path.exists(self.log_path):
            return 0
        with open(self.log_path, encoding="utf-8") as f:
            return sum(1 for _ in f)

    # ---------- 恢复协议（开发文档 §7.4） ----------
    def recover(self, current_hashes: dict) -> dict:
        """恢复：重放日志 → 重建 dirty 全集 → 校验哈希 → 输出动作

        current_hashes: {artifact_id: 当前文件哈希}
        返回 {trusted: [...], dirty: [...], stage: 恢复起点}
        核心：完成标记一律不信，只信任哈希匹配的产物（A13/A16）。
        """
        ck = self.load_checkpoint()
        stage = ck["stage"] if ck else "stage0"
        replay = self.replay_log()
        trusted, dirty = [], []
        if ck:
            for aid, h in ck["artifact_hashes"].items():
                if current_hashes.get(aid) == h:
                    trusted.append(aid)
                else:
                    dirty.append(aid)
        # 日志里声明完成但 checkpoint 哈希对不上的 → 也标脏
        for ev in replay:
            if ev.get("event") == "artifact_done":
                aid = ev.get("artifact_id")
                if aid and aid not in trusted and aid not in dirty:
                    if current_hashes.get(aid) == ev.get("hash"):
                        trusted.append(aid)
                    else:
                        dirty.append(aid)
        return {"stage": stage, "trusted": trusted, "dirty": dirty,
                "replayed_events": len(replay)}


class TimeWindowStateMachine:
    """72h 时间窗状态机：只读不拥有（消费进度数据做降级决策）"""

    def __init__(self, started_at: float = None):
        self.started_at = started_at or time.time()

    def elapsed(self) -> float:
        return time.time() - self.started_at

    def remaining(self) -> float:
        return max(0.0, TOTAL_BUDGET - self.elapsed())

    def phase_remaining(self, phase: str) -> float:
        """该阶段剩余预算（简化模型：按比例扣减总剩余）"""
        return PHASE_BUDGET[phase]

    def writing_floor_intact(self) -> bool:
        """成文 25% 硬保底不可压缩：剩余时间必须 ≥ 成文预算"""
        return self.remaining() >= PHASE_BUDGET["writing"]

    def assess(self, progress: dict) -> dict:
        """降级决策（D9）：返回应执行的预授权降级动作列表

        progress: {"recalc_eta_seconds": float, "recovery_eta_seconds": float,
                   "assumption_overtime": bool}
        """
        actions = []
        remaining = self.remaining()
        if progress.get("recalc_eta_seconds", 0) > 0.30 * remaining:
            actions += DEGRADATION_PLAN["recalc_squeeze"]
        if progress.get("recovery_eta_seconds", 0) > PHASE_BUDGET["correction"]:
            actions += DEGRADATION_PLAN["recovery_eta"]
        if progress.get("assumption_overtime"):
            actions += DEGRADATION_PLAN["assumption_timeout"]
        return actions

    def veto_check(self, phase: str, planned_seconds: float) -> bool:
        """铁律优先级：正确性 > 完整性 > 时间窗。允许带风险交付，但成文 25% 不可破。"""
        if phase == "writing":
            return False  # 成文永远不否决
        return planned_seconds > self.remaining() + PHASE_BUDGET["writing"] * 0.5
