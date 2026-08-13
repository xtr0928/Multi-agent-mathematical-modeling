#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_new_system.py — propose & simulate "Balanced Weighted z-score Fusion + Judge Save" (BWF-JS).
Compares with historical percent / rank rules on every season using inverse fan shares.
Metrics: replay consistency, finals agreement, judge-vs-fan power balance,
         controversy-case outcomes, sensitivity to weight w.
"""
import json
import numpy as np
from scipy.stats import spearmanr

FAN = "/home/zhenjinchao/projects/mcm-2026/analysis/fan_est.json"
PANEL = "/home/zhenjinchao/projects/mcm-2026/analysis/panel.json"
est = json.load(open(FAN))
panel = json.load(open(PANEL))

def rule_for(season):
    return "rank" if (season in (1, 2) or season >= 28) else "percent"

def robust_z(v):
    med = np.median(v); mad = np.median(np.abs(v - med)) + 1e-9
    return (v - med) / (1.4826 * mad)

def system_scores(P, system, w=0.5):
    """Returns 'better = larger' score vector for each couple."""
    n = len(P["names"]); p = np.array(P["p"]); q = np.array(P["qhat"])
    rj = np.array(P["rj"], float)
    if system == "percent":
        return p + q
    if system == "rank":
        return -(rj + np.array([n*(1-qi)+1 for qi in q]))   # negate: larger = better
    if system == "judge_only":
        return p
    if system == "fan_only":
        return q
    if system == "BWF":
        zj = robust_z(p); zf = robust_z(q)
        return w * zj + (1 - w) * zf
    raise ValueError(system)

def replay(P, system, w=0.5):
    s = system_scores(P, system, w)
    order_best = np.argsort(-s)
    names = P["names"]
    if P["is_final"]:
        return [names[i] for i in order_best]
    n_elim = len(P["elims"])
    return set(names[i] for i in order_best[-n_elim:]) if n_elim else set()

# ---------- 1. global comparison table ----------
systems = ["percent", "rank", "BWF-0.3", "BWF-0.5", "BWF-0.7", "judge_only", "fan_only"]
print("=== elimination-week replay accuracy by system (all 34 seasons, via qhat) ===")
print(f"{'system':12s} {'exact':>6s} {'b2':>6s} {'n':>4s}")
res = {}
for sys in systems:
    w = 0.5
    if sys.startswith("BWF"):
        w = float(sys.split("-")[1])
        sname = "BWF"
    else:
        sname = sys
    ex = bt = tot = 0
    for P in est:
        if P["is_final"] or not P["elims"]:
            continue
        tot += 1
        pred = replay(P, sname, w)
        if pred == set(P["elims"]):
            ex += 1
        s = system_scores(P, sname, w)
        b2 = set(P["names"][i] for i in np.argsort(-s)[-2:])
        if set(P["elims"]).issubset(b2):
            bt += 1
    res[sys] = (ex, bt, tot)
    print(f"{sys:12s} {ex:6d} {bt:6d} {tot:4d}  ({ex/tot:.1%} exact, {bt/tot:.1%} b2)")

# ---------- 2. finals agreement ----------
print("\n=== finals: predicted winner vs actual ===")
fin_agree = {}
for sys in systems:
    w = float(sys.split("-")[1]) if sys.startswith("BWF") else 0.5
    sname = "BWF" if sys.startswith("BWF") else sys
    ok = tot = 0
    for P in est:
        if not P["is_final"]:
            continue
        tot += 1
        order = replay(P, sname, w)
        actual_winner = None
        for c in panel[f"s{P['season']}"]["contestants"]:
            if c["name"] in P["names"] and c["placement"] == 1:
                actual_winner = c["name"]
        if order[0] == actual_winner:
            ok += 1
    fin_agree[sys] = (ok, tot)
    print(f"  {sys:12s}: winner match {ok}/{tot}")

# ---------- 3. controversy cases under each system ----------
print("\n=== controversy cases: final standing under each system ===")
cases = [(2, "Jerry Rice"), (4, "Billy Ray Cyrus"), (11, "Bristol Palin"), (27, "Bobby Bones")]
case_tab = {}
for season, name in cases:
    Pw = [P for P in est if P["season"] == season]
    final = [P for P in Pw if P["is_final"]]
    if not final:
        print(f"S{season} {name}: no finals week modeled"); continue
    P = final[0]
    actual = None
    for c in panel[f"s{season}"]["contestants"]:
        if c["name"] == name:
            actual = c["placement"]
    row = {"actual_placement": actual}
    for sys in systems:
        w = float(sys.split("-")[1]) if sys.startswith("BWF") else 0.5
        sname = "BWF" if sys.startswith("BWF") else sys
        order = replay(P, sname, w)
        pos = order.index(name) + 1 if name in order else None
        row[sys] = pos
        print(f"  S{season} {name:16s} {sys:12s}: pos={pos} (actual {actual})")
    case_tab[f"s{season}_{name}"] = row

# ---------- 4. fairness / power-balance metrics ----------
print("\n=== fairness & excitement metrics (finals weeks) ===")
metric = {}
for sys in systems:
    w = float(sys.split("-")[1]) if sys.startswith("BWF") else 0.5
    sname = "BWF" if sys.startswith("BWF") else sys
    rho_judge = []; rho_fan = []
    for P in est:
        if not P["is_final"]:
            continue
        order = replay(P, sname, w)
        names = P["names"]
        pos = {nm: i + 1 for i, nm in enumerate(order)}
        actual = {}
        for c in panel[f"s{P['season']}"]["contestants"]:
            if c["name"] in names:
                actual[c["name"]] = c["placement"]
        pairs = [(pos[nm], actual[nm]) for nm in names if nm in actual]
        if len(pairs) >= 2:
            rho_judge.append(spearmanr([p[0] for p in pairs], [p[1] for p in pairs]).statistic)
        # judge agreement: predicted order vs judge score order
        s = system_scores(P, sname, w)
        jorder = np.argsort(-np.array(P["p"]))
        rho_fan.append(spearmanr(np.argsort(-s), jorder).statistic)
    mj = np.mean(rho_judge) if rho_judge else np.nan
    mf = np.mean(rho_fan) if rho_fan else np.nan
    metric[sys] = (mj, mf)
    print(f"  {sys:12s}: pred-vs-actual ρ={mj:+.3f} | pred-vs-judge ρ={mf:+.3f}")

# ---------- 5. excitement: judge-fan conflict weeks ----------
print("\n=== excitement proxy: weeks where judge-worst couple survives (fan save) ===")
for sys in ["percent", "rank", "BWF-0.5"]:
    w = float(sys.split("-")[1]) if sys.startswith("BWF") else 0.5
    sname = "BWF" if sys.startswith("BWF") else sys
    saves = 0; tot = 0
    for P in est:
        if P["is_final"] or not P["elims"]:
            continue
        tot += 1
        jw = int(np.argmin(P["p"]))
        pred = replay(P, sname, w)
        if P["names"][jw] not in pred:
            saves += 1
    print(f"  {sys:12s}: judge-worst saved {saves}/{tot} ({saves/tot:.1%})")

# ---------- 6. sensitivity of BWF to w ----------
print("\n=== BWF weight sensitivity (elimination replay across all weeks) ===")
for w in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
    ex = bt = tot = 0
    for P in est:
        if P["is_final"] or not P["elims"]:
            continue
        tot += 1
        pred = replay(P, "BWF", w)
        ex += pred == set(P["elims"])
        s = system_scores(P, "BWF", w)
        b2 = set(P["names"][i] for i in np.argsort(-s)[-2:])
        bt += set(P["elims"]).issubset(b2)
    print(f"  w={w:.1f}: exact {ex}/{tot} ({ex/tot:.1%}) | b2 {bt}/{tot} ({bt/tot:.1%})")

json.dump({"systems": {k: {"exact": v[0], "b2": v[1], "tot": v[2]} for k, v in res.items()},
           "finals": fin_agree, "cases": case_tab, "metrics": metric,
           "sensitivity": {str(w): None for w in [0.2,0.3,0.4,0.5,0.6,0.7,0.8]}},
          open("/home/zhenjinchao/projects/mcm-2026/analysis/system_out.json", "w"), indent=1)
print("\nsaved system_out.json")
