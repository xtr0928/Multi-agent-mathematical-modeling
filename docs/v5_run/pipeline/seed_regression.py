#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""种子库回归测试：注入已知矛盾 → 测 claims_registry 召回率
种子 = 华数杯实战矛盾 + 26C 病例（注入版）
"""
import sys
sys.path.insert(0, '/tmp/solve_mcm2026C_v5/pipeline')
from claims_registry import Registry

SEEDS = [
    # (名称, 注入函数, 预期规则)。注意：注入函数必须实际注册全部声明（用元组/列表，不能用 or 短路）
    ('R1-264vs259同scope', lambda r: [r.add(section='2.3', predicate='elimination_weeks', value=264,
        scope={'population': 'all'}), r.add(section='3.5', predicate='elimination_weeks', value=259,
        scope={'population': 'all'})], 'R1_HARD_CONFLICT'),
    ('R2-264vs259异scope', lambda r: [r.add(section='2.3', predicate='elimination_weeks', value=264,
        scope={'population': '含退赛周'}), r.add(section='3.5', predicate='elimination_weeks', value=259,
        scope={'population': '不含退赛周'})], 'R2_SCOPE_NOTE_REQUIRED'),
    ('R3-华数杯训练占比', lambda r: [r.add(section='4.2', predicate='train_share', value=0.819,
        value_display='81.9% (461.3/575.7)', scope={'unit': '万GPU-h'})], 'R3_DERIVED_MISMATCH'),
    ('R3-华数杯时延旧值', lambda r: [r.add(section='5.4', predicate='avg_delay', value=5.74,
        value_display='5.74h (2055.2/349.6)', scope={})], 'R3_DERIVED_MISMATCH'),
    ('R1-28vs30同scope', lambda r: [r.add(section='3.6', predicate='final_match', value=28,
        scope={'rule': 'percent'}), r.add(section='5.1', predicate='final_match', value=30,
        scope={'rule': 'percent'})], 'R1_HARD_CONFLICT'),
]

def run_seed_test():
    caught = 0
    results = []
    for name, inject, expected_rule in SEEDS:
        r = Registry()
        inject(r)
        issues, n = r.check()
        rules = {it['rule'] for it in issues}
        hit = expected_rule in rules
        caught += int(hit)
        results.append((name, expected_rule, list(rules), hit))
    recall = caught / len(SEEDS)
    print(f'种子库回归：{caught}/{len(SEEDS)} 召回率 {recall:.0%}')
    for name, exp, got, hit in results:
        print(f"  {'✓' if hit else '✗'} {name}: 预期 {exp} 实际 {got}")
    return recall

if __name__ == '__main__':
    run_seed_test()
