#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""09_verify.py — cross-check every headline number in the paper against live analysis outputs."""
import json
import numpy as np

est = json.load(open("/home/zhenjinchao/projects/mcm-2026/analysis/fan_est.json"))
sysout = json.load(open("/home/zhenjinchao/projects/mcm-2026/analysis/system_out.json"))
checks = []

def chk(name, got, expected):
    ok = abs(got - expected) < 1e-6 if isinstance(expected, float) else str(got) == str(expected)
    checks.append((name, got, expected, "OK" if ok else "MISMATCH"))

# --- structural counts ---
n_finals = sum(1 for P in est if P["is_final"])
n_elim = sum(1 for P in est if not P["is_final"] and P["elims"])
n_noelim = sum(1 for P in est if not P["is_final"] and not P["elims"])
chk("total problems", len(est), 335)
chk("finals weeks", n_finals, 29)
chk("elim weeks", n_elim, 264)
chk("no-elim weeks", n_noelim, 42)

# --- replay by era ---
def comb(P, rule, q):
    n = len(P["names"])
    if rule == "percent": return np.array(P["p"]) + np.array(q)
    return np.array(P["rj"], float) + np.array([n*(1-qi)+1 for qi in q])
def pred(P):
    q = P["qhat"]; c = comb(P, P["rule"], q)
    if P["rule"] == "percent": w = np.argsort(c)[:len(P["elims"])]
    else: w = np.argsort(-c)[:len(P["elims"])]
    return set(P["names"][i] for i in w)
def b2(P):
    c = comb(P, P["rule"], P["qhat"])
    if P["rule"] == "percent": w = np.argsort(c)[:2]
    else: w = np.argsort(-c)[:2]
    return set(P["names"][i] for i in w)

s12 = [P for P in est if not P["is_final"] and P["elims"] and P["season"] <= 2]
s3_27 = [P for P in est if not P["is_final"] and P["elims"] and 3 <= P["season"] <= 27]
s28 = [P for P in est if not P["is_final"] and P["elims"] and P["season"] >= 28]
chk("S1-2 exact", sum(1 for P in s12 if pred(P) == set(P["elims"])), 10)
chk("S3-27 exact", sum(1 for P in s3_27 if pred(P) == set(P["elims"])), 198)
chk("S28+ exact", sum(1 for P in s28 if pred(P) == set(P["elims"])), 19)
chk("S28+ b2", sum(1 for P in s28 if set(P["elims"]).issubset(b2(P))), 31)

# --- uncertainty ---
widths = [P["qmax"][i]-P["qmin"][i] for P in est for i in range(len(P["names"]))]
chk("mean width", round(np.mean(widths), 3), 0.898)
ew = [P["qmax"][i]-P["qmin"][i] for P in est for i in range(len(P["names"])) if P["names"][i] in P["elims"]]
sw = [P["qmax"][i]-P["qmin"][i] for P in est for i in range(len(P["names"])) if P["names"][i] not in P["elims"]]
chk("elim width", round(np.mean(ew), 3), 0.346)
chk("surv width", round(np.mean(sw), 3), 0.965)
w1 = [P["qmax"][i]-P["qmin"][i] for P in est for i in range(len(P["names"])) if P["week"] == 1]
w11 = [P["qmax"][i]-P["qmin"][i] for P in est for i in range(len(P["names"])) if P["week"] == 11]
chk("week1 width", round(np.mean(w1), 3), 0.967)
chk("week11 width", round(np.mean(w11), 3), 0.648)

# --- systems ---
sysok = {k: v for k, v in sysout["systems"].items()}
chk("percent exact", sysok["percent"]["exact"], 232)
chk("rank exact", sysok["rank"]["exact"], 101)
chk("BWF-0.5 exact", sysok["BWF-0.5"]["exact"], 241)
chk("BWF-0.5 b2", sysok["BWF-0.5"]["b2"], 251)
chk("BWF-0.7 exact", sysok["BWF-0.7"]["exact"], 236)
chk("judge_only exact", sysok["judge_only"]["exact"], 94)
chk("fan_only exact", sysok["fan_only"]["exact"], 242)
fin = sysout["finals"]
chk("finals percent winner", fin["percent"][0], 22)
chk("finals BWF-0.5 winner", fin["BWF-0.5"][0], 17)
chk("finals rank winner", fin["rank"][0], 19)

# --- factors ---
fac = json.load(open("/home/zhenjinchao/projects/mcm-2026/analysis/factors_out.json"))
chk("Derek judge effect", round(fac["partner_judge"]["Derek Hough"], 2), 0.68)
chk("Val judge effect", round(fac["partner_judge"]["Valentin Chmerkovskiy"], 2), 0.35)
chk("Artem judge effect", round(fac["partner_judge"]["Artem Chigvintsev"], 2), 0.45)
chk("Koko judge effect", round(fac["partner_judge"]["Koko Iwasaki"], 2), -1.50)
chk("Other fan effect", round(fac["ind_fan"]["Other"], 2), 0.63)
chk("Musician judge effect", round(fac["ind_judge"]["Musician"], 2), 0.22)

print(f"{'CHECK':38s} {'GOT':>10s} {'EXPECTED':>10s}  STATUS")
fails = 0
for name, got, exp, st in checks:
    print(f"{name:38s} {str(got):>10s} {str(exp):>10s}  {st}")
    if st == "MISMATCH": fails += 1
print(f"\n{len(checks)-fails}/{len(checks)} checks passed")
