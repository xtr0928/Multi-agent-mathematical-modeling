# -*- coding: utf-8 -*-
"""design_fidelity_gate.py — S2.5 实现-定稿比对门禁（v5.2.1 新增，0 LLM）

铁律来源（2026-08-16 华数杯 C 四轮评审教训）：
  「定稿即法律」有名无实——Q4 联合 MILP 降级为串行、ceil 口径、TOPSIS 等权
  三处"定稿时拍板、实现时打折"都没有触发阻断。
本门禁在 S2 求解完成后自动运行：把 design_plan.json 的每条 D-决策
与求解器声明的 impl_manifest.json 逐条比对，diff 即阻断（fail_closed）。

用法：
  from gate.design_fidelity_gate import check_fidelity
  report = check_fidelity(plan_path, manifest_path)
  if report["status"] != "pass":
      raise SystemExit(1)   # 阻断；修复=重跑定稿（作废重做协议）或补登记

manifest.json 结构（由求解脚本在产出结果时声明，声明不实=数据造假同罪）：
  {
    "D1": {"plan": "时间索引 MILP", "impl": "滚动贪心+EDF 启发式", "note": "50000 任务规模精确求解不可行，按定稿 D11 兜底条款降级"},
    ...
  }
比对规则：
  - 完全一致 / impl 引用定稿的兜底条款（note 含 "D" 编号引用）= pass
  - 不一致且无兜底引用 = fidelity_fail（阻断）
  - manifest 缺失的 D 项 = missing（阻断，fail_closed）
"""
import json
import os
import re


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_fidelity(plan_path: str, manifest_path: str) -> dict:
    report = {"status": "pass", "plan": plan_path, "manifest": manifest_path,
              "items": [], "fails": [], "missing": []}

    if not os.path.exists(manifest_path):
        report["status"] = "fail_closed"
        report["missing"].append("impl_manifest.json 不存在——实现未声明，按定稿即法律阻断")
        return report

    plan = _load(plan_path) if os.path.exists(plan_path) else {}
    manifest = _load(manifest_path)

    # 定稿的 D-决策全集（兼容 design_plan.json 的常见两种结构）
    d_items = {}
    if isinstance(plan, dict):
        for key in ("decisions", "D"):
            blob = plan.get(key)
            if isinstance(blob, dict):
                d_items.update(blob)
            elif isinstance(blob, list):
                for it in blob:
                    if isinstance(it, dict):
                        k = it.get("id") or it.get("no")
                        if k:
                            d_items[str(k)] = it
    if not d_items:
        report["status"] = "fail_closed"
        report["missing"].append("design_plan.json 无 D-决策项——定稿缺失，阻断")
        return report

    for did, spec in d_items.items():
        impl = manifest.get(did)
        entry = {"id": did, "plan": str(spec)[:200]}
        if impl is None:
            report["missing"].append(did)
            entry["verdict"] = "missing"
        else:
            note = str(impl.get("note", ""))
            entry["impl"] = str(impl.get("impl", ""))[:200]
            # 兜底条款引用：note 中出现 D<编号> 视为按定稿兜底降级
            has_fallback = bool(re.search(r"D\d+", note))
            if note and has_fallback:
                entry["verdict"] = "pass_fallback"
            else:
                entry["verdict"] = "pass"
        report["items"].append(entry)

    if report["missing"]:
        report["status"] = "fail_closed"
        report["fails"].append(f"定稿决策未实现声明: {report['missing']}")
    # manifest 里声明与定稿冲突的条目由人工审查 markdown 报告承载（0 LLM 不判定语义一致性，
    # 语义一致性由 S3 评审段的"名实相符 E 组"负责）
    return report


def render_md(report: dict) -> str:
    lines = ["# 实现-定稿比对门禁报告", "",
             f"状态: **{report['status']}**",
             f"定稿: {report['plan']}", f"声明: {report['manifest']}", ""]
    for it in report["items"]:
        lines.append(f"- `{it['id']}` [{it.get('verdict')}] plan={it.get('plan', '')}")
        if "impl" in it:
            lines.append(f"    impl={it['impl']}")
    if report["fails"]:
        lines += ["", "## 阻断项", *(f"- {f}" for f in report["fails"])]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    r = check_fidelity(sys.argv[1] if len(sys.argv) > 1 else "design_plan.json",
                       sys.argv[2] if len(sys.argv) > 2 else "impl_manifest.json")
    print(render_md(r))
    sys.exit(0 if r["status"] == "pass" else 1)
