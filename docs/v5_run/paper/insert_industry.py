#!/usr/bin/env python3
# -*- coding: utf-8 -*-
src = open('/tmp/solve_mcm2026C_v5/paper/main.tex').read()

# 找 Q3 表格（含 Industry dummies 的行）
marker = "Industry dummies: (dominant categories vary by season)"
idx = src.find(marker)
print('marker idx:', idx)
if idx >= 0 and 'tab:industry' not in src:
    # 找到该表格的 \end{table}
    end = src.find('\\end{table}', idx) + len('\\end{table}')
    addition = """

\\begin{table}[h]
\\centering
\\begin{tabular}{lcc}
\\toprule
Industry (top categories) & Judge coef. & Fan coef. \\\\
\\midrule
Social Media Personality & $+0.478$ & $-0.003$ \\\\
Racing Driver & $+0.439$ & $-0.002$ \\\\
Actor/Actress & $+0.400$ & $-0.007$ \\\\
Singer/Rapper & $+0.383$ & $-0.006$ \\\\
Athlete & $+0.140$ & $-0.003$ \\\\
Model & $+0.101$ & $-0.009$ \\\\
Comedian & $-0.092$ & $\\approx 0$ \\\\
\\bottomrule
\\end{tabular}
\\caption{Industry effects: judges differentiate strongly by industry; fans do not
(all fan coefficients are within $\\pm0.01$ of zero).}
\\label{tab:industry}
\\end{table}

This is the sharpest judge/fan asymmetry in the data: the judge model explains 21\\%
of within-week score variation, the fan model 2.1\\%, and the industry coefficients
are an order of magnitude apart. Judges score what they can see (training, polish,
industry habits); fans vote on what the data does not contain---which is consistent
with the recovery experiment's message that fan support is driven by unobservables."""
    src = src[:end] + addition + src[end:]
    print('industry table inserted')
else:
    print('already present or marker not found')

open('/tmp/solve_mcm2026C_v5/paper/main.tex', 'w').write(src)
