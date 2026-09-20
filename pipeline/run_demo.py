# -*- coding: utf-8 -*-
"""数学管线生产模式运行器：S0-S6 全流程（真实四模型 API）。

用法：
    cd pipeline
    python run_demo.py --problem ../docs/2026_MCM-ICM_Problems/<题目>.txt [--owner-mode auto]
    python run_demo.py --problem my_problem.txt --owner-mode semi   # 拍板者暂停等你（博士确认）

花钱纪律（README 铁律）：真实 API 运行前打印预估调用次数并给出确认提示。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_bridge import make_backend          # noqa: E402
from orchestrator import Orchestrator, DryRunClient  # noqa: E402


def build_client(real: bool, dry_seed: int = 7):
    if real:
        return Orchestrator(make_backend())
    return Orchestrator(DryRunClient(seed=dry_seed))


def main():
    ap = argparse.ArgumentParser(description="数学建模管线 S0-S6 运行器")
    ap.add_argument("--problem", required=True, help="题目文本文件（.txt/.md/.pdf 文本层）")
    ap.add_argument("--dry-run", action="store_true", help="零成本 DryRun（不调 API）")
    ap.add_argument("--owner-mode", default="auto", choices=["auto", "semi"])
    ap.add_argument("--baseline", type=float, default=50.0,
                    help="S7 回归门基线（华数杯 C 基线=50）")
    args = ap.parse_args()

    if not os.path.exists(args.problem):
        print(f"题目不存在: {args.problem}")
        sys.exit(1)
    with open(args.problem, encoding="utf-8") as f:
        problem_text = f.read()

    oc = build_client(real=not args.dry_run)
    if not args.dry_run:
        n = oc.estimate_calls()
        print(f"[成本提醒] 本次为真实 API 运行，预估 LLM 调用约 {n} 次（S0-S6）。")
        confirm = input("按 Enter 开始；输 n 取消: ").strip().lower()
        if confirm == "n":
            print("已取消。")
            sys.exit(0)
    else:
        print("[DryRun] 零成本桩模式，输出为确定性占位内容。")

    report = oc.run_full(problem_text, owner_mode=args.owner_mode,
                         score_baseline=args.baseline)
    # 汇总输出：阶段 → 摘要（不 dump 超长正文）
    summary = {}
    for k, v in report.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and "raw" in v:
            summary[k] = v["raw"]
        elif isinstance(v, str):
            summary[k] = v[:200]
        else:
            summary[k] = f"<{type(v).__name__} keys={list(v.keys()) if isinstance(v, dict) else ''}>"
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    state_path = os.path.join(os.path.dirname(args.problem), "run_report.json")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n完整报告: {state_path}")


if __name__ == "__main__":
    main()
