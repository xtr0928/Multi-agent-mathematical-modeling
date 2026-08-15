# -*- coding: utf-8 -*-
"""模板门禁 + 篇幅门禁测试（用户指令 2026-08-15）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'layout'))
from layout_gate import LayoutFinding, TemplateGate, LengthGate


def test_template_gate():
    tg = TemplateGate()
    # 缺模板清单 → 阻断
    r = tg.check("华数杯X", {})
    assert r[0].verdict == "fail" and "先搜索官方模板" in r[0].detail
    # 华数杯全项符合
    full = {name: True for name, _, _ in TemplateGate.HUASHU_TEMPLATE}
    r = tg.check("华数杯", full)
    assert r[0].verdict == "pass"
    # 缺 AI 声明 → fail
    bad = dict(full)
    bad["ai_statement_before_refs"] = False
    r = tg.check("华数杯", bad)
    assert any(f.verdict == "fail" and "AI 声明" in f.detail for f in r)
    # 缺网络资源访问时间（非阻断）→ warn
    bad2 = dict(full)
    bad2["web_resources_access_time"] = False
    r = tg.check("华数杯", bad2)
    assert any(f.verdict == "warn" for f in r)
    assert not any(f.verdict == "fail" for f in r)


def test_length_gate():
    lg = LengthGate()
    # 10 页 vs 20 页上限（75% = 15 页）→ 阻断
    r = lg.check(10, 20)
    assert r[0].verdict == "fail" and "15" in r[0].detail
    # 15 页 → 通过
    r = lg.check(15, 20)
    assert r[0].verdict == "pass"
    # 21 页超上限 → 阻断
    r = lg.check(21, 20)
    assert r[0].verdict == "fail"
    # 75% 可配置
    r = lg.check(12, 20, percent=0.6)
    assert r[0].verdict == "pass"


if __name__ == "__main__":
    test_template_gate()
    test_length_gate()
    print("2/2 passed")
