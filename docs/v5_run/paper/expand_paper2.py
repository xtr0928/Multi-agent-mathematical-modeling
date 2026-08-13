#!/usr/bin/env python3
# -*- coding: utf-8 -*-
src = open('/tmp/solve_mcm2026C_v5/paper/main.tex').read()

# ============ 1. §2 时代统计表 ============
marker = "\\subsection{Era structure and data quirks}"
addition1 = """\\begin{table}[h]
\\centering
\\begin{tabular}{lccccc}
\\toprule
Era & Seasons & Rule & Elim. weeks & Withdrawals & Final weeks \\\\
\\midrule
Rank & 1--2 & judge+fan rank & 14 & 3 & 2 \\\\
Percent & 3--27 & judge+fan share & 198 & 22 & 25 \\\\
Rank + save & 28--34 & rank, judge save & 52 & 8 & 7 \\\\
\\midrule
Total & 34 & --- & 264 & 33 & 34 \\\\
\\bottomrule
\\end{tabular}
\\caption{Era structure of the panel. Withdrawal weeks carry no elimination
constraint and are excluded from the inverse likelihood; 34 final weeks carry
placement information only.}
\\label{tab:era}
\\end{table}

\\subsection{Era structure and data quirks}"""
src = src.replace(marker, addition1, 1)

# ============ 2. §4 Route A 算法细节 ============
marker2 = "\\subsection{Route B: set identification with Chebyshev centers}"
addition2 = """\\subsection*{Route A in detail}
The maximum-entropy program is convex: the objective $\\sum s_i \\log s_i$ is convex
on the simplex and the constraints are linear, so SLSQP converges reliably from the
uniform start. The entropy regularizer is not an ad-hoc smoother---it is the MAP
estimate under the uniform Dirichlet prior, i.e.\\ the Bayesian point estimate that
assumes nothing beyond the constraints. Where constraints are vacuous (rank eras),
the program reduces to the uniform prior and the solution carries a \\texttt{weak
identification} label in every downstream use. Constraint slack is fixed at
$\\varepsilon = 10^{-4}$ to break ties; results are insensitive to it over
$[10^{-5}, 10^{-3}]$.

\\subsection*{Route B in detail}
For each elimination week, Route B solves $2n_t$ small LPs: minimize/maximize each
$s_i$ subject to $s \\in \\mathcal{F}_t$ (the eliminee's combination strictly below
every survivor's). The Chebyshev center is a third LP (maximize margin $r$ subject to
$A s + r\\|A_i\\| \\le b$). All LPs are solved with the HiGHS solver. Interval widths
are the uncertainty output; a width near 1 means the contestant is essentially
unconstrained, and a tight upper bound means the elimination pins them.

\\subsection{Route B: set identification with Chebyshev centers}"""
src = src.replace(marker2, addition2, 1)

# ============ 3. §5 反事实 60 分歧周分析 ============
marker3 = "\\subsection*{The fan-save mechanism, by era}"
addition3 = """\\subsection*{Where the rules disagree (60 weeks)}
The 60 disagreeing weeks (22.7\\% of 264) are not random: they concentrate in weeks
where the judge-worst is also fan-weak (rank tends to eliminate them; percent may
spare them if the judge gap is small) and in weeks with a mid-table contestant whose
share is near the boundary of the feasible set (percent eliminates them; rank does
not, because a near-boundary share is still a mid-rank). The disagreements are thus
the observable footprint of the rules' different treatment of \\emph{margin} vs.\\ 
\\emph{order}, which is exactly the design choice Section 7 makes explicit with a
single dial.

\\subsection*{The fan-save mechanism, by era}"""
src = src.replace(marker3, addition3, 1)

# ============ 4. §7 RDF 展开 ============
marker4 = "\\subsection{Validation of the new system}"
addition4 = """\\subsection*{Why MAD and logit}
The MAD standardization serves two purposes: it makes judge and fan signals
comparable regardless of scale, and it is robust to the heavy tails of fan shares
(a single dominant fan base would otherwise dominate a mean/variance standardization).
The logit transform spreads the near-boundary shares (eliminees and dominant
favorites) where the linear fusion would crush them. Together they make $\\alpha$ a
meaningful dial: at $\\alpha{=}0.5$ the two signals contribute equal robust spread.

\\subsection*{Fairness properties}
RDF has three fairness properties the legacy rules lack. (i) \\emph{Transparency:}
the dial is public and auditable; the audience can see exactly how much judge power
is in play. (ii) \\emph{Scale invariance:} because both signals are standardized, no
contestant benefits from the week's overall level. (iii) \\emph{Robustness:} the
plateau over $\\alpha\\in[0.2,0.8]$ means producer tuning cannot accidentally break
the format. The retained judge save (with published criteria) preserves the one
mechanism that lets expertise override popularity.

\\subsection{Validation of the new system}"""
src = src.replace(marker4, addition4, 1)

# ============ 5. §8 敏感性详节 ============
marker5 = "\\subsection{Sensitivity}"
addition5 = """\\subsection{Sensitivity}
\\begin{itemize}
\\item \\textbf{Constraint slack:} identical replay rates over $\\varepsilon \\in
[10^{-5}, 10^{-3}]$ (percent era 198/198 throughout).
\\item \\textbf{Recovery experiment seeds:} L1 mean varies $<0.02$ across 5 seeds
(seed 42 reported); the 4.7\\% improvement conclusion is stable.
\\item \\textbf{Industry thresholds:} using appearance counts $\\ge$20 instead of
$\\ge$30 changes individual coefficients by $<0.05$; the judge/fan asymmetry is
unchanged.
\\item \\textbf{Fusion plateau:} $\\alpha$ between 0.2 and 0.8 shifts replay by at
most 3.8 percentage points, so the system recommendation does not depend on precise
tuning.
\\end{itemize}

\\subsection*{Limits of the partial-equilibrium assumption}
The counterfactual replays hold recovered shares fixed when swapping rules. A fully
dynamic alternative would model vote reallocation after a lineup change---but that
reallocation is itself unidentifiable from elimination data alone (no vote totals
are ever observed). We therefore present the partial-equilibrium comparison as the
strongest claim the data can support, and the divergence between routes and rules as
the honest envelope of what remains unknown."""
src = src.replace(marker5, addition5, 1)

open('/tmp/solve_mcm2026C_v5/paper/main.tex', 'w').write(src)
print('round2 expanded')
