#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
08_joint_intervals.py — season-level joint LP: fan shares across weeks with
continuity constraints |q_iw - q_i,w-1| <= delta, then per-(couple,week) projections.
Compares interval width with/without continuity. (Experiment first on S11 & S27.)
"""
import json
import numpy as np
from scipy.optimize import linprog

EST = "/home/zhenjinchao/projects/mcm-2026/analysis/fan_est.json"
est = json.load(open(EST))

def build_joint(season, delta):
    Pw = sorted([P for P in est if P["season"] == season], key=lambda x: x["week"])
    # variables: per week q (and z for weak weeks S28+)
    offsets = {}; total = 0
    for P in Pw:
        offsets[id(P)] = total
        total += len(P["names"])
    A = []; b = []
    # week constraints
    for P in Pw:
        o = offsets[id(P)]
        # elimination constraints (strong form only; seasons >=28 skip weak weeks)
        if P["rule"] == "percent":
            for e in P["elims"]:
                ei = P["names"].index(e)
                for i, nm in enumerate(P["names"]):
                    if nm == e: continue
                    row = np.zeros(total); row[o+ei] = 1; row[o+i] = -1
                    A.append(row); b.append(P["p"][i] - P["p"][ei] - 1e-9)
        else:
            if P["season"] < 28:
                for e in P["elims"]:
                    ei = P["names"].index(e)
                    for i, nm in enumerate(P["names"]):
                        if nm == e: continue
                        row = np.zeros(total); row[o+ei] = 1; row[o+i] = -1
                        A.append(row); b.append((P["rj"][ei] - P["rj"][i]) / len(P["names"]) - 1e-9)
            else:
                # weak: skip elimination constraints but keep finals
                pass
        if P["is_final"]:
            pls = []
            for i, nm in enumerate(P["names"]):
                pl = None
                for c in panel_caches.get(P["season"], []):
                    if c["name"] == nm and c["placement"]:
                        pl = c["placement"]
                if pl: pls.append((i, pl))
            pls.sort(key=lambda t: t[1])
            for (i, _), (k, _) in zip(pls[:-1], pls[1:]):
                row = np.zeros(total)
                if P["rule"] == "percent":
                    row[o+k] = 1; row[o+i] = -1; A.append(row); b.append(P["p"][i] - P["p"][k] - 1e-9)
                else:
                    row[o+k] = 1; row[o+i] = -1; A.append(row); b.append((P["rj"][k] - P["rj"][i]) / len(P["names"]) - 1e-9)
    # continuity: |q_iw - q_i,w-1| <= delta
    if delta is not None:
        for a, b2 in zip(Pw[:-1], Pw[1:]):
            common = [nm for nm in a["names"] if nm in b2["names"]]
            for nm in common:
                ia = a["names"].index(nm); ib = b2["names"].index(nm)
                oa = offsets[id(a)]; ob = offsets[id(b2)]
                r1 = np.zeros(total); r1[oa+ia] = 1; r1[ob+ib] = -1; A.append(r1); b.append(delta)
                r2 = np.zeros(total); r2[oa+ia] = -1; r2[ob+ib] = 1; A.append(r2); b.append(delta)
    # sum-to-1 per week
    A_eq = []
    for P in Pw:
        o = offsets[id(P)]
        row = np.zeros(total); row[o:o+len(P["names"])] = 1.0
        A_eq.append(row)
    return Pw, offsets, total, np.array(A), np.array(b), np.array(A_eq)

panel_caches = {}
for key, S in json.load(open("/home/zhenjinchao/projects/mcm-2026/analysis/panel.json")).items():
    panel_caches[int(key[1:])] = S["contestants"]

for season in (11, 27):
    print(f"\n===== season {season} =====")
    for delta in (None, 0.2, 0.1):
        Pw, offsets, total, A, b, Aeq = build_joint(season, delta if delta else None)
        widths = []
        Au = A if A.size else None
        bu = b if b.size else None
        for P in Pw:
            o = offsets[id(P)]
            for i in range(len(P["names"])):
                c = np.zeros(total); c[o+i] = 1
                r1 = linprog(c, A_ub=Au, b_ub=bu,
                             A_eq=Aeq, b_eq=np.ones(len(Aeq)), bounds=[(0,1)]*total, method="highs")
                r2 = linprog(-c, A_ub=Au, b_ub=bu,
                             A_eq=Aeq, b_eq=np.ones(len(Aeq)), bounds=[(0,1)]*total, method="highs")
                if r1.success and r2.success:
                    widths.append((-r2.fun) - r1.fun)
        widths = np.array(widths)
        print(f"  delta={delta}: mean width={widths.mean():.4f} median={np.median(widths):.4f} "
              f"p90={np.percentile(widths,90):.4f} n={len(widths)}")
