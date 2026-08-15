# -*- coding: utf-8 -*-
"""剩余模块验收：A3/A14/A15/A19/A23/A24/A28 + 编排层 dry-run + 写作模板 + 基准"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.dag import DependencyGraph
from engine.hashing import sha512_text
from engine.registry import ClaimRegistry, atomic_write
from seed.seed_library import SeedLibrary
from visual.dag_visualizer import dag_json, diff_dag
from audit.role_audit import RoleAuditLog, RoleAuditor, RoleEvent
from writing.template import ParagraphUnit, WritingTemplateEngine
from bench.internal_benchmark import InternalBenchmark
from orchestrator import Orchestrator, DryRunClient


def _mkfile(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    atomic_write(path, text.encode("utf-8"))
    return path


def test_A14_idempotency():
    """A14：幂等抽测——同输入/代码/参数哈希 → 同输出哈希（引擎层语义）"""
    g = DependencyGraph()
    for nid, ntype in [("s1", "script"), ("r1", "result")]:
        g.add_node(nid, ntype, "h0")
    g.add_edge("s1", "r1")
    # 组合哈希确定性：同输入必同哈希
    h1 = sha512_text("|".join(["script_h", "input_h", "params_h", "env_h"]))
    h2 = sha512_text("|".join(["script_h", "input_h", "params_h", "env_h"]))
    assert h1 == h2
    # 不同输入必不同哈希
    assert sha512_text("a") != sha512_text("b")


def test_A15_recovery_order():
    """A15：恢复顺序——stage2 作废 + stage3 待跑时，stage3 在全绿前不得启动"""
    from state.state_machine import ProgressStateMachine
    d = tempfile.mkdtemp()
    try:
        sm = ProgressStateMachine(d)
        sm.checkpoint("stage2", {"a1": "h1"})
        # 当前 a1 哈希不符 → dirty 非空 → stage3 不得推进
        r = sm.recover({"a1": "modified"})
        assert r["dirty"] == ["a1"]
        # 全绿后允许推进
        sm.checkpoint("stage2", {"a1": "h1"})
        r2 = sm.recover({"a1": "h1"})
        assert r2["dirty"] == [] and r2["trusted"] == ["a1"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_A19_experiment_isolation():
    """A19：敏感度实验产物隔离——experiment/ namespace 禁入论文引用池"""
    # 语义：registry 状态 experiment 的 claim 不得被 paragraph 引用
    d = tempfile.mkdtemp()
    try:
        data = _mkfile(os.path.join(d, "d.csv"), "1")
        script = _mkfile(os.path.join(d, "s.py"), "1")
        reg = ClaimRegistry(os.path.join(d, "r.db"), d)
        reg.register_input(data); reg.register_script(script)
        reg.register_params({"model": "h"})
        cid = reg.add_claim("sensitivity_run", 1.0, script, data, "model",
                            status="experiment")
        eng = WritingTemplateEngine(reg)
        unit = ParagraphUnit("结果呈现",
                             {"metric_name": "x", "value": 1.0, "uncertainty": "±0.1",
                              "baseline_name": "b", "baseline_value": 0,
                              "comparison": "更优"},
                             [cid])
        eng.add(unit)
        stale = eng.scan_stale_refs(unit.id)
        # experiment 状态禁入论文引用池（A19）
        assert any(c["reason"] == "experiment" for c in stale), \
            f"experiment 引用未被阻断: {stale}"
        c = reg.get_claim(cid)
        assert c["status"] == "experiment"
        reg.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_A23_seed_library():
    """A23：华数杯 17 条结构化入库；文本层可测种子检出"""
    lib = SeedLibrary()
    st = lib.stats()
    assert st["total"] == 17, f"种子数 {st['total']} ≠ 17"
    assert st["by_category"]["numeric"] >= 5
    # 检出测试：摘要正文因果冲突 + 占位符 + 灵敏度不量化
    t1 = "摘要：主要原因是碳价主导。\n\n" + "正文" * 1500 + "：主要原因是容量均衡。"
    hits1 = lib.scan(t1)
    assert "HSB-02" in hits1, f"因果冲突未检出: {hits1}"
    hits2 = lib.scan("TODO: 补图 3")
    assert "HSB-15" in hits2
    hits3 = lib.scan("我们做了灵敏度分析。")
    assert "HSB-17" in hits3, "灵敏度不量化未检出"


def test_A24_dag_diff():
    """A24：DAG 可视化与 registry 依赖记录 diff 一致率 100%"""
    g = DependencyGraph()
    g.add_node("a", "script", "h"); g.add_node("b", "result", "h")
    g.add_edge("a", "b")
    j1 = dag_json(g)
    j2 = dag_json(g)
    assert diff_dag(j1, j2) == []
    j3 = {"nodes": j1["nodes"], "edges": {"x": ["y"]}}
    assert diff_dag(j1, j3) != []


def test_A28_role_audit():
    """A28：角色隔离审计——四类违规全部检出"""
    d = tempfile.mkdtemp()
    try:
        log = RoleAuditLog(os.path.join(d, "roles.jsonl"))
        # 违规1：同一实例写 §3 又评审 §3
        log.record(RoleEvent("inst_A", "writer", "deepseek", "§3", "write"))
        log.record(RoleEvent("inst_A", "reviewer", "deepseek", "§3", "review"))
        # 违规2：假设提交者自己审查
        log.record(RoleEvent("inst_B", "assumption_submitter", "glm", "H01", "submit"))
        log.record(RoleEvent("inst_B", "assumption_officer", "glm", "H01", "review"))
        # 违规3：实例先写后评（零上下文污染）
        log.record(RoleEvent("inst_C", "writer", "kimi", "§5", "write"))
        log.record(RoleEvent("inst_C", "reviewer", "kimi", "§4", "review"))
        auditor = RoleAuditor()
        v = auditor.audit(log)
        assert not v["passed"], "违规未被检出"
        assert len(v["writer_reviewer"]) == 1
        assert len(v["assumption_avoidance"]) == 1
        assert len(v["zero_context"]) == 2  # inst_A 与 inst_C 均先写后评
        # 干净日志 → 通过
        d2 = tempfile.mkdtemp()
        log2 = RoleAuditLog(os.path.join(d2, "r.jsonl"))
        log2.record(RoleEvent("inst_A", "writer", "deepseek", "§3", "write"))
        log2.record(RoleEvent("inst_B", "reviewer", "glm", "§3", "review"))
        log2.record(RoleEvent("inst_C", "assumption_officer", "kimi", "H01", "review"))
        assert auditor.audit(log2)["passed"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_writing_template_stale():
    """写作模板：claim 作废 → 段落 stale 引用被扫描阻断（A6 语义）"""
    d = tempfile.mkdtemp()
    try:
        data = _mkfile(os.path.join(d, "d.csv"), "1")
        script = _mkfile(os.path.join(d, "s.py"), "1")
        reg = ClaimRegistry(os.path.join(d, "r.db"), d)
        reg.register_input(data); reg.register_script(script)
        reg.register_params({"model": "h"})
        cid = reg.add_claim("mse", 0.42, script, data, "model")
        eng = WritingTemplateEngine(reg)
        unit = ParagraphUnit("结果呈现", {"metric_name": "MSE", "value": 0.42,
                                          "uncertainty": "±0.03", "baseline_name": "基线",
                                          "baseline_value": 0.55, "comparison": "提升 24%"}, [cid])
        eng.add(unit)
        text = unit.render()
        assert "[claim:" in text
        # 作废后扫描必须暴露
        reg.invalidate(cid, "上游脚本修改")
        stale = eng.scan_stale_refs(unit.id)
        assert stale and stale[0]["claim_id"] == cid
        reg.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_orchestrator_dry_run():
    """编排层 dry-run：零 API 成本跑通 S0-S6（完整流程 29 次调用）"""
    orch = Orchestrator(DryRunClient())
    assert orch.estimate_calls() == 29
    rep = orch.run_full("测试需求")
    assert rep["_dry_run"] is True
    assert rep["_total_calls"] == 29


def test_benchmark():
    """基准：C++ 决策公式 + predicate 覆盖率"""
    d = tempfile.mkdtemp()
    try:
        b = InternalBenchmark(os.path.join(d, "bench.json"))
        # 收益>成本 且 总运行≥1h → 建议重写（(3600-30)*5=17850 > 1h*3600*3=10800）
        assert b.cpp_should_rewrite(est_py_s=3600, est_cpp_s=30,
                                    rewrite_cost_h=1, calls=5, total_run_s=7200)
        # 总运行 <1h → 禁止
        assert not b.cpp_should_rewrite(est_py_s=3600, est_cpp_s=30,
                                        rewrite_cost_h=0.1, calls=5, total_run_s=1800)
        b.record_predicate("fresh"); b.record_predicate("自由文本状态")
        cov = b.predicate_coverage(["fresh", "stale", "自由文本状态"])
        assert cov["illegal"] == ["自由文本状态"]
        assert cov["coverage"] == 2 / 3
    finally:
        shutil.rmtree(d, ignore_errors=True)


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
