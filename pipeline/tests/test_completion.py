# -*- coding: utf-8 -*-
"""补全模块验收：反思器 / DA / 跨语言 KS / 完整编排层（双轨迹+检测层作者回避）"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reflect.reflector import (CompletionChecker, ErrorReflector,
                               HotLoopRecommender, Reflector)
from reflect.devils_advocate import DevilAdvocate, Attack
from cpp.ks_compare import ks_compare, gen_rng_file, load_rng_file
from orchestrator import Orchestrator, DryRunClient, MODELERS


def test_completion_checker():
    """完成度检查：缺产物不通过；补齐后通过"""
    cc = CompletionChecker([
        {"task": "数据清洗", "expected_product": "clean.csv",
         "check": lambda files: "clean.csv" in files},
        {"task": "模型拟合", "expected_product": "results.json",
         "check": lambda files: "results.json" in files},
    ])
    r1 = cc.check(set())
    assert not r1["complete"] and len(r1["missing"]) == 2
    r2 = cc.check({"clean.csv", "results.json"})
    assert r2["complete"] and r2["completion_rate"] == 1.0


def test_reflector_rounds():
    """反思器：最多 3 轮，不通过则 exhausted"""
    checklist = [{"task": "结果落盘", "expected_product": "results.json",
                  "check": lambda f: "results.json" in f}]
    r = Reflector(checklist)
    for _ in range(Reflector.MAX_ROUNDS - 1):
        state = r.run_round(set())
        assert state["status"] == "need_fix"
    state = r.run_round(set())
    assert state["status"] == "exhausted" and state["rounds"] == 3
    # 有产物 → complete
    r2 = Reflector(checklist)
    assert r2.run_round({"results.json"})["status"] == "complete"


def test_error_reflector_hints():
    er = ErrorReflector()
    r = er.reflect("ModuleNotFoundError: No module named 'pandas'", "import pandas as pd")
    assert "缺 import" in r["hint_categories"]
    assert "原因 + 修正" in r["required_output"]


def test_hot_loop_recommender():
    hr = HotLoopRecommender()
    code = "for i in range(1000000):\n    for j in range(1000000):\n        x = i + j"
    rec = hr.recommend(code)
    assert rec["hot_loop_candidate"] is True
    assert hr.recommend("x = 1 + 1")["hot_loop_candidate"] is False


def test_da_substantive_and_critical():
    """DA：实质挑战 ≥2 强制 + 关键假设全覆盖 + 攻击核实分离"""
    da = DevilAdvocate(instance_id="da_kimi")
    assumptions = [
        {"id": "H01", "statement": "碳价主导任务迁移", "level": "critical", "author": "modeler_A"},
        {"id": "H02", "statement": "任务到达独立", "level": "important", "author": "modeler_B"},
    ]
    attack_list = da.generate(assumptions, critical_ids={"H01"})
    assert attack_list["n_substantive"] >= 2
    assert attack_list["critical_covered"] == ["H01"]
    # 评审侧核实（攻击与核实分离）
    checks = da.verify_attacks(attack_list, critical_ids={"H01"})
    assert checks["passed"] is True
    # 关键假设缺覆盖 → 不通过
    checks2 = da.verify_attacks(attack_list, critical_ids={"H01", "H03"})
    assert checks2["passed"] is False


def test_ks_compare():
    """跨语言对照：同分布不拒绝；明显不同分布拒绝"""
    import random
    rng1 = random.Random(42)
    a = [rng1.random() for _ in range(500)]
    b = [rng1.random() for _ in range(500)]
    r1 = ks_compare(a, b)
    assert r1["reject_same_distribution"] is False, f"同分布被误拒: {r1}"
    # 明显位移的分布 → 拒绝
    c = [x + 0.5 for x in a]
    r2 = ks_compare(a, c)
    assert r2["reject_same_distribution"] is True, f"异分布未被拒: {r2}"


def test_rng_file_protocol():
    d = tempfile.mkdtemp()
    try:
        p = gen_rng_file(os.path.join(d, "rng.txt"), 100, seed=7)
        vals = load_rng_file(p)
        assert len(vals) == 100
        assert all(0 <= v < 1 for v in vals)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_orchestrator_full_flow():
    """完整编排层：预估调用数 + 全流程 + 双轨迹 + 检测层作者回避"""
    orch = Orchestrator(DryRunClient())
    # 1+4+1+1+1+2+4+1+0+1+12(4节×3抽)+1 = 29
    assert orch.estimate_calls() == 29, orch.estimate_calls()
    rep = orch.run_full("测试赛题文本")
    assert rep["_dry_run"] is True
    assert rep["_total_calls"] == 29, rep["_total_calls"]
    assert rep["S2_routes"]["selected"] == ["route_A", "route_B"], "双轨迹路线选择缺失"
    assert set(rep["S2_tracks"].keys()) == {"route_A", "route_B"}
    assert rep["S3_vote"]["winner"] in ("route_A", "route_B"), "投票无胜者"
    det = rep["S5b_detect"]
    assert det["avoidance_ok"] is True, "检测层作者回避失效"
    # 作者回避验证：每个抽取实例都不抽自己撰写的章节
    from orchestrator import SECTION_ASSIGNMENT
    for sec, writer in SECTION_ASSIGNMENT.items():
        assert writer not in [m for m in MODELERS if m != writer], "回避池构造错误"
        assert writer not in det["extractions"].get(writer, []), \
            f"{writer} 抽取了自己撰写的 {sec}"


def test_orchestrator_with_reflector():
    orch = Orchestrator(DryRunClient())
    checklist = [{"task": "结果落盘", "expected_product": "results.json",
                  "check": lambda f: "results.json" in f}]
    rep = orch.run_full("测试赛题", checklist=checklist)
    assert rep["S2_reflect"]["status"] == "exhausted"  # 空产物 → 3 轮后耗尽


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
