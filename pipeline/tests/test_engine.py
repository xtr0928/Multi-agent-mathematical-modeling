# -*- coding: utf-8 -*-
"""核心引擎验收测试：对应开发文档 A1/A2/A4/A5/A14/A16 判据"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.dag import DependencyGraph, CycleError
from engine.invalidation import InvalidationEngine
from engine.registry import ClaimRegistry, WriteGuardError, atomic_write
from engine.hashing import params_hash


def _mkfile(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    atomic_write(path, text.encode("utf-8"))
    return path


def test_A1_transitive_closure():
    """A1：作废传播 = 传递闭包，无遗漏"""
    g = DependencyGraph()
    for nid, ntype in [("p1", "param"), ("s1", "script"), ("r1", "result"),
                       ("c1", "claim"), ("para1", "paragraph"), ("s2", "script"),
                       ("r2", "result"), ("c2", "claim")]:
        g.add_node(nid, ntype, "h0")
    g.add_edge("p1", "s1"); g.add_edge("s1", "r1"); g.add_edge("r1", "c1")
    g.add_edge("c1", "para1"); g.add_edge("s1", "r2"); g.add_edge("r2", "c2")
    # s1 修改 → 传递闭包应含 r1,r2,c1,c2,para1（不只是直接下游）
    ds = g.transitive_downstream("s1")
    assert {"r1", "r2", "c1", "c2", "para1"} <= ds, f"闭包不完整: {ds}"
    # para1 修改 → 下游为空（无出边）
    assert g.transitive_downstream("para1") == set()


def test_A2_cycle_detection():
    """A2：A→B→A 写回用例 100% 拦截"""
    g = DependencyGraph()
    g.add_node("a", "script", "h"); g.add_node("b", "script", "h")
    g.add_edge("a", "b"); g.add_edge("b", "a")
    try:
        g.assert_acyclic()
        assert False, "环未被拦截"
    except CycleError:
        pass
    # 正常图不误报
    g2 = DependencyGraph()
    g2.add_node("x", "param", "h"); g2.add_node("y", "script", "h")
    g2.add_edge("x", "y")
    g2.assert_acyclic()


def test_A5_params_semantic_hash():
    """A5：参数语义化哈希——改注释/键序 → 哈希不变；作用域隔离"""
    p1 = {"model": {"alpha": 0.5, "beta": 2}, "_comment": "说明"}
    p2 = {"_comment": "改了注释", "model": {"beta": 2, "alpha": 0.5}}  # 键序不同
    assert params_hash(p1) == params_hash(p2), "注释/键序变化不应改变哈希"
    p3 = {"model": {"alpha": 0.5, "beta": 2}, "plot": {"figsize": 10}}
    h1 = params_hash(p3)
    p4 = {"model": {"alpha": 0.5, "beta": 2}, "plot": {"figsize": 12}}
    h2 = params_hash(p4)
    assert h1["model"] == h2["model"], "plot 作用域变化不应影响 model 哈希"
    assert h1["plot"] != h2["plot"], "plot 作用域变化必须反映在 plot 哈希"


def test_A4_write_guard():
    """A4：旧进程注入拦截——输入被新版本替换后，旧进程按旧哈希回写被拒绝"""
    d = tempfile.mkdtemp()
    try:
        data = _mkfile(os.path.join(d, "data.csv"), "1,2,3")
        script = _mkfile(os.path.join(d, "s.py"), "print(1)")
        reg = ClaimRegistry(os.path.join(d, "reg.db"), d)
        reg.register_input(data)          # live = h1
        reg.register_script(script)
        reg.register_params({"model": "h_model"})
        cid = reg.add_claim("x", 1.0, script, data, "model")
        assert reg.get_claim(cid)["status"] == "fresh"
        h1 = reg.live_input_hashes[data]
        # 数据被新版本替换
        _mkfile(data, "9,9,9")
        reg.register_input(data)          # live = h2
        assert reg.live_input_hashes[data] != h1
        # 旧进程用旧输入(h1)算完，声明旧哈希回写 → 必须被门卫拒绝
        try:
            reg.add_claim("x_stale", 2.0, script, data, "model", declared_input_hash=h1)
            assert False, "过期数据写入未被门卫拦截"
        except WriteGuardError:
            pass
        # 新进程按当前哈希回写 → 正常
        cid2 = reg.add_claim("x_fresh", 3.0, script, data, "model")
        assert reg.get_claim(cid2)["status"] == "fresh"
        reg.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_A16_atomic_write():
    """A16：原子发布——写入中途 kill 不产生可认作完成的产物"""
    d = tempfile.mkdtemp()
    try:
        path = os.path.join(d, "out.json")
        atomic_write(path, b'{"v": 1}')
        assert open(path, "rb").read() == b'{"v": 1}'
        leftovers = [f for f in os.listdir(d) if f.endswith(".part")]
        assert leftovers == [], f"残留临时文件: {leftovers}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_scan_and_reschedule():
    """扫描→作废→拓扑序重算 端到端（A1+A14 幂等性的基础）"""
    d = tempfile.mkdtemp()
    try:
        s1 = _mkfile(os.path.join(d, "s1.py"), "print(1)")
        s2 = _mkfile(os.path.join(d, "s2.py"), "print(2)")
        g = DependencyGraph()
        for nid, ntype in [("s1", "script"), ("s2", "script"), ("r1", "result"), ("r2", "result")]:
            g.add_node(nid, ntype, "h0")
        g.add_edge("s1", "r1"); g.add_edge("r1", "s2"); g.add_edge("s2", "r2")
        eng = InvalidationEngine(g)
        eng.watch_script("s1", s1); eng.watch_script("s2", s2)
        assert eng.scan() == set(), "初始扫描不应有脏节点"
        _mkfile(s1, "print(1)  # 修改了")  # 上游改
        dirty = eng.scan()
        assert dirty == {"s1", "r1", "s2", "r2"}, f"传递闭包作废失败: {dirty}"
        order = eng.reschedule()
        assert order == ["s1", "r1", "s2", "r2"], f"拓扑序错误: {order}"
        # 幂等：无新变化 → 再扫无脏
        assert eng.scan() == set()
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
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
