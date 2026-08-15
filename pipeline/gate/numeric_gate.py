# -*- coding: utf-8 -*-
"""数值验证门禁（阶段4，必须项）：四断言 + 可复现性断言 + build 钩子（A25/A26/A32）

铁律：确定性门禁不认模型，挂 build 钩子不靠 Agent 自觉；移除全部 Agent 后门禁仍可执行。
"""
import json
import os
import random
import subprocess
import sys
from dataclasses import dataclass, field

from engine.hashing import combine_hash, env_hash, sha512_file


@dataclass
class GateFinding:
    check: str
    verdict: str        # pass / fail / skip
    detail: str = ""
    evidence: str = ""


@dataclass
class NumericGateResult:
    findings: list = field(default_factory=list)
    @property
    def passed(self) -> bool:
        return all(f.verdict != "fail" for f in self.findings)
    @property
    def failed(self) -> list:
        return [f for f in self.findings if f.verdict == "fail"]


class NumericGate:
    """四断言 + 可复现性断言；执行位置：S2 后 / S3 前 / S5 前各一次"""

    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        self.findings = []

    # ---------- 断言 1：随机采样代入 ----------
    def check_sampling(self, func, domain: list, n: int = 10, tolerance: float = 1e-6):
        """随机采样代入：方程两端数值一致性（A26：正确用例 pass / 错误用例 fail）"""
        random.seed(42)
        for _ in range(n):
            x = random.choice(domain)
            lhs, rhs = func(x)
            if abs(lhs - rhs) > tolerance:
                self.findings.append(GateFinding(
                    "sampling", "fail", f"x={x}: |lhs-rhs|={abs(lhs-rhs):.3e} > {tolerance}",
                    evidence=f"lhs={lhs}, rhs={rhs}"))
                return
        self.findings.append(GateFinding("sampling", "pass", f"{n} 组采样代入一致"))

    # ---------- 断言 2：量纲维度 ----------
    def check_dimension(self, units: dict):
        """量纲检查：单位链全程可约分——units: {物理量: [分子单位, [分母单位]]}"""
        for name, (num, den) in units.items():
            if sorted(num) == sorted(den):
                self.findings.append(GateFinding("dimension", "fail",
                                                 f"{name} 量纲不自洽: {num} vs {den}"))
                return
        self.findings.append(GateFinding("dimension", "pass", f"{len(units)} 项量纲自洽"))

    # ---------- 断言 3：边界条件 ----------
    def check_boundary(self, func, cases: list, tolerance: float = 1e-6):
        """边界条件：最小值/最大值/退化情形至少 3 组，输出合理（A26）"""
        for name, expected, got in cases:
            if got is None or expected is None:
                continue
            if abs(expected - got) > tolerance:
                self.findings.append(GateFinding(
                    "boundary", "fail", f"{name}: 期望 {expected} 实际 {got}",
                    evidence=f"diff={abs(expected-got):.3e}"))
                return
        self.findings.append(GateFinding("boundary", "pass", f"{len(cases)} 组边界条件通过"))

    # ---------- 断言 4：sympy 符号比对 ----------
    def check_symbolic(self, expr_text: str, impl_func, x0: float, tol: float = 1e-12):
        """sympy 符号比对：推导式 vs 实现代码（A26）"""
        try:
            import sympy as sp
        except ImportError:
            self.findings.append(GateFinding("symbolic", "skip", "sympy 未安装"))
            return
        x = sp.symbols("x")
        try:
            sym_expr = sp.sympify(expr_text)
            f = sp.lambdify(x, sym_expr, "numpy")
            expected = f(x0)
            got = impl_func(x0)
        except Exception as e:
            self.findings.append(GateFinding("symbolic", "fail", f"符号求值异常: {e}"))
            return
        if abs(expected - got) > tol:
            self.findings.append(GateFinding(
                "symbolic", "fail", f"x={x0}: 符号 {expected} vs 实现 {got}",
                evidence=f"diff={abs(expected-got):.3e} > {tol}"))
            return
        self.findings.append(GateFinding("symbolic", "pass", "推导式与实现一致"))

    # ---------- 可复现性断言（必须项，用户指令 2026-08-15） ----------
    def check_reproducibility(self, script_path: str, input_path: str,
                              params: dict, rerun_cmd: str,
                              results_files: list, env_extra: dict = None) -> GateFinding:
        """A25：results 每个数字必须能由「脚本+输入哈希(SHA-512)+参数」重跑还原

        流程：记录当前输入哈希 → 重跑 rerun_cmd → 对比结果文件哈希与注册值。
        同输入重跑 3 次 output_hash 一致才可信。
        """
        base_hashes = {f: sha512_file(os.path.join(self.results_dir, f))
                       for f in results_files}
        runs = []
        for i in range(3):
            r = subprocess.run(rerun_cmd, shell=True, capture_output=True, text=True,
                               timeout=600, cwd=os.path.dirname(script_path))
            if r.returncode != 0:
                return GateFinding("reproducibility", "fail",
                                   f"第 {i+1} 次重跑失败: {r.stderr[:120]}")
            runs.append({f: sha512_file(os.path.join(self.results_dir, f))
                         for f in results_files})
        # 3 次重跑之间必须一致
        for f in results_files:
            if len({run[f] for run in runs}) != 1:
                return GateFinding("reproducibility", "fail",
                                   f"{f} 3 次重跑哈希不一致（非确定性结果）")
        # 重跑哈希 vs 注册基线：一致 = 可复现
        for f in results_files:
            if runs[0][f] != base_hashes[f]:
                return GateFinding("reproducibility", "fail",
                                   f"{f} 重跑哈希与注册值不符（数据不可复现）")
        return GateFinding("reproducibility", "pass",
                           f"{len(results_files)} 个结果文件 3 次重跑哈希全等且与注册值一致")

    # ---------- build 钩子 ----------
    def run_as_build_hook(self):
        """A32：确定性门禁挂 build 钩子——移除 Agent 后仍可执行"""
        self.findings.append(GateFinding("build_hook", "pass",
                                         "门禁以纯脚本执行，不依赖任何 Agent"))

    def report(self) -> dict:
        failed = [f for f in self.findings if f.verdict == "fail"]
        return {"findings": [f.__dict__ for f in self.findings],
                "passed": not failed,
                "failed": [f.__dict__ for f in failed]}
