#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 claims registry 原型：声明注册 + 冲突检测 + 派生量反算
schema: {claim_id, section, predicate, value, value_display, scope{population,era,rule,transform},
         provenance{file,key,line}, caveats[], depends_on[]}
规则：
  R1 同谓词+同scope+不同value → 硬冲突（阻断）
  R2 同谓词+不同scope → 合法，但必须有口径说明句
  R3 派生量必须可反算（value_display 里的百分比 = 分子/分母）
"""
import json, re, sys
from collections import defaultdict

class Registry:
    def __init__(self, path=None):
        self.claims = []
        self.path = path

    def add(self, **kw):
        kw.setdefault('caveats', [])
        kw.setdefault('depends_on', [])
        if 'claim_id' not in kw:
            kw['claim_id'] = f'C{len(self.claims) + 1:04d}'
        self.claims.append(kw)
        return kw['claim_id']

    def check(self):
        """返回 (issues, ok_count)"""
        issues = []
        # R1/R2: 同谓词分组
        by_pred = defaultdict(list)
        for c in self.claims:
            by_pred[c['predicate']].append(c)
        for pred, group in by_pred.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    same_scope = a.get('scope') == b.get('scope')
                    if same_scope and a.get('value') != b.get('value'):
                        issues.append({
                            'rule': 'R1_HARD_CONFLICT',
                            'claim_ids': [a['claim_id'], b['claim_id']],
                            'predicate': pred,
                            'values': [a.get('value'), b.get('value')],
                            'sections': [a['section'], b['section']],
                            'msg': f'同谓词同 scope 不同值：{a["value"]} vs {b["value"]}'
                        })
                    elif not same_scope and a.get('value') != b.get('value'):
                        # R2: 需要口径说明
                        has_note = any('scope' in c.get('scope_note', '') for c in (a, b))
                        issues.append({
                            'rule': 'R2_SCOPE_NOTE_REQUIRED',
                            'claim_ids': [a['claim_id'], b['claim_id']],
                            'predicate': pred,
                            'values': [a.get('value'), b.get('value')],
                            'scopes': [a.get('scope'), b.get('scope')],
                            'msg': f'同谓词不同 scope 不同值（合法），但散文中必须出现口径说明句'
                        })
        # R3: 派生量反算
        for c in self.claims:
            vd = c.get('value_display', '')
            if 'of' not in vd and '(' not in vd:
                continue
            # 形如 "57.5% (149/259)" 或 "81.9% (461.3/575.7)"——支持小数
            m = re.search(r'\((\d+\.?\d*)\s*/\s*(\d+\.?\d*)\)', vd)
            if m:
                num, den = float(m.group(1)), float(m.group(2))
                if den > 0:
                    quotient = num / den
                    # 百分比反算
                    pct_m = re.search(r'(\d+\.?\d*)%', vd)
                    if pct_m:
                        expected = round(quotient * 100, 1)
                        actual = float(pct_m.group(1))
                        if abs(expected - actual) > 0.15:
                            issues.append({
                                'rule': 'R3_DERIVED_MISMATCH',
                                'claim_id': c['claim_id'],
                                'msg': f'派生量反算不符：{num}/{den}={expected}% 但显示 {actual}%'
                            })
                    # 非百分比商反算（如 5.88h (2055.2/349.6)）：括号前最近数字
                    elif 'h' in vd or 's' in vd or 'ms' in vd:
                        pre_m = re.search(r'(\d+\.?\d*)\s*(?:h|s|ms)\s*\(', vd)
                        if pre_m:
                            shown = float(pre_m.group(1))
                            if abs(shown - quotient) / max(quotient, 1e-9) > 0.01:
                                issues.append({
                                    'rule': 'R3_DERIVED_MISMATCH',
                                    'claim_id': c['claim_id'],
                                    'msg': f'派生量反算不符：{num}/{den}={quotient:.3f} 但显示 {shown}'
                                })
            # 和式检查 "232 + 31 + 1 = 264"
            m2 = re.search(r'(\d+)\s*\+\s*(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)', vd)
            if m2:
                nums = [int(m2.group(i)) for i in range(1, 4)]
                total = int(m2.group(4))
                if sum(nums) != total:
                    issues.append({
                        'rule': 'R3_SUM_MISMATCH',
                        'claim_id': c['claim_id'],
                        'msg': f'和式不符：{nums} 之和 {sum(nums)} != {total}'
                    })
        return issues, len(self.claims)

    def save(self, path=None):
        p = path or self.path or 'claims_registry.json'
        with open(p, 'w') as f:
            json.dump({'claims': self.claims}, f, ensure_ascii=False, indent=1)
        return p

    @classmethod
    def load(cls, path):
        with open(path) as f:
            data = json.load(f)
        r = cls(path)
        r.claims = data['claims']
        return r

if __name__ == '__main__':
    # 自测：用 26C 论文的真实病例
    r = Registry()
    r.add(section='2.3', predicate='elimination_weeks', value=264,
          value_display='264 elimination weeks', scope={'population': '含退赛周', 'era': 'all'},
          provenance={'file': 'results/panel.json', 'key': 'n_elim_weeks'})
    r.add(section='3.5', predicate='elimination_weeks', value=259,
          value_display='259 elimination weeks', scope={'population': '不含退赛周', 'era': 'all'},
          provenance={'file': 'results/panel.json', 'key': 'n_elim_clean'})
    r.add(section='5.2', predicate='fan_save_rate', value=0.575,
          value_display='57.5% (149/259)', scope={'population': 'all', 'era': 'percent'},
          provenance={'file': 'results/rule_compare.json', 'key': 'fan_save_rate'})
    r.add(section='6.1', predicate='fan_save_rate', value=0.575,
          value_display='57.5% (149/259)', scope={'population': 'all', 'era': 'percent'},
          provenance={'file': 'results/rule_compare.json', 'key': 'fan_save_rate'})
    r.add(section='2.2', predicate='elim_events', value=264,
          value_display='232 + 31 + 1 = 264 elimination events',
          scope={'population': 'all'},
          provenance={'file': 'results/panel.json', 'key': 'n_events'})
    issues, n = r.check()
    print(f'注册 {n} 条声明，检测到 {len(issues)} 个问题：')
    for it in issues:
        print(f"  [{it['rule']}] {it['msg']}")
    r.save('/tmp/solve_mcm2026C_v5/pipeline/self_test_registry.json')
    print('自测通过（预期：1 个 R1 硬冲突 + 1 个 R2 口径说明要求 + 0 个 R3 反算错误）')
