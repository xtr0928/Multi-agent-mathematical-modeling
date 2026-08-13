#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
src = open('/tmp/solve_mcm2026C_v5/paper/main.tex').read()

# fig1 插入 replay 表后
src = src.replace(r'\label{tab:replay}\end{table}',
r'''\label{tab:replay}\end{table}
\begin{figure}[h]
\centering
\includegraphics[width=0.85\textwidth]{figures/fig1_replay.png}
\caption{Elimination replay by era: both routes agree where data is strong; Route B declares weak identification elsewhere.}
\label{fig:replay}
\end{figure}''')

# fig2 插入 certainty 节
src = src.replace("""flag the gap explicitly: the true uncertainty is bracketed by the two, and any
single-number confidence claim would overstate precision.""",
"""flag the gap explicitly: the true uncertainty is bracketed by the two, and any
single-number confidence claim would overstate precision.

\\begin{figure}[h]
\\centering
\\includegraphics[width=0.9\\textwidth]{figures/fig2_width.png}
\\caption{Uncertainty width distributions: Route A's uncalibrated Laplace approximation (left) vs.\\ Route B's identification intervals (right).}
\\label{fig:width}
\\end{figure}""")

# fig3 插入争议案例
src = src.replace("""and our Route A replay confirms it changes outcomes in the save weeks.""",
"""and our Route A replay confirms it changes outcomes in the save weeks.

\\begin{figure}[h]
\\centering
\\includegraphics[width=0.8\\textwidth]{figures/fig3_cases.png}
\\caption{The four controversy cases: early-week judge rank vs.\\ fan rank. Fan support offsets judge scores---the structural source of controversy.}
\\label{fig:cases}
\\end{figure}""")

# fig4 插入 RDF 表后
src = src.replace(r'\label{tab:rdf}\end{table}',
r'''\label{tab:rdf}\end{table}
\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{figures/fig4_rdf.png}
\caption{RDF replay rate over the fusion weight $\alpha$: a stable plateau over $\alpha\in[0.2,0.8]$.}
\label{fig:rdf}
\end{figure}''')

open('/tmp/solve_mcm2026C_v5/paper/main.tex', 'w').write(src)
print('figures inserted:', src.count('\\includegraphics'))
