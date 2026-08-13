#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data cleaning & exploratory analysis for 2026 MCM Problem C."""
import csv, json, re
import numpy as np
import pandas as pd

DATA = "/home/zhenjinchao/projects/mcm-2026/2026_MCM-ICM_Problems/2026_MCM_Problem_C_Data.csv"
df = pd.read_csv(DATA, encoding="utf-8-sig")

print("shape:", df.shape)
print("\n--- columns ---")
print(list(df.columns))
print("\n--- dtypes / missing ---")
print(df.dtypes.value_counts())
print("rows with any N/A (raw):", df.isna().any(axis=1).sum())

# results parsing
print("\n--- results value counts (top 15) ---")
print(df["results"].value_counts().head(15))
print("\n--- placement stats ---")
print(df["placement"].describe())
print("unique placements:", sorted(df["placement"].unique()))

# season structure
print("\n--- per-season contestant counts ---")
sc = df.groupby("season").agg(n=("celebrity_name","count"),
                              ages=("celebrity_age_during_season","mean")).reset_index()
for _, r in df.groupby("season")["results"].apply(lambda x: x.tolist()).items():
    pass
# infer max weeks per season from non-N/A score columns
week_cols = [f"week{w}_judge{j}_score" for w in range(1,12) for j in range(1,5)]
for s in sorted(df["season"].unique()):
    sub = df[df["season"]==s]
    maxw = 0
    for w in range(1,12):
        cols = [f"week{w}_judge{j}_score" for j in range(1,5)]
        if sub[cols].notna().any().any():
            maxw = w
    sc.loc[sc["season"]==s, "max_week"] = maxw
    sc.loc[sc["season"]==s, "n_active_final"] = (sub[cols].notna().any(axis=1)).sum()
print(sc.to_string())

# industry counts
print("\n--- industry counts ---")
print(df["celebrity_industry"].value_counts())
print("\n--- home country counts (top 10) ---")
print(df["celebrity_homecountry/region"].value_counts().head(10))

# judge score structure: check decimal scores, N/A pattern per week
print("\n--- week coverage (fraction non-N/A of contestants) ---")
for w in range(1,12):
    cols = [f"week{w}_judge{j}_score" for j in range(1,5)]
    nonna = df[cols].notna().any(axis=1).mean()
    n4 = df[f"week{w}_judge4_score"].notna().mean()
    print(f"week{w}: any-score coverage {nonna:.2%}, judge4 present {n4:.2%}")

# zero score patterns (eliminated -> 0)
zcols = [f"week{w}_judge{j}_score" for w in range(1,12) for j in range(1,5)]
nz = (df[zcols] == 0).sum().sum()
print("\ntotal zero score cells (eliminated-after weeks):", nz)

# unique dancers
print("\nunique pro dancers:", df["ballroom_partner"].nunique())
print("top partners:", df["ballroom_partner"].value_counts().head(10).to_dict())

# check contestants' weekly score = mean over judges of that week? verify with example
ex = df.iloc[1]  # Kelly Monaco season 1
for w in range(1,7):
    vals = [ex[f"week{w}_judge{j}_score"] for j in range(1,5) if not pd.isna(ex[f"week{w}_judge{j}_score"])]
    if vals:
        print("Kelly S1 W%d scores %s mean %.2f" % (w, vals, np.mean(vals)))

# age range
print("\nage range:", df["celebrity_age_during_season"].min(), "-", df["celebrity_age_during_season"].max())
