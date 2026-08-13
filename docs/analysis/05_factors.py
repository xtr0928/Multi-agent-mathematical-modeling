#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_factors.py — how do pro dancers and celebrity traits affect judge scores vs fan votes?
Two OLS models on contestant-week panel:
  y1 = standardized judge score
  y2 = standardized fan rank (from inverse estimates)
predictors: age (linear + age^2), industry group, partner FE, week progress, season trend
Also partner skill rankings and industry×outcome analysis.
"""
import json, re
import numpy as np
import pandas as pd

FAN = "/home/zhenjinchao/projects/mcm-2026/analysis/fan_est.json"
PANEL = "/home/zhenjinchao/projects/mcm-2026/analysis/panel.json"
est = json.load(open(FAN))
panel = json.load(open(PANEL))

IND_GROUPS = {
    "Actor/Actress": "Entertainer", "TV Personality": "Entertainer", "Comedian": "Entertainer",
    "Singer/Rapper": "Musician", "Musician": "Musician", "Producer": "Musician",
    "Athlete": "Athlete", "Sports Broadcaster": "Athlete", "Racing Driver": "Athlete",
    "Model": "Model", "Beauty Pagent": "Model", "Fashion Designer": "Model",
    "Politician": "Media/Politics", "News Anchor": "Media/Politics", "Journalist": "Media/Politics",
    "Radio Personality": "Media/Politics", "Social Media Personality": "Media/Politics",
    "Social media personality": "Media/Politics",
    "Entrepreneur": "Other", "Astronaut": "Other", "Magician": "Other",
    "Motivational Speaker": "Other", "Military": "Other", "Fitness Instructor": "Other",
    "Con artist": "Other", "Conservationist": "Other",
}
def ind_group(x):
    return IND_GROUPS.get(x, "Other")

# ---- build panel rows ----
rows = []
for P in est:
    s = P["season"]
    for i, nm in enumerate(P["names"]):
        c = [c for c in panel[f"s{s}"]["contestants"] if c["name"] == nm][0]
        rows.append({
            "season": s, "week": P["week"], "name": nm,
            "partner": c["partner"], "industry": ind_group(c["industry"]),
            "age": c["age"] if c["age"] else np.nan,
            "p": P["p"][i], "rj": P["rj"][i],
            "q": P["qhat"][i],
            "fr": sum(1 for qq in P["qhat"] if qq > P["qhat"][i] + 1e-12) + 1,  # fan rank 1=most
            "n": len(P["names"]),
            "placement": c["placement"] if c["placement"] else 99,
        })
df = pd.DataFrame(rows)
df = df.dropna(subset=["age"])
print("panel rows:", len(df), "| contestants:", df["name"].nunique(), "| partners:", df["partner"].nunique())

# normalize within-week: judge score z, fan rank z (within each week roster)
def zscore_within_week(g):
    return (g - g.mean()) / g.std(ddof=0) if g.std(ddof=0) > 0 else g * 0
df["z_judge"] = df.groupby(["season", "week"])["p"].transform(lambda g: (g - g.mean())/ (g.std(ddof=0) if g.std(ddof=0)>0 else 1))
df["z_fan"] = df.groupby(["season", "week"])["fr"].transform(lambda g: -(g - g.mean())/ (g.std(ddof=0) if g.std(ddof=0)>0 else 1))  # negate: high fr = bad -> high z_fan = popular

# ---- OLS: judge & fan ~ age + age^2 + industry + partner + week + season ----
import statsmodels.api as sm
# check availability
try:
    import statsmodels
    print("statsmodels", statsmodels.__version__)
except ImportError:
    print("no statsmodels, installing")
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "statsmodels", "-i",
                    "https://mirrors.aliyun.com/pypi/simple/", "-q"])
    import statsmodels
    print("statsmodels installed", statsmodels.__version__)

d = df.copy()
d["age2"] = d["age"] ** 2 / 100.0
d["week"] = d["week"].astype(float)
d["season_c"] = d["season"] - d["season"].mean()

def run_model(ycol, label):
    fe_cols = ["age", "age2", "week", "season_c"]
    dummies = pd.get_dummies(d["industry"], prefix="ind", drop_first=True).astype(float)
    part_dum = pd.get_dummies(d["partner"], prefix="par", drop_first=True).astype(float)
    X = pd.concat([d[fe_cols].astype(float), dummies, part_dum], axis=1)
    X = sm.add_constant(X)
    y = d[ycol].astype(float)
    m = sm.OLS(y, X).fit(cov_type="HC1")
    print(f"\n===== {label} (n={int(m.nobs)}, R2={m.rsquared:.3f}) =====")
    # report key coefficients
    for pat in ["age", "ind_", "week", "season_c"]:
        idx = [c for c in X.columns if c.startswith(pat)]
        rows_out = [(c, m.params[c], m.bse[c], m.pvalues[c]) for c in idx]
        rows_out.sort(key=lambda t: -abs(t[1]))
        print(f"  [{pat}]")
        for c, beta, se, pv in rows_out[:8]:
            print(f"    {c:28s} beta={beta:+.3f} se={se:.3f} p={pv:.4f}")
    # partner effects summary
    pidx = [c for c in X.columns if c.startswith("par_")]
    peff = pd.Series({c[4:]: m.params[c] for c in pidx})
    peff_full = pd.concat([pd.Series({"base": m.params["const"]}), peff])
    return m, X

m_judge, X_judge = run_model("z_judge", "JUDGE score model")
m_fan, X_fan = run_model("z_fan", "FAN rank model")

# ---- partner overall skill ranking (judge-based, placement-based) ----
print("\n===== partner effects (judge-score contribution, top/bottom) =====")
pj = pd.Series({c[4:]: m_judge.params[c] for c in X_judge.columns if c.startswith("par_")})
pf = pd.Series({c[4:]: m_fan.params[c] for c in X_fan.columns if c.startswith("par_")})
common = sorted(set(pj.index) & set(pf.index), key=lambda x: -pj[x])
print("partner (n>=3 seasons) sorted by judge-effect:")
part_counts = df["partner"].value_counts()
for p in common:
    if part_counts.get(p, 0) < 3:
        continue
print("  top10 by judge effect:")
for p in common[:10]:
    print(f"    {p:26s} judge={pj[p]:+.3f} fan={pf.get(p,0):+.3f} (n={part_counts.get(p,0)})")
print("  bottom5 by judge effect:")
for p in common[-5:]:
    print(f"    {p:26s} judge={pj[p]:+.3f} fan={pf.get(p,0):+.3f} (n={part_counts.get(p,0)})")

# ---- industry aggregate: judge vs fan ----
print("\n===== industry effects (model-based) =====")
ind_j = {c[4:]: m_judge.params[c] for c in X_judge.columns if c.startswith("ind_")}
ind_f = {c[4:]: m_fan.params[c] for c in X_fan.columns if c.startswith("ind_")}
for k in sorted(set(ind_j) | set(ind_f)):
    print(f"  {k:18s} judge={ind_j.get(k,0):+.3f} fan={ind_f.get(k,0):+.3f}")

# raw means
print("\n===== raw means by industry =====")
gm = df.groupby("industry").agg(n=("name","count"), judge=("z_judge","mean"), fan=("z_fan","mean"),
                                placement=("placement","mean"), rj=("rj","mean")).round(3)
print(gm.sort_values("judge", ascending=False).to_string())

# ---- age effect ----
print("\n===== age effect (marginal at mean) =====")
for model, label in [(m_judge, "judge"), (m_fan, "fan")]:
    a, a2 = model.params["age"], model.params["age2"]
    print(f"  {label}: dY/dAge = {a:.4f} + 2*{a2:.4f}*Age/100  -> at 30: {a + 2*a2*0.3:.3f}, at 50: {a + 2*a2*0.5:.3f}")

# ---- season trend: fan power growing? ----
print("\n===== week & season trend coefficients =====")
for model, label in [(m_judge, "judge"), (m_fan, "fan")]:
    print(f"  {label}: week={model.params['week']:+.4f} (p={model.pvalues['week']:.4f}), "
          f"season={model.params['season_c']:+.4f} (p={model.pvalues['season_c']:.4f})")

# ---- progress/learning curve: judge score slope per contestant ----
print("\n===== learning curve (judge z-score slope over weeks) =====")
slopes = df.groupby(["season","name"]).apply(lambda g: np.polyfit(g["week"], g["z_judge"], 1)[0] if len(g) >= 3 else np.nan, include_groups=False)
print(f"  mean slope: {slopes.mean():+.4f}  (positive = improving)")
print(f"  n with 3+ weeks: {slopes.notna().sum()}")

# save
df.to_csv("/home/zhenjinchao/projects/mcm-2026/analysis/factors_panel.csv", index=False)
json.dump({"partner_judge": pj.to_dict(), "partner_fan": pf.to_dict(),
           "ind_judge": ind_j, "ind_fan": ind_f},
          open("/home/zhenjinchao/projects/mcm-2026/analysis/factors_out.json", "w"), indent=1)
print("\nsaved factors_out.json")
