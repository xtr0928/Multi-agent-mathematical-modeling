#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03_inverse.py — inverse-optimization model for fan votes (share space). v3
For each (season, week):
  - active roster, judge totals -> judge percent p_i, judge rank rj_i
  - elimination set E (or final-week placement ordering)
  - linear constraints on fan share q_i (sum q = 1, q >= 0):
      percent rule (S3-27): p_e + q_e < p_i + q_i   (e eliminated = lowest combined)
      rank rule (S1-2, S28-34):  C = rj + n(1-q)+1 ; eliminated e has LARGEST C
         strong: q_e - q_i < (rj_e - rj_i)/n
         weak (S28+, bottom-two+judge-save): big-M exists i with C_i > C_e
      finals: placement ordering C_better < C_worse
  - feasible interval [qmin,qmax] per contestant via LP projections
  - point estimate: max-entropy + cross-week smoothing (global SLSQP per season)
Output: analysis/fan_est.json
"""
import json, math, re as _re
import numpy as np
from scipy.optimize import linprog, minimize

def re_place(s):
    return bool(_re.search(r"Place", s))

PANEL = "/home/zhenjinchao/projects/mcm-2026/analysis/panel.json"
OUT   = "/home/zhenjinchao/projects/mcm-2026/analysis/fan_est.json"
panel = json.load(open(PANEL))
EPS = 1e-9

def rule_for(season):
    return "rank" if (season in (1, 2) or season >= 28) else "percent"

def judge_rank_desc(scores):
    """rank 1 = highest score (best). ties by stable order."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    r = [0]*len(scores)
    for pos, i in enumerate(order):
        r[i] = pos + 1
    return r

def build_week(season, week, week_info, contestants, scores_by_name):
    names = week_info["active"]
    if not names:
        return None
    j = {nm: scores_by_name[nm][str(week)] for nm in names}
    scores = [j[nm] for nm in names]
    n = len(names)
    p = np.array(scores, dtype=float) / sum(scores)
    rj = judge_rank_desc(scores)
    finals = [c["name"] for c in contestants if not c["withdrew"] and c["placement"] is not None and re_place(c["results"])]
    is_final = len(week_info["active"]) == len(finals) and all(nm in finals for nm in week_info["active"])
    return {"season": season, "week": week, "names": names, "p": p, "rj": rj, "n": n,
            "elims": [e for e in week_info["eliminated"] if e in names],
            "rule": rule_for(season), "is_final": is_final}

def constraints_for(W):
    """Returns (A, b, weak, nv): A_ub x <= b_ub. Variables x = [q (n) | z (weak only)].
       weak (S28+): eliminated is one of the bottom two; judges choose."""
    n = W["n"]; p = W["p"]; rj = W["rj"]; rule = W["rule"]
    elim_idx = [W["names"].index(e) for e in W["elims"]]
    alive = [i for i in range(n) if i not in elim_idx]
    weak = rule == "rank" and W["season"] >= 28
    A = []; b = []
    if W["elims"] and alive and not weak:
        for e in elim_idx:
            for i in alive:
                if rule == "percent":
                    # p_e + q_e < p_i + q_i  ->  q_e - q_i < p_i - p_e
                    row = [0.0]*n; row[e] = 1.0; row[i] = -1.0
                    A.append(row); b.append(p[i] - p[e] - EPS)
                else:
                    # C_e > C_i  ->  q_e - q_i < (rj_e - rj_i)/n
                    row = [0.0]*n; row[e] = 1.0; row[i] = -1.0
                    A.append(row); b.append((rj[e] - rj[i]) / n - EPS)
        return np.array(A), np.array(b), weak, n
    if W["elims"] and alive and weak:
        # big-M: for each eliminated e, exists i in alive with C_i > C_e
        # C_i - C_e = n(q_e - q_i) + (rj_i - rj_e) ; require >= -M(1-z_i), sum z >= 1
        # => -n q_e + n q_i + M z_i <= (rj_i - rj_e) + M
        M = 2.0 * n
        nv = n + len(elim_idx) * len(alive)
        for e in elim_idx:
            for zi, i in enumerate(alive):
                zcol = n + elim_idx.index(e) * len(alive) + zi
                row = [0.0]*nv; row[e] = -n; row[i] = n; row[zcol] = M
                A.append(row); b.append(rj[i] - rj[e] + M)
            row = [0.0]*nv
            for zi in range(len(alive)):
                row[n + elim_idx.index(e) * len(alive) + zi] = -1.0
            A.append(row); b.append(-1.0)
        return np.array(A), np.array(b), weak, nv
    return np.array(A), np.array(b), weak, n

def finals_constraints(W, contestants):
    """Ordering from placement: better placement -> lower combined C."""
    n = W["n"]; p = W["p"]; rj = W["rj"]; rule = W["rule"]
    A = []; b = []
    pls = []
    for i, nm in enumerate(W["names"]):
        for c in contestants:
            if c["name"] == nm and c["placement"]:
                pls.append((i, c["placement"]))
    pls.sort(key=lambda t: t[1])
    for (i, pl_i), (k, pl_k) in zip(pls[:-1], pls[1:]):
        if rule == "percent":
            # percent: HIGHER combined = better; winner has largest p+q
            # C_i > C_k  ->  q_k - q_i < p_i - p_k
            row = [0.0]*n; row[k] = 1.0; row[i] = -1.0
            A.append(row); b.append(p[i] - p[k] - EPS)
        else:
            # rank: LOWER combined = better; C_i < C_k  ->  q_k - q_i < (rj_k - rj_i)/n
            row = [0.0]*n; row[k] = 1.0; row[i] = -1.0
            A.append(row); b.append((rj[k] - rj[i]) / n - EPS)
    if not A:
        return None, None
    return np.array(A), np.array(b)

# ---------- build all week problems ----------
problems = []
for key in sorted(panel, key=lambda k: int(k[1:])):
    season = panel[key]["season"]
    contestants = panel[key]["contestants"]
    scores_by_name = {c["name"]: c["scores"] for c in contestants}
    for w in sorted(panel[key]["weeks"], key=int):
        wk = panel[key]["weeks"][w]
        W = build_week(season, int(w), wk, contestants, scores_by_name)
        if W is None:
            continue
        A, b, weak, nv = constraints_for(W)
        if W["is_final"]:
            Af, bf = finals_constraints(W, contestants)
            if Af is not None:
                A = np.vstack([A, Af]) if len(A) else Af
                b = np.concatenate([b, bf]) if len(b) else bf
        W["A"], W["b"], W["weak"], W["nv"] = A, b, weak, nv
        problems.append(W)

print("total weekly problems:", len(problems))
print("finals:", sum(1 for P in problems if P["is_final"]),
      "| elim weeks:", sum(1 for P in problems if P["elims"]),
      "| no-elim:", sum(1 for P in problems if not P["is_final"] and not P["elims"]),
      "| weak:", sum(1 for P in problems if P["weak"]))

def eq_row(nv, n):
    r = np.zeros(nv); r[:n] = 1.0
    return r

def bounds_for(nv, n):
    bd = [(0, 1.0)]*n + [(0, 1.0)]*(nv - n)
    return bd

# feasibility + drop infeasible finals constraints
skipped = []
for P in problems:
    n, nv = P["n"], P["nv"]
    Au = P["A"] if len(P["A"]) else None
    bu = P["b"] if len(P["b"]) else None
    res = linprog(np.zeros(nv), A_ub=Au, b_ub=bu,
                  A_eq=eq_row(nv, n).reshape(1, -1), b_eq=np.array([1.0]),
                  bounds=bounds_for(nv, n), method="highs")
    if not res.success:
        if P["is_final"]:
            P["A"], P["b"] = np.array([]), np.array([])
            skipped.append((P["season"], P["week"], "finals dropped"))
        else:
            skipped.append((P["season"], P["week"], P["elims"], "INFEASIBLE-KEPT"))
print("infeasible:", len(skipped))
for s in skipped:
    print("  ", s)

# ---------- interval estimation (LP projections) ----------
for P in problems:
    n, nv = P["n"], P["nv"]
    Au = P["A"] if len(P["A"]) else None
    bu = P["b"] if len(P["b"]) else None
    qmin = np.full(n, np.nan); qmax = np.full(n, np.nan)
    for i in range(n):
        c = np.zeros(nv); c[i] = 1.0
        r1 = linprog(c, A_ub=Au, b_ub=bu, A_eq=eq_row(nv, n).reshape(1, -1),
                     b_eq=np.array([1.0]), bounds=bounds_for(nv, n), method="highs")
        r2 = linprog(-c, A_ub=Au, b_ub=bu, A_eq=eq_row(nv, n).reshape(1, -1),
                     b_eq=np.array([1.0]), bounds=bounds_for(nv, n), method="highs")
        if r1.success: qmin[i] = r1.fun
        if r2.success: qmax[i] = -r2.fun
    P["qmin"], P["qmax"] = qmin, qmax

# ---------- point estimate: max entropy + cross-week smoothing (per season) ----------
def point_estimate_season(season_problems, lam=0.5):
    P_by_week = sorted(season_problems, key=lambda P: P["week"])
    nvs = [P["nv"] for P in P_by_week]
    total_vars = sum(nvs)
    offsets = {}
    off = 0
    for P in P_by_week:
        offsets[id(P)] = off
        off += P["nv"]
    q_mask = []
    for P in P_by_week:
        o = offsets[id(P)]
        m = np.zeros(P["nv"]); m[:P["n"]] = 1.0
        q_mask.append((o, m))
    cons = []
    for P in P_by_week:
        o = offsets[id(P)]
        eq = np.zeros(total_vars); eq[o:o+P["n"]] = 1.0
        cons.append({"type": "eq", "fun": lambda x, e=eq: e @ x - 1.0, "jac": lambda x, e=eq: e})
        if len(P["A"]):
            A = P["A"]; b = P["b"]; nv = P["nv"]
            cons.append({"type": "ineq",
                         "fun": lambda x, A=A, b=b, o=o, nv=nv: b - A @ x[o:o+nv],
                         "jac": lambda x, A=A, o=o, nv=nv: -np.hstack([np.zeros((A.shape[0], o)), A, np.zeros((A.shape[0], total_vars-o-nv))])})
    def obj(x):
        q = x.copy(); q[q < 1e-12] = 1e-12
        ent = np.sum(q * np.log(q))
        pen = 0.0
        for a, b2 in zip(P_by_week[:-1], P_by_week[1:]):
            oa, ob = offsets[id(a)], offsets[id(b2)]
            common = [nm for nm in a["names"] if nm in b2["names"]]
            if not common:
                continue
            ia = [a["names"].index(nm) for nm in common]
            ib = [b2["names"].index(nm) for nm in common]
            pen += np.sum((x[oa:oa+a["n"]][ia] - x[ob:ob+b2["n"]][ib])**2)
        return ent + lam * pen
    def grad(x):
        q = x.copy(); q[q < 1e-12] = 1e-12
        g = np.log(q) + 1.0
        pen_g = np.zeros_like(x)
        for a, b2 in zip(P_by_week[:-1], P_by_week[1:]):
            oa, ob = offsets[id(a)], offsets[id(b2)]
            common = [nm for nm in a["names"] if nm in b2["names"]]
            if not common:
                continue
            ia = [a["names"].index(nm) for nm in common]
            ib = [b2["names"].index(nm) for nm in common]
            d = x[oa:oa+a["n"]][ia] - x[ob:ob+b2["n"]][ib]
            pen_g[oa:oa+a["n"]][ia] += 2*d
            pen_g[ob:ob+b2["n"]][ib] -= 2*d
        return g + lam * pen_g
    x0 = np.array([1.0/P["n"] if j < P["n"] else 0.5 for P in P_by_week for j in range(P["nv"])])
    bds = [(1e-9, 1.0) if j < P["n"] else (0.0, 1.0) for P in P_by_week for j in range(P["nv"])]
    res = minimize(obj, x0, jac=grad, constraints=cons, method="SLSQP",
                   bounds=bds, options={"maxiter": 800, "ftol": 1e-10})
    return res.x, res.success

lam = 0.5
season_keys = sorted({P["season"] for P in problems})
n_fail = 0
for s in season_keys:
    sp = [P for P in problems if P["season"] == s]
    x, ok = point_estimate_season(sp, lam=lam)
    if not ok:
        n_fail += 1
        print(f"season {s}: SLSQP FAILED")
    off = 0
    for P in sp:
        P["qhat"] = np.clip(x[off:off+P["n"]], 1e-9, None)
        off += P["nv"]

# ---- projection: snap each week's qhat back onto its feasible set (L2) ----
def project_week(P):
    n, nv = P["n"], P["nv"]
    if not len(P["A"]):
        return
    A = P["A"]; b = P["b"]; q0 = P["qhat"]
    def obj(q):
        return np.sum((q - q0) ** 2)
    def jac(q):
        return 2 * (q - q0)
    cons = [{"type": "eq", "fun": lambda q: np.sum(q) - 1.0, "jac": lambda q: np.ones(n)}]
    if len(A):
        cons.append({"type": "ineq", "fun": lambda q: b - A @ np.concatenate([q, np.full(nv - n, 0.5)]),
                     "jac": lambda q: -A[:, :n]})
    r = minimize(obj, q0, jac=jac, constraints=cons, method="SLSQP",
                 bounds=[(1e-9, 1.0)]*n, options={"maxiter": 300, "ftol": 1e-12})
    P["qhat"] = np.clip(r.x, 1e-9, None)

for P in problems:
    if len(P["A"]):
        project_week(P)
print(f"season optimizations failed: {n_fail}/{len(season_keys)}")

# ---------- consistency replay ----------
def combined_score(P, rule, q):
    n = P["n"]
    if rule == "percent":
        return np.array(P["p"]) + np.array(q)
    return np.array(P["rj"], float) + np.array([n*(1-qi)+1 for qi in q])

n_weeks = 0; n_exact = 0; n_bt = 0; n_rank = 0; n_pct = 0; exact_r = 0; exact_p = 0
bt_r = 0; bt_p = 0
for P in problems:
    if P["is_final"] or not P["elims"]:
        continue
    n_weeks += 1
    q = P["qhat"]
    cval = combined_score(P, P["rule"], q)
    if P["rule"] == "percent":
        worst = np.argsort(cval)[:len(P["elims"])]      # LOWEST combined eliminated
    else:
        worst = np.argsort(-cval)[:len(P["elims"])]     # HIGHEST combined eliminated
    pred = set(P["names"][i] for i in worst)
    actual = set(P["elims"])
    exact = pred == actual
    bottom2 = set(P["names"][i] for i in np.argsort(cval if P["rule"]=="percent" else -cval)[:2])
    in_bt = set(P["elims"]).issubset(bottom2)
    if P["rule"] == "rank":
        n_rank += 1; exact_r += exact; bt_r += in_bt
    else:
        n_pct += 1; exact_p += exact; bt_p += in_bt
    n_exact += exact; n_bt += in_bt
print(f"\nreplay (own rule): {n_exact}/{n_weeks} exact elim ({n_exact/n_weeks:.1%}); "
      f"elim in bottom2: {n_bt}/{n_weeks} ({n_bt/n_weeks:.1%})")
print(f"  rank rule: exact {exact_r}/{n_rank} ({exact_r/n_rank:.1%}), bottom2 {bt_r}/{n_rank} ({bt_r/n_rank:.1%})")
print(f"  percent rule: exact {exact_p}/{n_pct} ({exact_p/n_pct:.1%}), bottom2 {bt_p}/{n_pct} ({bt_p/n_pct:.1%})")

# ---------- save ----------
out = []
for P in problems:
    out.append({
        "season": P["season"], "week": P["week"], "rule": P["rule"], "is_final": P["is_final"],
        "weak": P["weak"], "names": P["names"], "p": P["p"].tolist(), "rj": P["rj"],
        "elims": P["elims"], "qmin": P["qmin"].tolist(), "qmax": P["qmax"].tolist(),
        "qhat": P["qhat"].tolist(),
    })
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print("saved", OUT, "| problems:", len(out))
