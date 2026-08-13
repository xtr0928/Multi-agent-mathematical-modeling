#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_pipeline.py — build per-season/per-week active rosters & elimination events.
Output: analysis/panel.json  (machine-readable, for all downstream models)
Also cross-validates inferred eliminations against the `results` column.
"""
import json, re
import numpy as np
import pandas as pd

DATA = "/home/zhenjinchao/projects/mcm-2026/2026_MCM-ICM_Problems/2026_MCM_Problem_C_Data.csv"
OUT  = "/home/zhenjinchao/projects/mcm-2026/analysis/panel.json"

df = pd.read_csv(DATA, encoding="utf-8-sig")
WEEKS = range(1, 12)
JUDGES = range(1, 5)

def weekly_scores(row, w):
    """Total judge score for week w; None if the week didn't run for this contestant."""
    vals = []
    for j in JUDGES:
        v = row[f"week{w}_judge{j}_score"]
        if pd.isna(v):
            continue
        vals.append(float(v))
    if not vals:
        return None
    return sum(vals)  # sum of the judges that actually scored

def active_weeks(row):
    aw = []
    for w in WEEKS:
        s = weekly_scores(row, w)
        if s is not None and s > 0:
            aw.append(w)
    return aw

panel = {}
mismatch = []
withdrawn = []
for _, row in df.iterrows():
    name = str(row["celebrity_name"]).strip()
    partner_raw = str(row["ballroom_partner"]).strip()
    partner = partner_raw.split(" (")[0].split("/")[0].strip()  # S34 has extra notes; keep main partner
    season = int(row["season"])
    res = str(row["results"]).strip()
    is_withdrew = res.lower().startswith("withdrew")
    aw = active_weeks(row)
    elim_week = None
    if not is_withdrew:
        m = re.search(r"Eliminated Week (\d+)", res)
        if m:
            elim_week = int(m.group(1))
        elif res.lower() == "withdrew":
            pass
        # inferred: last active week is the elimination week (end of that show)
        inferred_elim = max(aw) if aw else None
        # finalists: placement <= 3 (or 4-5 in some seasons) -> not eliminated
        is_finalist = bool(re.search(r"Place", res))
        if elim_week is not None:
            if inferred_elim != elim_week:
                mismatch.append((season, name, res, elim_week, inferred_elim))
        elif not is_finalist:
            mismatch.append((season, name, res, None, inferred_elim))
    else:
        withdrawn.append((season, name, res, max(aw) if aw else None))

    key = f"s{season}"
    panel.setdefault(key, {"season": season, "contestants": []})
    panel[key]["contestants"].append({
        "name": name,
        "partner": partner,
        "industry": str(row["celebrity_industry"]).strip(),
        "homestate": str(row["celebrity_homestate"]).strip(),
        "country": str(row["celebrity_homecountry/region"]).strip(),
        "age": None if pd.isna(row["celebrity_age_during_season"]) else float(row["celebrity_age_during_season"]),
        "results": res,
        "placement": None if pd.isna(row["placement"]) else int(row["placement"]),
        "withdrew": is_withdrew,
        "scores": {w: weekly_scores(row, w) for w in WEEKS},
    })

# per-week active roster + elimination set (from `results` field; scores for activity)
for key, S in panel.items():
    roster = S["contestants"]
    elim_map = {}
    for c in roster:
        if c["withdrew"] or re.search(r"Place", c["results"]):
            continue
        m = re.search(r"Eliminated Week (\d+)", c["results"])
        if m:
            elim_map[c["name"]] = int(m.group(1))
        else:
            aw = [w for w in WEEKS if (c["scores"][w] or 0) > 0]
            if aw:
                elim_map[c["name"]] = max(aw)  # fallback: score-based
    for w in WEEKS:
        active = [c for c in roster if not c["withdrew"] and (c["scores"][w] or 0) > 0]
        if not active:
            continue
        elims = [nm for nm, ew in elim_map.items() if ew == w and nm in [c["name"] for c in active]]
        # also include eliminated-but-no-scores this week (e.g. Diana Nyad S18)
        elims += [nm for nm, ew in elim_map.items() if ew == w and nm not in [c["name"] for c in active]]
        wd = [c["name"] for c in roster if c["withdrew"] and (c["scores"][w] or 0) > 0]
        S.setdefault("weeks", {})[str(w)] = {
            "active": [c["name"] for c in active],
            "eliminated": elims,
            "withdrew": wd,
        }

# sanity: season lengths & finalists
print("=== per-season structure ===")
for key in sorted(panel, key=lambda k: int(k[1:])):
    S = panel[key]
    ws = sorted(int(w) for w in S.get("weeks", {}))
    finals = [c["name"] for c in S["contestants"] if not c["withdrew"] and re.search(r"Place", c["results"])]
    print(f"{key}: n={len(S['contestants'])} weeks={ws} finalists={finals}")

print("\n=== results-vs-scores mismatches (elim week inferred) ===")
for m in mismatch:
    print(m)
print("total mismatches:", len(mismatch))
print("\n=== withdrawn ===")
for w in withdrawn:
    print(w)

with open(OUT, "w") as f:
    json.dump(panel, f, ensure_ascii=False, indent=1)
print("\nsaved", OUT)
