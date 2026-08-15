# -*- coding: utf-8 -*-
"""LLM 编排层：S0-S6 四模型角色调用框架（设计文档 §8 角色矩阵）

生产模式：LLMClient 接入真实 API（llm_client 四模型：DS/GLM/Kimi K3/Qwen3.8-Max）。
测试模式：DryRunClient 确定性桩——零 API 成本跑通全流程（本次验收用它）。
花钱纪律：任何真实 API 运行必须先报预估调用次数并获用户批准。
"""
import json
import os
import time


class LLMClient:
    """生产接口：对接真实四模型 API（DeepSeek/GLM/Kimi K3/Qwen3.8-Max）"""

    def __init__(self, backend=None):
        # backend: 实现 ask(provider, system, user, **kw) -> {"content": str} 的对象
        self.backend = backend

    def ask(self, provider: str, system: str, user: str, **kw) -> dict:
        if self.backend is None:
            raise RuntimeError("未接入真实 API 后端（生产模式需配置 llm_client）")
        return self.backend.ask(provider, system, user, **kw)


class DryRunClient:
    """零成本桩：确定性返回，跑通编排骨架（验收测试用，不调用任何 API）"""

    def ask(self, provider: str, system: str, user: str, **kw) -> dict:
        return {"content": f"[dry-run {provider}]\n{user[:100]}"}


ROLES = {
    "S0": {"providers": ["deepseek"], "role": "problem_parser"},
    "S1_assumption": {"providers": ["deepseek", "glm", "kimi", "qwen"],
                      "role": "modeler_quartet"},
    "S1_officer": {"providers": ["glm"], "role": "assumption_officer"},
    "S2_modeling": {"providers": ["deepseek", "glm", "kimi", "qwen"],
                    "role": "modeler_quartet"},
    "S3_review": {"providers": ["deepseek", "glm", "kimi", "qwen"],
                  "role": "review_quartet"},
    "S4_gate": {"providers": [], "role": "deterministic_gate"},   # 无 LLM：确定性
    "S5_layout": {"providers": ["qwen"], "role": "visual_officer"},
    "S6_deliver": {"providers": ["deepseek"], "role": "final_writer"},
}


class Orchestrator:
    """编排器：按角色矩阵调度四模型；生产=LLMClient，测试=DryRunClient（零成本）"""

    def __init__(self, client, role_audit_log=None):
        self.client = client
        self.role_log = role_audit_log
        self.call_count = 0
        self.run_log = []

    def run_stage(self, stage: str, ctx: str) -> dict:
        """执行一个 stage 的全部角色调用，记录角色事件与调用数"""
        spec = ROLES[stage]
        outputs = {}
        for provider in spec["providers"]:
            self.call_count += 1
            r = self.client.ask(provider, f"role={spec['role']}", ctx)
            outputs[provider] = r.get("content", "")[:200]
            self.run_log.append({"stage": stage, "provider": provider,
                                 "role": spec["role"], "ts": time.time()})
        return outputs

    def estimate_calls(self, stages: list) -> int:
        """花钱纪律：任何真实 API 运行前必须报预估调用次数"""
        return sum(len(ROLES[s]["providers"]) for s in stages)

    def run_full(self, ctx: str, stages: list = None) -> dict:
        stages = stages or list(ROLES.keys())
        report = {}
        for s in stages:
            report[s] = self.run_stage(s, ctx)
        report["_total_calls"] = self.call_count
        report["_dry_run"] = isinstance(self.client, DryRunClient)
        return report
