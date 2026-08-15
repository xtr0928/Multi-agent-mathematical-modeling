# -*- coding: utf-8 -*-
"""阶段3-8 模块验收测试：状态机恢复(A13/A16) / 假设官(A17/A18) / 门禁(A26/A32) / 排版(A22)"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state.state_machine import ProgressStateMachine, TimeWindowStateMachine, TOTAL_BUDGET
from assumptions.officer import AssumptionOfficer
from gate.numeric_gate import NumericGate
from layout.layout_gate import FigureInventory, FormulaInventory, DensityChecker


def test_A13_recovery():
    """A13：作废传播中途 kill → 恢复后 dirty 集与理论值一致（完成标记不信）"""
    d = tempfile.mkdtemp()
    try:
        sm = ProgressStateMachine(d)
        # checkpoint 声明 artifact a1/a2 完成，哈希 h1/h2
        sm.checkpoint("stage2", {"a1": "h1", "a2": "h2"})
        sm.append_log({"event": "artifact_done", "artifact_id": "a3", "hash": "h3"})
        # 当前实际：a1 匹配，a2 已被修改，a3 存在且匹配
        cur = {"a1": "h1", "a2": "h2_modified", "a3": "h3", "a4": "h4"}
        r = sm.recover(cur)
        assert r["trusted"] == ["a1", "a3"], f"信任集错误: {r}"
        assert r["dirty"] == ["a2"], f"脏集错误: {r['dirty']}"
        assert r["replayed_events"] == 2
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_A16_half_done_artifact():
    """A16：checkpoint 声明完成但实际哈希不符 → 恢复时认作 dirty 而非完成"""
    d = tempfile.mkdtemp()
    try:
        sm = ProgressStateMachine(d)
        sm.checkpoint("stage3", {"out.json": "correct_hash"})
        # 实际文件哈希不符（半成品/被改）→ dirty
        r = sm.recover({"out.json": "half_written"})
        assert r["dirty"] == ["out.json"] and r["trusted"] == []
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_time_window():
    """时间窗：成文 25% 硬保底不可压缩；预授权降级触发"""
    tw = TimeWindowStateMachine()
    assert tw.remaining() > TOTAL_BUDGET * 0.99
    actions = tw.assess({"recalc_eta_seconds": TOTAL_BUDGET * 0.4})
    assert "dual_to_single" in actions, "重算挤占 >30% 应触发降级"
    # 成文永不否决
    assert tw.veto_check("writing", 999999) is False


def test_A18_assumption_officer():
    """A18：作者回避强制 + 挑战防形式化 + 关键假设敏感度覆盖"""
    d = tempfile.mkdtemp()
    try:
        ao = AssumptionOfficer(os.path.join(d, "assumptions.json"))
        a = ao.register("碳价主导任务迁移", author="modeler_A", level="critical")
        # 作者回避：提交者不得审查
        try:
            ao.necessity_review(a.id, reviewer="modeler_A", keep=True, reason="x")
            assert False, "作者回避被突破"
        except ValueError:
            pass
        ao.necessity_review(a.id, reviewer="officer_B", keep=True, reason="建模需要")
        # 空话挑战被拒
        try:
            ao.challenge(a.id, reviewer="da_C", counterfactual="", experiment_design="", verdict="attack")
            assert False, "空话挑战未被拦截"
        except ValueError:
            pass
        ao.challenge(a.id, reviewer="da_C",
                     counterfactual="若容量均衡驱动，迁移模式将与碳价主导不可区分",
                     experiment_design="去掉碳价项重跑调度，比对迁移率变化",
                     verdict="可测")
        # 关键假设未做敏感度不可冻结
        try:
            ao.freeze(a.id, reviewer="officer_B")
            assert False, "关键假设跳过敏感度被冻结"
        except ValueError:
            pass
        ao.sensitivity(a.id, {"performed": True, "robust": True}, reviewer="officer_B")
        ao.freeze(a.id, reviewer="officer_B")
        assert ao.stats()["critical_sensitivity_covered"] == "1/1"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_A17_implicit_check():
    """A17：隐式假设映射——选最小二乘未登记隐式假设 → 漏登记列表非空"""
    d = tempfile.mkdtemp()
    try:
        ao = AssumptionOfficer(os.path.join(d, "a.json"))
        ao.register("关系为线性", author="m1")  # 只登记一条
        hits = ao.implicit_check(["最小二乘"], author="m1")
        assert len(hits) >= 3, f"隐式假设漏登记检测不足: {hits}"
        # 全部登记后无漏
        for s in ("误差项服从正态分布", "误差项同方差", "自变量与误差不相关"):
            ao.register(s, author="m1")
        assert ao.implicit_check(["最小二乘"], author="m1") == []
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_A26_numeric_gate():
    """A26：四断言正确/错误用例判定正确"""
    gate = NumericGate("/tmp")
    # 采样代入：f(x)=(lhs,rhs) 恒等 → pass
    gate.check_sampling(lambda x: (x**2, x**2), domain=[0.1, 0.5, 1.0], n=5)
    # 量纲：正确用例（分子分母可约分语义）——用自洽单位对
    gate.check_dimension({"速度": (["m"], ["s"]), "加速度": (["m"], ["s", "s"])})
    # 边界：3 组边界条件
    gate.check_boundary(lambda x: None, [("min", 0, 0), ("max", 1, 1), ("degenerate", 0, 0)])
    # 符号比对：x^2+2x+1 在 x=3 → 16
    gate.check_symbolic("x**2 + 2*x + 1", lambda x: x**2 + 2*x + 1, 3.0)
    gate.run_as_build_hook()
    rep = gate.report()
    assert rep["passed"], f"正确用例被误判: {rep['failed']}"
    # 错误用例：采样断言必须 fail
    gate2 = NumericGate("/tmp")
    gate2.check_sampling(lambda x: (x**2, x**2 + 1.0), domain=[0.1], n=3)
    assert not gate2.report()["passed"], "错误用例未被抓出"


def test_A22_orphan_figure():
    """A22：注入 1 张无引用图 → 孤儿检测 100%"""
    fi = FigureInventory()
    fi.register(id="fig1", caption="结果图", section="§3",
                data_source_hash="h_data", script_hash="h_script",
                claim_refs=["c1"], info_gain="两模型对比")
    orphans = fi.check_orphan(used_in_text=set())  # 正文没引用
    assert [f["id"] for f in orphans] == ["fig1"]
    # 有引用 → 无孤儿
    assert fi.check_orphan(used_in_text={"fig1"}) == []


def test_density():
    """密度检查：图数低于下限 → fail；section 失衡 → warn"""
    dc = DensityChecker()
    findings = dc.check(page_count=15, n_fig=3, n_tab=2, n_formula=22,
                        section_counts={"§3": 3}, qtype="优化类")
    verdicts = [f.verdict for f in findings]
    assert "fail" in verdicts, "图数 3 < 10 应 fail"


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
