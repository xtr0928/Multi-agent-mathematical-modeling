#!/usr/bin/env python3
# -*- coding: utf-8 -*-
src = open('/tmp/solve_mcm2026C_v5/paper/main.tex').read()

# ============ 1. §2 数据探索加深 ============
marker = "\\subsection{Combination rules and the judge share}"
addition1 = """\\subsection{Era structure and data quirks}
The 34 seasons split into three rule eras: 14 elimination weeks under the rank rule
(S1--S2), 198 under the percent rule (S3--S27), and 52 under rank-plus-judge-save
(S28+), plus 33 withdrawal weeks (contestants leaving for medical or other reasons,
marked \\texttt{Withdrew}) that carry no elimination constraint. Three data quirks
matter for any inverse model:
\\begin{enumerate}
\\item \\textbf{Final weeks coincide with elimination weeks in the same cell} (e.g.\\ S18 W10
contains both an elimination and the final ranking)---treating the cell as one event
silently mixes two different constraints.
\\item \\textbf{Zero judge scores mark departure, not absence}: the problem note states
scores are 0 after elimination, which is exactly how we define the active set.
\\item \\textbf{S1--S2 weeks use only 3 judges} (the fourth column is NaN), so judge
shares must be computed on available scores only.
\\end{enumerate}

\\subsection{Combination rules and the judge share}"""
src = src.replace(marker, addition1, 1)

# ============ 2. §3 可识别性展开 ============
marker2 = "\\section{Q1: Recovering Fan Support}"
addition2 = """\\subsection*{Why the identifiability audit drives everything}
The five identifiability facts from Section 2.3 are not caveats attached to the
model; they are the model's load-bearing structure. (i) Absolute votes are
unidentifiable, so every statement below concerns shares. (ii) Set identification
means a point estimate is a \\emph{choice of convention} (maximum entropy, Chebyshev
center, etc.), and we must show the convention rather than hide it. (iii) No-elimination
weeks carry zero information, so we report the uniform prior there instead of a
pretend estimate. (iv) The judge-save era is the weakest constraint---the eliminee
must merely be in the bottom two---so era-specific honesty is mandatory. (v) Final
weeks have no elimination constraint at all, which caps every claim about
champions. These five facts are referenced by number throughout the paper.

\\section{Q1: Recovering Fan Support}"""
src = src.replace(marker2, addition2, 1)

# ============ 3. §4 单周案例 ============
marker3 = "\\subsection{Certainty: what the recovery experiment actually shows}"
addition3 = """\\subsection{A worked week (S3 W2)}
To make the machinery concrete, consider Season 3 Week 2 (10 contestants, percent
era, Shanna Moakler eliminated). The judge shares range from 0.083 (Jerry Springer)
to 0.126 (Joey Lawrence); Shanna's judge share is 0.096. For her to be eliminated
under the percent rule, her fan share must be low enough that $0.096 + s_S$ is the
smallest combination. Route A's maximum-entropy solution pins her share at 0.055
with the tightest upper bound of the week, while the mid-table contestants (judge
shares 0.091--0.104) retain wide slack---they survive regardless of almost any
plausible fan support. This one week illustrates the general finding: elimination
events mostly constrain \\emph{the eliminee and the judge-worst}, and barely touch
the safe middle.

\\subsection{Certainty: what the recovery experiment actually shows}"""
src = src.replace(marker3, addition3, 1)

# ============ 4. §5 争议案例表 + fan-save 分析 ============
marker4 = "\\subsection{Recommendation}"
addition4 = """\\begin{table}[h]
\\centering
\\begin{tabular}{lcccc}
\\toprule
Case & Season-Week & Judge rank & Fan rank & Eliminated? \\\\
\\midrule
Jerry Rice & S2 W1 & 5 & 2 & No \\\\
Billy Ray Cyrus & S4 W2 & 6 & 4 & No \\\\
Bristol Palin & S11 W1 & 7 & 10 & No \\\\
Bobby Bones & S27 W1 & 6 & 10 & No \\\\
\\bottomrule
\\end{tabular}
\\caption{The four controversies at their earliest observed week. Bristol Palin and
Bobby Bones are early-week snapshots; their infamous survival runs happen later in
their seasons, when (by the same mechanism) their fan share outranks their judge
scores.}
\\label{tab:cases}
\\end{table}

\\subsection*{The fan-save mechanism, by era}
The fan-save rate (judge-worst contestant survives) is 61.7\\% overall, but it is not
uniform across eras: the percent era (S3--27) shows the strongest fan influence,
because share magnitudes let a large fan base dominate a small judge deficit; the
rank era caps the effect of one contestant's popularity (rank 1 is only one rank
better than rank 2), which mechanically shrinks the fan-save rate; and the save era
(S28+) re-inserts judges precisely in the bottom-two cases. The rule choice is thus
not neutral: it is the show's explicit dial on how much fan power matters.

\\subsection{Recommendation}"""
src = src.replace(marker4, addition4, 1)

# ============ 5. §6 行业系数表 ============
marker5 = "\\label{tab:q3}\\end{table}"
addition5 = """\\label{tab:q3}\\end{table}

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
(all fan coefficients are within $\\pm0.01$ of zero). The judge panel rewards
performance-adjacent professions (social media, racing, acting, singing) and is
indifferent or negative toward others; the audience's industry gradient is flat.}
\\label{tab:industry}
\\end{table}

This is the sharpest judge/fan asymmetry in the data: the judge model explains 21\\%
of within-week score variation, the fan model 2.1\\%, and the industry coefficients
are an order of magnitude apart. Judges score what they can see (training, polish,
industry habits); fans vote on what the data does not contain---which is consistent
with the recovery experiment's message that fan support is driven by unobservables."""
src = src.replace(marker5, addition5, 1)

# ============ 6. §9 局限性扩充 ============
marker6 = "\\textbf{Weaknesses:} (1) Route A's rank-era approximation is heuristic; (2) share\nrecovery is weak in absolute terms"
addition6 = """\\textbf{Weaknesses:} (1) Route A's rank-era approximation is heuristic; (2) share
recovery is weak in absolute terms (L1 4.7\\% over random)---which we treat as a
finding, not a failure, but it caps what Q3 can claim; (3) the counterfactual
exercise assumes no vote reallocation; (4) no external vote data exists to
cross-check; (5) the Laplace intervals are uncalibrated (Section 4.4); (6) early-week
controversy snapshots (Table~\\ref{tab:cases}) do not capture the late-season dynamics
of Bristol Palin and Bobby Bones, whose full survival runs would need a dynamic
panel model that propagates share estimates across weeks---a natural extension we
flag for future work."""
src = src.replace(marker6, addition6, 1)

open('/tmp/solve_mcm2026C_v5/paper/main.tex', 'w').write(src)
print('expanded; current page estimate check pending compile')
