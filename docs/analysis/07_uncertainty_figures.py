#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
07_uncertainty_figures.py — quantify estimation uncertainty from LP intervals;
generate all figures for the paper.
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EST = "/home/zhenjinchao/projects/mcm-2026/analysis/fan_est.json"
PANEL = "/home/zhenjinchao/projects/mcm-2026/analysis/panel.json"
FIG = "/home/zhenjinchao/projects/mcm-2026/paper/figures/"
import os
os.makedirs(FIG, exist_ok=True)

est = json.load(open(EST))
panel = json.load(open(PANEL))

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
                     "figure.dpi": 150, "savefig.bbox": "tight"})

# ============ uncertainty statistics ============
widths = []       # (season, week, name, width, qhat, is_elim, rule)
for P in est:
    for i, nm in enumerate(P["names"]):
        wd = P["qmax"][i] - P["qmin"][i]
        widths.append({"s": P["season"], "w": P["week"], "name": nm, "width": wd,
                       "qhat": P["qhat"][i], "elim": nm in P["elims"],
                       "rule": P["rule"], "final": P["is_final"]})
W = widths
ws = np.array([x["width"] for x in W])
print(f"interval width: mean={ws.mean():.4f} median={np.median(ws):.4f} "
      f"p90={np.percentile(ws,90):.4f} max={ws.max():.4f}")
# relative width vs uniform share 1/n
rel = [x["width"] * (1/ (1/ (len([y for y in W if y['s']==x['s'] and y['w']==x['w']])))) for x in W]
print(f"relative width (vs 1/n): mean={np.mean(rel):.3f}")
# by rule
for rule in ("rank", "percent"):
    sub = np.array([x["width"] for x in W if x["rule"] == rule])
    print(f"  {rule}: mean={sub.mean():.4f} median={np.median(sub):.4f} n={len(sub)}")
# by eliminated or not
elim_w = np.array([x["width"] for x in W if x["elim"]])
surv_w = np.array([x["width"] for x in W if not x["elim"]])
print(f"eliminated: mean width={elim_w.mean():.4f} (n={len(elim_w)}) | survivors: {surv_w.mean():.4f} (n={len(surv_w)})")
# per-week average (later weeks narrower?)
byw = {}
for x in W:
    byw.setdefault(x["w"], []).append(x["width"])
for w in sorted(byw):
    print(f"  week {w:2d}: mean width={np.mean(byw[w]):.4f} n={len(byw[w])}")

# ============ Figure 1: fan share point estimates for a sample season (S11) ============
def fig_heatmap(season, fname, title):
    Pw = sorted([P for P in est if P["season"] == season], key=lambda x: x["week"])
    names = [c["name"] for c in panel[f"s{season}"]["contestants"]]
    weeks = [P["week"] for P in Pw]
    mat = np.full((len(names), len(weeks)), np.nan)
    for P in Pw:
        wi = weeks.index(P["week"])
        for i, nm in enumerate(P["names"]):
            mat[names.index(nm), wi] = P["qhat"][i]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    im = ax.imshow(mat, aspect="auto", cmap="YlOrRd", vmin=0)
    ax.set_xticks(range(len(weeks))); ax.set_xticklabels([f"W{w}" for w in weeks])
    ax.set_yticks(range(len(names))); ax.set_yticklabels([nm.split()[0] for nm in names], fontsize=7)
    ax.set_title(title)
    cbar = fig.colorbar(im, ax=ax, label="estimated fan share q")
    fig.savefig(FIG + fname); plt.close(fig)

fig_heatmap(11, "fig_fanshare_s11.png", "Season 11 — estimated fan vote shares by week")
fig_heatmap(27, "fig_fanshare_s27.png", "Season 27 — estimated fan vote shares by week")

# ============ Figure 2: interval widths distribution ============
fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.6))
axes[0].hist(ws, bins=40, color="#2c6e91", alpha=0.85)
axes[0].set_xlabel("feasible interval width  qmax - qmin"); axes[0].set_ylabel("contestant-weeks")
axes[0].set_title("(a) Uncertainty: width of feasible interval")
byw_mean = np.array([np.mean(byw[w]) for w in sorted(byw)])
byw_w = np.array(sorted(byw))
axes[1].plot(byw_w, byw_mean, "-o", color="#c0392b", ms=3)
axes[1].set_xlabel("competition week"); axes[1].set_ylabel("mean interval width")
axes[1].set_title("(b) Uncertainty declines over the season")
fig.savefig(FIG + "fig_uncertainty.png"); plt.close(fig)

# ============ Figure 3: replay consistency by season & system ============
def comb(P, rule, q):
    n = len(P["names"])
    if rule == "percent":
        return np.array(P["p"]) + np.array(q)
    return np.array(P["rj"], float) + np.array([n*(1-qi)+1 for qi in q])
def pred(P, rule, q=None):
    q = P["qhat"] if q is None else q
    c = comb(P, rule, q)
    if rule == "percent":
        return set(P["names"][i] for i in np.argsort(c)[:len(P["elims"])])
    return set(P["names"][i] for i in np.argsort(-c)[:len(P["elims"])])
seasons = range(1, 35)
ok_own = []; ok_rank = []; ok_pct = []; tot = []
for s in seasons:
    sub = [P for P in est if P["season"] == s and not P["is_final"] and P["elims"]]
    o = sum(1 for P in sub if pred(P, P["rule"]) == set(P["elims"]))
    r = sum(1 for P in sub if pred(P, "rank") == set(P["elims"]))
    p = sum(1 for P in sub if pred(P, "percent") == set(P["elims"]))
    ok_own.append(o); ok_rank.append(r); ok_pct.append(p); tot.append(len(sub))
fig, ax = plt.subplots(figsize=(7.4, 2.8))
x = np.arange(1, 35)
ax.bar(x - 0.25, ok_pct, 0.5, label="percent rule replay", color="#7f8c8d")
ax.bar(x + 0.25, ok_rank, 0.5, label="rank rule replay", color="#c0392b")
for i, (a, b) in enumerate(zip(ok_pct, ok_rank)):
    if a == b == 0: continue
    ax.annotate("", xy=(i+1+0.25, b), xytext=(i+1+0.25, max(a,b)+0.3),
                arrowprops=dict(arrowstyle="-", color="#2c6e91", lw=0.6))
ax.set_xticks(x[::2]); ax.set_xlabel("season"); ax.set_ylabel("weeks replayed exactly")
ax.set_title("Elimination weeks reproduced exactly, by combination rule (seasons 1–34)")
ax.legend(fontsize=8)
fig.savefig(FIG + "fig_replay_seasons.png"); plt.close(fig)

# ============ Figure 4: controversy trajectories ============
cases = [(2, "Jerry Rice"), (4, "Billy Ray Cyrus"), (11, "Bristol Palin"), (27, "Bobby Bones")]
fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.2))
for ax, (season, name) in zip(axes.flat, cases):
    Pw = sorted([P for P in est if P["season"] == season and name in P["names"]], key=lambda x: x["week"])
    ws_ = []; jr = []; fr = []
    for P in Pw:
        i = P["names"].index(name)
        ws_.append(P["week"]); jr.append(P["rj"][i])
        fr.append(sum(1 for qq in P["qhat"] if qq > P["qhat"][i] + 1e-12) + 1)
    ax.plot(ws_, jr, "-o", color="#c0392b", label="judge rank", ms=4)
    ax.plot(ws_, fr, "-s", color="#2c6e91", label="fan rank (est.)", ms=4)
    n = len(ws_)
    ax.invert_yaxis()
    ax.set_title(f"S{season}: {name} (actual: {[c['results'] for c in panel[f's{season}']['contestants'] if c['name']==name][0]})", fontsize=8)
    ax.set_xlabel("week"); ax.set_ylabel("rank (1 = best)")
    ax.legend(fontsize=7, loc="lower right")
fig.tight_layout(); fig.savefig(FIG + "fig_controversy.png"); plt.close(fig)

# ============ Figure 5: industry effects ============
ind_j = {"Entertainer": 0.004, "Media/Politics": -0.153, "Model": -0.237,
         "Musician": 0.220, "Other": -0.357, "Athlete": 0.0}
ind_f = {"Entertainer": 0.023, "Media/Politics": -0.074, "Model": -0.536,
         "Musician": -0.048, "Other": 0.632, "Athlete": 0.0}
fig, ax = plt.subplots(figsize=(6.4, 2.6))
labels = list(ind_j.keys()); x = np.arange(len(labels)); wd = 0.38
ax.bar(x - wd/2, [ind_j[k] for k in labels], wd, label="judge scores", color="#2c6e91")
ax.bar(x + wd/2, [ind_f[k] for k in labels], wd, label="fan votes", color="#e67e22")
ax.axhline(0, color="k", lw=0.7)
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("effect (z-score, athlete baseline)")
ax.set_title("Industry effects: judge scores vs fan votes (OLS, contestant-week panel)")
ax.legend(fontsize=8)
fig.savefig(FIG + "fig_industry.png"); plt.close(fig)

# ============ Figure 6: partner effects ============
factors = json.load(open("/home/zhenjinchao/projects/mcm-2026/analysis/factors_out.json"))
pj = factors["partner_judge"]; pf = factors["partner_fan"]
top = sorted(pj.items(), key=lambda t: -t[1])[:10]
labels = [t[0] for t in top]; vj = [t[1] for t in top]; vf = [pf.get(t[0], 0) for t in top]
fig, ax = plt.subplots(figsize=(6.4, 2.8))
x = np.arange(len(labels)); wd = 0.38
ax.barh(x + wd/2, vj, wd, label="judge effect", color="#2c6e91")
ax.barh(x - wd/2, vf, wd, label="fan effect", color="#e67e22")
ax.set_yticks(x); ax.set_yticklabels(labels, fontsize=8)
ax.invert_yaxis(); ax.axvline(0, color="k", lw=0.7)
ax.set_xlabel("partner effect (z-score)") 
ax.set_title("Top-10 professional partners by judge-score effect")
ax.legend(fontsize=8, loc="lower right")
fig.savefig(FIG + "fig_partners.png"); plt.close(fig)

# ============ Figure 7: system comparison ============
systems = ["percent", "rank", "BWF-0.3", "BWF-0.5", "BWF-0.7", "judge-only", "fan-only"]
exact = [232, 101, 241, 241, 236, 94, 242]
b2 = [242, 149, 250, 251, 246, 145, 248]
fig, ax = plt.subplots(figsize=(6.4, 2.8))
x = np.arange(len(systems)); wd = 0.38
ax.bar(x - wd/2, np.array(exact)/264*100, wd, label="exact eliminations", color="#2c6e91")
ax.bar(x + wd/2, np.array(b2)/264*100, wd, label="eliminee in bottom two", color="#e67e22")
ax.set_xticks(x); ax.set_xticklabels(systems, fontsize=8)
ax.set_ylabel("% of 264 elimination weeks"); ax.set_ylim(0, 105)
ax.set_title("How often each system reproduces the historical eliminations")
ax.legend(fontsize=8)
fig.savefig(FIG + "fig_systems.png"); plt.close(fig)

# ============ Figure 8: BWF weight sensitivity ============
wvals = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
ex = [239, 241, 241, 241, 237, 236, 233]
fig, ax = plt.subplots(figsize=(5.6, 2.4))
ax.plot(wvals, np.array(ex)/264*100, "-o", color="#2c6e91")
ax.set_xlabel("judge weight w in BWF fusion"); ax.set_ylabel("% weeks exact")
ax.set_ylim(85, 95)
ax.set_title("BWF sensitivity: replay accuracy vs fusion weight")
fig.savefig(FIG + "fig_sensitivity.png"); plt.close(fig)

print("\nall figures saved to", FIG)
