#!/usr/bin/env python3
# -*- coding: utf-8 -*-
src = open('/tmp/solve_mcm2026C_v5/paper/main.tex').read()

# fig1：找 tab:replay 的 end{table}
marker1 = "\\label{tab:replay}"
idx1 = src.find(marker1)
if idx1 >= 0 and 'fig1_replay' not in src:
    end1 = src.find('\\end{table}', idx1) + len('\\end{table}')
    src = src[:end1] + '''

\\begin{figure}[h]
\\centering
\\includegraphics[width=0.85\\textwidth]{figures/fig1_replay.png}
\\caption{Elimination replay by era: both routes agree where data is strong; Route B declares weak identification elsewhere.}
\\label{fig:replay}
\\end{figure}''' + src[end1:]
    print('fig1 inserted')

# fig4：找 tab:rdf 的 end{table}
marker4 = "\\label{tab:rdf}"
idx4 = src.find(marker4)
if idx4 >= 0 and 'fig4_rdf' not in src:
    end4 = src.find('\\end{table}', idx4) + len('\\end{table}')
    src = src[:end4] + '''

\\begin{figure}[h]
\\centering
\\includegraphics[width=0.8\\textwidth]{figures/fig4_rdf.png}
\\caption{RDF replay rate over the fusion weight $\\alpha$: a stable plateau over $\\alpha\\in[0.2,0.8]$.}
\\label{fig:rdf}
\\end{figure}''' + src[end4:]
    print('fig4 inserted')

open('/tmp/solve_mcm2026C_v5/paper/main.tex', 'w').write(src)
print('total includegraphics:', src.count('\\includegraphics'))
