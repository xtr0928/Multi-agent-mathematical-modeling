#!/usr/bin/env python3
# -*- coding: utf-8 -*-
src = open('/tmp/solve_mcm2026C_v5/paper/main.tex').read()

# ============ 1. 附录：算法 ============
marker = "\\end{document}"
addition1 = """\\section*{Appendix: Algorithm Sketches}

\\noindent\\textbf{Algorithm 1.} Maximum-entropy share recovery (Route A), per
elimination week $t$ with judge shares $J^\\%$ and eliminee index set $E$:
\\begin{enumerate}
\\item Build constraints: $\\Sigma s = 1$, $s \\ge 0$, and
$s_e - s_i \\le J^\\%_i - J^\\%_e - \\varepsilon$ for $e \\in E$, $i \\notin E$
(percent era).
\\item If no inequality survives (rank era or no elimination): return uniform
prior with the \\texttt{weak identification} label.
\\item Solve $\\min \\sum s_i \\log s_i$ with SLSQP from the uniform start.
\\item Back-test: predict eliminee as $\\arg\\min (J^\\% + s)$; record match.
\\end{enumerate}

\\noindent\\textbf{Algorithm 2.} Set identification (Route B), per elimination week:
\\begin{enumerate}
\\item For each contestant $i$: solve min/max $s_i$ over $\\mathcal{F}_t$ (HiGHS LP);
record $[\\underline{s}_i, \\overline{s}_i]$.
\\item Solve the Chebyshev-center LP: maximize $r$ s.t.\\ $A s + r \\|A_k\\| \\le b_k$.
\\item Report interval widths as the uncertainty output; never report a point
estimate without its interval.
\\end{enumerate}

\\noindent\\textbf{Algorithm 3.} Simulation-recovery validation (both routes):
\\begin{enumerate}
\\item Synthesize true shares (Dirichlet with structure) and judge scores correlated
with truth plus noise.
\\item Simulate eliminations under the percent rule.
\\item Estimate shares from eliminations alone with the route under test.
\\item Report L1 recovery vs.\\ a random-baseline distribution, and the replay rate
(expected 100\\% by construction).
\\end{enumerate}

\\end{document}"""
src = src.replace(marker, addition1, 1)

# ============ 2. 参考文献扩充 ============
marker2 = "\\item Dwork, C., et al. ``Fairness Through Awareness.'' \\emph{ITCS}, 2012.\n\\end{enumerate}"
addition2 = """\\item Dwork, C., et al. ``Fairness Through Awareness.'' \\emph{ITCS}, 2012.
\\item Nocedal, J., and Wright, S. J. \\emph{Numerical Optimization}. Springer, 2nd ed., 2006.
\\item Gelman, A., Carlin, J. B., Stern, H. S., and Rubin, D. B. \\emph{Bayesian Data Analysis}. Chapman \\& Hall/CRC, 3rd ed., 2013.
\\item Matou\\v{s}ek, J., and G\\\"artner, B. \\emph{Understanding and Using Linear Programming}. Springer, 2007.
\\end{enumerate}"""
src = src.replace(marker2, addition2, 1)

# ============ 3. 摘要数字核对（train share 不存在，跳过）============
open('/tmp/solve_mcm2026C_v5/paper/main.tex', 'w').write(src)
print('appendix + refs added')
