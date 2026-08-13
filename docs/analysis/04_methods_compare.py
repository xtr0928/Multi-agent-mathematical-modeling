#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_methods_compare.py — replay both rules everywhere; quantify fan-vs-judge bias;
controversy cases; bottom-two judge-save evidence.  v2 (directions fixed)
"""
import json
import numpy as np

FAN = "/home/zhenjinchao/projects/mcm-2026/analysis/fan_est.json"
PANEL = "/home/zhenjinchao/projects/mcm-2026/analysis/panel.json"
OUT = "/home/zhenjinchao/projects/mcm-2026/analysis/methods_out.json"

est = json.load(open(FAN))
panel = json.load(open(PANEL))

def rule_for(season):
    return "rank" if (season in (1, 2) or season >= 28) else "percent"

def combined(P, rule, q):
    n = len(P["names"])
    if rule == "percent":
        return np.array(P["p"]) + np.array(q)
    return np.array(P["rj"], float) + np.array([n*(1-qi)+1 for qi in q])

def best_to_worst(P, rule, q):
    c = combined(P, rule, q)
    if rule == "percent":
        return np.argsort(-c)   # highest combined = best
    return np.argsort(c)        # lowest combined = best

def replay(P, rule):
    names = P["names"]
    order = best_to_worst(P, rule, P["qhat"])
    if P["is_final"]:
        return {"order": [names[i] for i in order]}
    n_elim = len(P["elims"])
    pred = [names[i] for i in order[-n_elim:]] if n_elim else []
    b2 = [names[i] for i in order[-2:]]
    return {"order": [names[i] for i in order], "pred": pred, "b2": b2}

# ---------- 1. consistency table ----------
print("=== replay consistency by era (own rule) ===")
for label, f in [("S1-2 rank", lambda s: s <= 2), ("S3-27 percent", lambda s: 3 <= s <= 27),
                 ("S28-34 rank+save", lambda s: s >= 28)]:
    sub = [P for P in est if not P["is_final"] and P["elims"] and f(P["season"])]
    ex = sum(1 for P in sub if set(replay(P, P["rule"])["pred"]) == set(P["elims"]))
    bt = sum(1 for P in sub if set(P["elims"]).issubset(replay(P, P["rule"])["b2"]))
    print(f"  {label}: exact {ex}/{len(sub)} ({ex/max(1,len(sub)):.1%}), bottom2 {bt}/{len(sub)} ({bt/max(1,len(sub)):.1%})")

# ---------- 2. counterfactual: every season under BOTH rules ----------
print("\n=== counterfactual replay: both rules on all seasons (own-rule eras only matter) ===")
agg = {}
for P in est:
    if P["is_final"] or not P["elims"]:
        continue
    for rule in ("rank", "percent"):
        r = replay(P, rule)
        key = (P["season"], rule)
        d = agg.setdefault(key, {"tot": 0, "exact": 0, "b2": 0, "fan_saves": 0, "fan_kills": 0})
        d["tot"] += 1
        d["exact"] += set(r["pred"]) == set(P["elims"])
        d["b2"] += set(P["elims"]).issubset(r["b2"])
        # fan_saves: actual judge-worst (min p) not eliminated; fan_kills: eliminated not judge-worst
        jw = int(np.argmin(P["p"]))
        if P["names"][jw] not in P["elims"]:
            d["fan_saves"] += 1
        for e in P["elims"]:
            if P["names"].index(e) != jw:
                d["fan_kills"] += 1
                break

eras = [("S1-2", lambda s: s <= 2), ("S3-27", lambda s: 3 <= s <= 27), ("S28-34", lambda s: s >= 28)]
for label, f in eras:
    print(f"--- {label} ---")
    for rule in ("rank", "percent"):
        d = agg.get((label, rule))
        tot = sum(v["tot"] for (s, r), v in agg.items() if f(s) and r == rule)
        ex  = sum(v["exact"] for (s, r), v in agg.items() if f(s) and r == rule)
        b2  = sum(v["b2"] for (s, r), v in agg.items() if f(s) and r == rule)
        fs  = sum(v["fan_saves"] for (s, r), v in agg.items() if f(s) and r == rule)
        fk  = sum(v["fan_kills"] for (s, r), v in agg.items() if f(s) and r == rule)
        print(f"  {rule:8s}: exact {ex}/{tot} ({ex/max(1,tot):.1%}) b2 {b2}/{tot} ({b2/max(1,tot):.1%}) "
              f"| fan_saves {fs} | fan_kills {fk}")

# ---------- 3. judge-vs-fan agreement: Spearman per week (fan share rank vs judge rank) ----------
from scipy.stats import spearmanr
rhos = []
for P in est:
    q = P["qhat"]; n = len(P["names"])
    fr = np.argsort(-np.array(q)) + 1  # 1 = most fan votes
    rho, _ = spearmanr(P["rj"], fr)
    rhos.append((P["season"], P["week"], rho, n))
by_era = {}
for s, w, rho, n in rhos:
    era = "S1-2" if s <= 2 else ("S3-27" if s <= 27 else "S28-34")
    by_era.setdefault(era, []).append(rho)
print("\n=== judge-fan share agreement (Spearman) ===")
for era, rs in sorted(by_era.items()):
    print(f"  {era}: mean rho={np.mean(rs):.3f} (n={len(rs)})")

# ---------- 4. controversy cases ----------
print("\n=== controversy case studies ===")
cases = [(2, "Jerry Rice"), (4, "Billy Ray Cyrus"), (11, "Bristol Palin"), (27, "Bobby Bones")]
case_out = {}
for season, name in cases:
    Pw = sorted([P for P in est if P["season"] == season and name in P["names"]], key=lambda x: x["week"])
    c = [c for c in panel[f"s{season}"]["contestants"] if c["name"] == name][0]
    rows = []
    for P in Pw:
        i = P["names"].index(name)
        q = P["qhat"]
        jr = P["rj"][i]
        fr = sum(1 for qq in q if qq > q[i] + 1e-12) + 1
        cr = {rule: (lambda c, rule=rule: sum(1 for cv in c if cv < c[i]) + 1)(combined(P, rule, q))
              for rule in ("rank", "percent")}
        rows.append({"week": P["week"], "judge_rank": jr, "fan_rank": fr,
                     "comb_rank_rankrule": cr["rank"], "comb_rank_pctrule": cr["percent"],
                     "eliminated": name in P["elims"]})
        print(f"  S{season} W{P['week']:2d} {name}: judge_rank={jr} fan_rank={fr} "
              f"comb(rank)={cr['rank']} comb(pct)={cr['percent']} elim={name in P['elims']}")
    case_out[f"s{season}_{name}"] = {"actual": c["results"], "placement": c["placement"], "weeks": rows}

# ---------- 5. judge-save evidence in S28+ ----------
print("\n=== S28+ judge-save evidence (predicted bottom2 survivors) ===")
save_evidence = []
for P in est:
    if P["season"] < 28 or P["is_final"] or not P["elims"]:
        continue
    r = replay(P, "rank")
    for nm in r["b2"]:
        if nm not in P["elims"]:
            save_evidence.append({"season": P["season"], "week": P["week"], "name": nm,
                                  "b2": r["b2"], "eliminated": P["elims"]})
from collections import Counter
cnt = Counter((e["season"], e["name"]) for e in save_evidence)
print("couples predicted in bottom-2 but surviving (multi-week consistency):")
for (s, nm), k in sorted(cnt.items(), key=lambda x: -x[1])[:15]:
    print(f"  S{s} {nm}: {k} weeks")

# ---------- 6. finals: both rules vs actual placement ----------
print("\n=== finals replay ===")
fin_out = []
for P in est:
    if not P["is_final"]:
        continue
    pl = {}
    for c in panel[f"s{P['season']}"]["contestants"]:
        if c["name"] in P["names"]:
            pl[c["name"]] = c["placement"]
    r = {}
    for rule in ("rank", "percent"):
        order = replay(P, rule)["order"]
        r[rule] = order
        print(f"  S{P['season']} {rule:7s}: {order}  (actual: {pl})")
    fin_out.append({"season": P["season"], "names": P["names"], "actual": pl,
                    "rank_rule": r["rank"], "pct_rule": r["percent"]})

json.dump({"cases": case_out, "save_evidence": save_evidence, "finals": fin_out,
           "judge_fan_rho_by_era": {k: {"mean": float(np.mean(v)), "n": len(v)} for k, v in by_era.items()}},
          open(OUT, "w"), ensure_ascii=False, indent=1)
print("\nsaved", OUT)
