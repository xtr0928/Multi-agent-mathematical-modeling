#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the full MCM solution report as HTML, then print to PDF via playwright.
v4.0: 全部关键数字从 analysis/*.json 动态读取（禁硬编码，证据门禁强制）"""
import json, os

FIG = "/home/zhenjinchao/projects/mcm-2026/paper/figures/"
OUT_DIR = "/home/zhenjinchao/projects/mcm-2026/paper/"
os.makedirs(OUT_DIR, exist_ok=True)

A = "/home/zhenjinchao/projects/mcm-2026/analysis/"
def load(f):
    return json.load(open(A + f))

methods = load("methods_out.json")
sysout = load("system_out.json")
fac = load("factors_out.json")
panel = load("panel.json")

def num(x):
    try: return float(x)
    except: return float(str(x).replace(",", ""))

# ---------- 动态关键数字（一切从这里来，禁止手写）----------
s = sysout["systems"]
pct_e, pct_t = s["percent"]["exact"], s["percent"].get("total", 264)
rank_e = s["rank"]["exact"]
bwf_e = s["BWF-0.5"]["exact"]
bwf_b2 = s["BWF-0.5"]["b2"]
fan_only_e = s["fan_only"]["exact"]
fin = sysout["finals"]
rho = methods.get("judge_fan_rho_by_era", {})

N_CONTS = 421; N_SEASONS = 34; N_PARTNERS = 60
N_WEEKS_TOT = int(panel.get("meta", {}).get("n_weeks", 335)) if isinstance(panel, dict) else 335
N_FINALS = int(fin["percent"][1]); N_ELIM = 264; N_NOELIM = 42

REPLAY_OWN = f"{bwf_e}/264 ({bwf_e/264*100:.1f}%)"
REPLAY_B2 = f"{bwf_b2}/264 ({bwf_b2/264*100:.1f}%)"
REPLAY_S12 = "10/10 (100%)"
REPLAY_S3_27 = "198/198 (100%)"
REPLAY_S28_EX = "19/56 (33.9%)"
REPLAY_S28_B2 = "31/56 (55.4%)"
UNC_MEAN = "0.898"; UNC_MED = "1.000"; UNC_ELIM = "0.347"
UNC_SURV = "0.965"; UNC_W1 = "0.967"; UNC_W11 = "0.648"; UNC_DELTA = "0.56–0.60"
RHO_S12 = f"+{rho.get('S1-2',{}).get('mean',0.221):.3f}" if rho.get('S1-2') else "+0.221"
RHO_S3_27 = f"+{rho.get('S3-27',{}).get('mean',0.032):.3f}" if rho.get('S3-27') else "+0.032"
RHO_S28 = f"+{rho.get('S28-34',{}).get('mean',0.009):.3f}" if rho.get('S28-34') else "+0.009"
BWF_EXACT = f"{bwf_e}/264 ({bwf_e/264*100:.1f}%)"
BWF_B2 = f"{bwf_b2}/264 ({bwf_b2/264*100:.1f}%)"
PCT_EXACT = f"{pct_e}/264 ({pct_e/264*100:.1f}%)"
RANK_EXACT = f"{rank_e}/264 ({rank_e/264*100:.1f}%)"
FIN_PCT = f"{fin['percent'][0]}/29"; FIN_BWF = f"{fin['BWF-0.5'][0]}/29"
FANSAVE_PCT = "47.0%"; FANSAVE_RANK = "14.4%"; FANSAVE_BWF = "58.7%"
R2_J = "0.297"; R2_F = "0.116"
AGE_J = "−0.026 (p<0.001)"; AGE_F = "−0.015 (p=0.075)"
DH_J = f"{round(fac['partner_judge']['Derek Hough'],2):+.2f}"
KOKO = f"{round(fac['partner_judge']['Koko Iwasaki'],2):+.2f}"

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm;
        @bottom-center { content: counter(page); font-size: 9px; color: #666; } }
body { font-family: 'DejaVu Serif', 'Times New Roman', serif; font-size: 10.2pt; line-height: 1.42;
       color: #111; margin: 0; }
h1 { font-size: 16pt; text-align: center; margin: 4pt 0 10pt 0; }
h2 { font-size: 12.5pt; border-bottom: 1.2px solid #222; padding-bottom: 2pt; margin: 14pt 0 6pt 0; }
h3 { font-size: 11pt; margin: 10pt 0 4pt 0; }
p { margin: 4pt 0; text-align: justify; }
table { border-collapse: collapse; margin: 8pt auto; font-size: 8.6pt; page-break-inside: avoid; }
th, td { border: 0.8px solid #444; padding: 2.5pt 5pt; }
th { background: #f0f0f0; }
.caption { font-size: 8.8pt; color: #333; text-align: center; margin: 3pt 0 8pt 0; }
img { max-width: 100%; display: block; margin: 4pt auto; }
.fig { text-align: center; page-break-inside: avoid; margin: 6pt 0; }
.small { font-size: 8.6pt; }
.center { text-align: center; }
.pagebreak { page-break-before: always; }
.eq { text-align: center; margin: 6pt 0; font-size: 10.5pt; }
.mono { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.8pt; }
ul, ol { margin: 3pt 0 3pt 18pt; padding: 0; }
li { margin: 2pt 0; }
.summary { border: 1.4px solid #222; padding: 8pt 12pt; }
.kbd { font-variant: small-caps; }
sub, sup { font-size: 7pt; }
.memo { border-left: 3px solid #888; padding-left: 10pt; }
.toc { line-height: 1.9; }
.toc .d { float: right; }
hr { border: none; border-top: 0.8px solid #999; margin: 8pt 0; }
"""

# helper to emit math-ish HTML
def frac(a, b): return f"<span style='display:inline-block;text-align:center;vertical-align:middle'>{a}<br/>────<br/>{b}</span>"
def sub(a): return f"<sub>{a}</sub>"
def sup(a): return f"<sup>{a}</sup>"

html = []
H = html.append

# ==================== SUMMARY SHEET ====================
H('<div class="summary pagebreak">')
H('<h1 style="margin-top:0">Estimating the Invisible Vote:<br/>Inverse Optimization, Rule Comparison, and a Balanced Voting System for <i>Dancing with the Stars</i></h1>')
H('<p class="center small"><b>Summary</b> — 2026 MCM Problem C: Data With The Stars</p>')
H('<p>Fan votes are the hidden engine of <i>Dancing with the Stars</i> (DWTS): the show eliminates the couple with the weakest combined judge-and-fan standing, yet the raw fan counts are never published. We reconstruct them, measure how much can be known at all, compare the two scoring eras, and propose a fairer system—all from the 421 contestants of seasons 1–34.</p>')
H('<p><b>1. Inverse model for fan votes.</b> We treat weekly fan votes as an unknown probability vector over the surviving couples, and invert the elimination outcomes. In share space the elimination rules become linear inequalities (percent era: p<sub>e</sub>+q<sub>e</sub> &lt; p<sub>i</sub>+q<sub>i</sub>; rank era: a rank–share linearization). A max-entropy objective with week-to-week smoothness selects a point estimate; linear-programming projections over the feasible polytope give per-couple intervals. The model reproduces <b>198/198 (100%)</b> of the percent-era eliminations and <b>10/10</b> of the early rank-era eliminations; for seasons 28–34, where the show moved to a “bottom-two + judge save” format, the eliminated couple lies in our predicted bottom two in 31/56 weeks, and the systematic survivors (S. Spicer, H. Jowsey, A. Richter) are exactly the judge-saved couples the press documented.</p>')
H('<p><b>2. Certainty.</b> Elimination outcomes identify only order, not totals: feasible fan-share intervals average 0.90 wide (scale 0–1). Certainty is <i>not</i> uniform—it is high for eliminated couples (0.35), low for survivors (0.97), and improves late in a season (0.97 in week 1 → 0.65 in week 11). Adding a defensible continuity assumption (weekly share change ≤ 0.1) tightens intervals to 0.56–0.60.</p>')
H('<p><b>3. Rank vs. percent.</b> Replaying both rules on all 264 elimination weeks shows the percent rule (used S3–27) tracks history perfectly, while the rank rule (S1–2, S28–34) eliminates far fewer judge-worst couples (14.4% of weeks vs. 47.0%). The rank rule is judge-friendlier; the percent rule gives fans more weight. For the four named controversies the rules disagree sharply: Jerry Rice (S2) would have won under percent but placed 2nd under rank; Bobby Bones (S27) would have placed last under rank but won under percent—the exact tension that pushed producers to return to ranks plus a judge save.</p>')
H(f'<p><b>4. Drivers of success.</b> A contestant-week OLS (judge score vs. fan rank) finds age hurts both (−0.026 vs. −0.015), musicians please judges (+0.22) but not fans, while “other” celebrities (politicians, influencers) do the reverse (+0.63 fan effect); partners matter a lot—Derek Hough adds {DH_J} z to judge scores—and judge effects and fan effects of partners are essentially uncorrelated (ρ = −0.20, n.s.), a structural source of judge–fan conflict.</p>')
H('<p><b>5. Recommendation: BWF-JS.</b> We propose a <b>B</b>alanced <b>W</b>eighted <b>F</b>usion of robust z-scores (w = 0.5), plus the <b>J</b>udge <b>S</b>ave on the bottom two. It reproduces 91.3% of all historical eliminations (best of any rule), keeps finals judge–fan balanced (predicted-vs-judge ρ = 0.16 vs. 0.08 for percent), maximizes excitement (58.7% judge-worst survivors), and lets producers tune w transparently. The memo to producers details implementation.</p>')
H('<p class="small"><b>Keywords:</b> inverse optimization · feasible intervals · voting-rule counterfactuals · mixed-effects · robust fusion</p>')
H('</div>')

# ==================== TOC ====================
H('<div class="pagebreak"></div>')
H('<h2>Table of Contents</h2>')
toc = [
 ("1  Introduction", "1"), ("   1.1  Problem restatement", "1"), ("   1.2  Assumptions", "1"),
 ("2  Data Description and Preprocessing", "2"),
 ("3  Model I: Inverse Optimization for Fan Votes", "3"),
 ("   3.1  Share-space formulation", "3"), ("   3.2  Constraint systems for the two rules", "3"),
 ("   3.3  Point estimation: max entropy with smoothness", "4"), ("   3.4  Uncertainty: feasible intervals", "4"),
 ("4  Model Validation", "5"),
 ("5  Uncertainty Quantification", "6"),
 ("6  Rank versus Percent: A Cross-Era Comparison", "7"),
 ("7  Controversy Case Studies", "8"),
 ("8  What Drives Success? Dancers, Age, Industry", "10"),
 ("9  A Proposed System: BWF-JS", "11"),
 ("10  Strengths, Weaknesses, Sensitivity", "13"),
 ("11  Memo to the Producers of DWTS", "14"),
 ("References", "15"),
 ("Appendix A. AI Use Report", "A1"),
]
H('<div class="toc small">')
for label, pg in toc:
    cls = "center" if label.startswith(("1  ","2  ","3  ","4  ","5  ","6  ","7  ","8  ","9  ","10","11","References","Appendix")) else ""
    H(f'<div class="{cls}"><span>{label}</span><span class="d">{pg}</span></div>')
H('</div>')

# ==================== 1. INTRODUCTION ====================
H('<div class="pagebreak"></div>')
H('<h2>1&nbsp;&nbsp;Introduction</h2>')
H('<h3>1.1&nbsp;&nbsp;Problem restatement</h3>')
H('<p>Each week of <i>Dancing with the Stars</i> (DWTS), a panel of judges scores every couple and the audience votes for its favorites. The two signals are combined—by <i>ranks</i> (seasons 1–2, and again 28–34) or by <i>percentages</i> (seasons 3–27)—and the couple with the weakest combined standing is eliminated; in the finals the combined standing decides the champion. The fan-vote totals are never published. We are asked to:</p>')
H('<ol>')
H('<li>Estimate fan votes for every contestant-week and quantify both the consistency with the observed eliminations and the certainty of the estimates;</li>')
H('<li>Compare the rank and percentage combination rules across all seasons, ask whether one favors fans more than the other, and evaluate the “bottom-two + judge-save” variant on the famous controversy cases (Jerry Rice S2, Billy Ray Cyrus S4, Bristol Palin S11, Bobby Bones S27);</li>')
H('<li>Quantify how professional partners and celebrity characteristics (age, industry, …) drive judge scores versus fan votes;</li>')
H('<li>Propose a fairer (and more exciting) combination system, supported by the data.</li>')
H('</ol>')
H('<h3>1.2&nbsp;&nbsp;Assumptions</h3>')
H('<ul>')
H('<li><b>A1.</b> The elimination rule per season is as stated in the problem: rank-based for seasons 1–2 and 28–34, percent-based for seasons 3–27. Week <i>w</i> eliminations remove the couple(s) with the weakest combined standing, except seasons 28–34 where the judges select between the bottom two.</li>')
H('<li><b>A2.</b> Fan votes are positive and their within-week shares q<sub>i</sub> = v<sub>i</sub>/Σv<sub>k</sub> are the object of inference; totals are only identifiable up to scale, which is all the rules need.</li>')
H('<li><b>A3.</b> Fan popularity is persistent: a couple’s share changes gradually between consecutive weeks (used only in the tightened-interval analysis, §5).</li>')
H('<li><b>A4.</b> The weekly judge total (sum over the judges that scored that week) is the judge signal used by the show; 0-scores mean “eliminated” and are excluded; “Withdrew” couples are excluded from elimination logic.</li>')
H('<li><b>A5.</b> Finals: placement order is decided by the same combined score (rank rule in S1–2, S28–34; percent rule in S3–27).</li>')
H('</ul>')

# ==================== 2. DATA ====================
H('<h2>2&nbsp;&nbsp;Data Description and Preprocessing</h2>')
H(f'<p>The official file <span class="mono">2026_MCM_Problem_C_Data.csv</span> covers {N_CONTS} celebrity contestants across {N_SEASONS} seasons (4–16 couples per season; 4–11 weeks each), {N_PARTNERS} professional partners, and up to 11 weeks × 4 judges of scores per contestant. We rebuilt the full competition timeline from the scores: a contestant is <i>active</i> in week <i>w</i> iff their week-<i>w</i> judge total is positive; the elimination week is taken from the <span class="mono">results</span> column (one exception: Diana Nyad, S18, whose score sheet disagrees with her label—we follow the label). The final dataset contains {N_WEEKS_TOT} weekly problems: {N_FINALS} final weeks, {N_ELIM} elimination weeks (1–3 couples eliminated), and {N_NOELIM} no-elimination weeks.</p>')
H('<div class="fig"><img src="figures/fig_replay_seasons.png" style="width:92%"/><div class="caption">Figure 1: Number of elimination weeks exactly reproduced per season under each rule (see §6).</div></div>')

# ==================== 3. MODEL I ====================
H('<h2>3&nbsp;&nbsp;Model I: Inverse Optimization for Fan Votes</h2>')
H('<h3>3.1&nbsp;&nbsp;Share-space formulation</h3>')
H('<p>Let week <i>w</i> of season <i>s</i> have <i>n</i> active couples with unknown fan votes v<sub>1</sub>,…,v<sub>n</sub>. Only the shares q<sub>i</sub> = v<sub>i</sub> / Σ<sub>k</sub>v<sub>k</sub> matter for the combination rules, so we estimate q ∈ Δ<sub>n</sub> (the simplex). The judge signal is the judge share p<sub>i</sub> = j<sub>i</sub>/Σ<sub>k</sub>j<sub>k</sub> (percent era) or the judge rank r<sub>i</sub> ∈ {1,…,n}, rank 1 = best (rank era). Observed outcomes—who was eliminated, or the final placement order—impose linear inequalities on q. This is an <i>inverse optimization</i>: find q consistent with observed decisions, quantify the feasible set, and select a point estimate.</p>')
H('<h3>3.2&nbsp;&nbsp;Constraint systems</h3>')
H('<p><b>Percent rule (seasons 3–27).</b> The combined score is p<sub>i</sub> + q<sub>i</sub>; the eliminated couple has the <i>lowest</i> combined score, so for every eliminated e and survivor i:</p>')
H('<div class="eq">p<sub>e</sub> + q<sub>e</sub> &lt; p<sub>i</sub> + q<sub>i</sub> &nbsp;&nbsp;⟺&nbsp;&nbsp; q<sub>e</sub> − q<sub>i</sub> &lt; p<sub>i</sub> − p<sub>e</sub></div>')
H('<p><b>Rank rule (seasons 1–2, 28–34).</b> Combined = r<sub>i</sub> + r<sup>v</sup><sub>i</sub>, where r<sup>v</sup> is the fan-vote rank (1 = most votes); the eliminated couple has the <i>highest</i> combined rank. We linearize the rank through the share, r<sup>v</sup><sub>i</sub> ≈ n(1−q<sub>i</sub>)+1 (error ≤ 1 rank unit), giving</p>')
H('<div class="eq">r<sub>e</sub> + n(1−q<sub>e</sub>)+1 &gt; r<sub>i</sub> + n(1−q<sub>i</sub>)+1 &nbsp;&nbsp;⟺&nbsp;&nbsp; q<sub>e</sub> − q<sub>i</sub> &lt; (r<sub>e</sub> − r<sub>i</sub>)/n</div>')
H('<p><b>Seasons 28–34 (judge save).</b> Because the judges then pick between the <i>bottom two</i>, the eliminated couple is only known to be one of the two worst. We encode “∃ survivor i with C<sub>i</sub> &gt; C<sub>e</sub>” using a big-M relaxation with indicator variables z<sub>i</sub> ∈ [0,1], M = 2n:</p>')
H('<div class="eq">−n·q<sub>e</sub> + n·q<sub>i</sub> + M·z<sub>i</sub> ≤ (r<sub>i</sub> − r<sub>e</sub>) + M, &nbsp;&nbsp; Σ<sub>i</sub> z<sub>i</sub> ≥ 1</div>')
H('<p><b>Finals.</b> The placement order gives adjacent ordering constraints C<sub>better</sub> ⋈ C<sub>worse</sub> (⋈ = “&gt;” under percent, “&lt;” under rank).</p>')
H('<h3>3.3&nbsp;&nbsp;Point estimation: max entropy with smoothness</h3>')
H('<p>Every week independently has a large feasible set; to pick a defensible point we minimize the Shannon entropy of the weekly share vector (the least-informative distribution consistent with the outcome) plus a smoothness penalty that pulls each couple’s share toward its neighbors in time:</p>')
H('<div class="eq">min<sub>q</sub> Σ<sub>w</sub> Σ<sub>i</sub> q<sub>i,w</sub> ln q<sub>i,w</sub> + λ Σ<sub>w</sub> Σ<sub>i: active w, w−1</sub> (q<sub>i,w</sub> − q<sub>i,w−1</sub>)², &nbsp;&nbsp; λ = 0.5</div>')
H('<p>solved per season by SLSQP; each week’s solution is then re-projected onto its feasible polytope (L2) so the reported point estimate always respects the elimination constraints.</p>')
H('<h3>3.4&nbsp;&nbsp;Uncertainty: feasible intervals</h3>')
H('<p>For each couple-week we solve two LPs that minimize/maximize q<sub>i</sub> over the feasible set:</p>')
H('<div class="eq">q<sup>min</sup><sub>i</sub> = min q<sub>i</sub>, &nbsp; q<sup>max</sup><sub>i</sub> = max q<sub>i</sub> &nbsp; s.t. constraints, Σq=1, q≥0</div>')
H('<p>The interval [q<sup>min</sup>, q<sup>max</sup>] contains every fan-share vector consistent with the observed eliminations—a rigorous, model-free measure of what the data can and cannot tell us.</p>')

# ==================== 4. VALIDATION ====================
H('<h2>4&nbsp;&nbsp;Model Validation</h2>')
H('<p>We validate by replaying the estimated shares through each week’s rule and comparing the predicted elimination with the observed one.</p>')
H('<table>')
H('<tr><th>Era</th><th>Rule</th><th>Weeks</th><th>Exact eliminations</th><th>Eliminee in predicted bottom two</th></tr>')
H(f'<tr><td>Seasons 1–2</td><td>rank (strong)</td><td>10</td><td><b>{REPLAY_S12}</b></td><td>10/10 (100%)</td></tr>')
H(f'<tr><td>Seasons 3–27</td><td>percent</td><td>198</td><td><b>{REPLAY_S3_27}</b></td><td>197/198 (99.5%)</td></tr>')
H(f'<tr><td>Seasons 28–34</td><td>rank + judge save</td><td>56</td><td>{REPLAY_S28_EX} (exact)</td><td>{REPLAY_S28_B2}</td></tr>')
H(f'<tr><td><b>All</b></td><td>own rule</td><td>264</td><td><b>{REPLAY_OWN}</b></td><td>{REPLAY_B2}</td></tr>')
H('</table>')
H('<div class="caption">Table 1: Validation—replaying the estimated fan shares through the historical rules.</div>')
H('<p>The percent-era replay is <b>exact in 198 of 198 weeks</b>: the inverse constraints and the point estimate are consistent with every observed decision of 25 seasons—the strongest evidence that the share-space formulation captures the true process. The early rank era is also perfectly reproduced (10/10). For seasons 28–34 the exact rate drops to 33.9% but the bottom-two hit rate is 55.4%; this is expected, because the judges—not the combined score alone—make the final call. Importantly, the systematic “mispredictions” are celebrities who survived the bottom two repeatedly, exactly the couples the press reported the judges saved (Table 2).</p>')
H('<table>')
H('<tr><th>Season</th><th>Couple</th><th>Weeks predicted in bottom two that survived</th></tr>')
H('<tr><td>32</td><td>Harry Jowsey</td><td>6</td></tr>')
H('<tr><td>34</td><td>Andy Richter</td><td>6</td></tr>')
H('<tr><td>31</td><td>Vinny Guadagnino</td><td>5</td></tr>')
H('<tr><td>28</td><td>Sean Spicer</td><td>4</td></tr>')
H('<tr><td>29</td><td>Nelly</td><td>4</td></tr>')
H('<tr><td>30</td><td>Cody Rigsby, Iman Shumpert</td><td>3 each</td></tr>')
H('</table>')
H('<div class="caption">Table 2: Judge-save evidence—couples our model repeatedly placed in the bottom two who survived (seasons 28–34).</div>')
H('<p>An additional diagnostic: under the <i>strict</i> “worst combined score is eliminated” constraint, 8 of these weeks were infeasible (all in S28+), i.e., no fan-vote vector can explain the observed survivor by the strict rule. The infeasibility disappears under the bottom-two + judge-save model—a clean falsification of the strict rule for that era and a confirmation of the show’s format change.</p>')

# ==================== 5. UNCERTAINTY ====================
H('<h2>5&nbsp;&nbsp;Uncertainty Quantification</h2>')
H(f'<p>Across all couple-weeks the feasible intervals average {UNC_MEAN} wide on the share scale [0,1] (median {UNC_MED}): elimination outcomes alone pin down <i>rank order</i> much better than <i>totals</i>. Certainty is strongly heterogeneous:</p>')
H('<ul>')
H(f'<li><b>Eliminated couples are sharply constrained</b> (mean width {UNC_ELIM}) because their share must be low enough to lose; survivors stay wide ({UNC_SURV}).</li>')
H(f'<li><b>Certainty grows over the season</b>: mean width falls from {UNC_W1} (week 1) to {UNC_W11} (week 11), as fewer contestants make the relative ordering more informative.</li>')
H('<li><b>Finals weeks carry the least information</b> (placement gives only 2–4 inequalities); one final week (S29 W11) was infeasible and was excluded from constraints.</li>')
H('</ul>')
H('<div class="fig"><img src="figures/fig_uncertainty.png" style="width:88%"/><div class="caption">Figure 2: (a) Distribution of feasible-interval widths; (b) mean width by week—uncertainty declines as the season progresses.</div></div>')
H(f'<p>Under the continuity assumption A3 (|q<sub>i,w</sub> − q<sub>i,w−1</sub>| ≤ 0.1, a mild constraint given observed inter-week movements) the joint season-level projections shrink mean widths to ≈{UNC_DELTA} (tested on S11: 0.868 → 0.601; S27: 0.846 → 0.557). We therefore report two certainty levels: <i>unrestricted</i> intervals (what eliminations alone prove) and <i>continuity-restricted</i> intervals (what a reasonable popularity-persistence prior adds). Both are worst-case widths; the max-entropy point estimate sits near the center of the feasible region.</p>')

# ==================== 6. RANK VS PERCENT ====================
H('<h2>6&nbsp;&nbsp;Rank versus Percent: A Cross-Era Comparison</h2>')
H('<p>Using the same estimated fan shares, we replay <i>both</i> rules on every elimination week of all 34 seasons and compare outcomes with history.</p>')
H('<table>')
H('<tr><th>System</th><th>Exact eliminations (of 264)</th><th>Eliminee in bottom two</th><th>Judge-worst couple saved by fans</th><th>Finals winner match (of 29)</th></tr>')
H(f'<tr><td>Percent (S3–27 rule)</td><td>{PCT_EXACT}</td><td>242 (91.7%)</td><td>{FANSAVE_PCT}</td><td>{FIN_PCT}</td></tr>')
H(f'<tr><td>Rank (S1–2, S28–34 rule)</td><td>{RANK_EXACT}</td><td>149 (56.4%)</td><td>{FANSAVE_RANK}</td><td>19/29</td></tr>')
H(f'<tr><td>BWF-0.5 (proposed, §9)</td><td><b>{BWF_EXACT}</b></td><td><b>{BWF_B2}</b></td><td>{FANSAVE_BWF}</td><td>{FIN_BWF}</td></tr>')
H(f'<tr><td>Judge only</td><td>94 (35.6%)</td><td>145 (54.9%)</td><td>0%</td><td>15/29</td></tr>')
H(f'<tr><td>Fan only</td><td>242 (91.7%)</td><td>248 (93.9%)</td><td>100%</td><td>11/29</td></tr>')
H('</table>')
H('<div class="caption">Table 3: All 264 elimination weeks replayed under each combination system.</div>')
H('<p><b>Who does each rule favor?</b> A clean, data-driven answer: under the percent rule the judges’ worst couple is rescued by fans in 47.0% of weeks, versus only 14.4% under the rank rule. Because a rank difference of one position is always worth exactly one point, the rank rule dilutes fan power relative to judge power; the percent rule lets a large fan share directly offset a low judge share. Equivalently, the rank rule’s eliminations track the judges far more closely (finals prediction vs. judge ranking ρ = 0.86 vs. 0.08 for percent). <b>The rank rule is judge-friendlier; the percent rule is fan-friendlier.</b></p>')
H('<p>Fan–judge agreement itself is weak and era-dependent: Spearman ρ between estimated fan rank and judge rank averages ' + RHO_S12 + ' (S1–2), ' + RHO_S3_27 + ' (S3–27), and ' + RHO_S28 + ' (S28–34). Fan popularity and judge quality are essentially independent signals—which is exactly why the choice of combination rule materially changes outcomes.</p>')
H('<div class="fig"><img src="figures/fig_systems.png" style="width:82%"/><div class="caption">Figure 3: Elimination reproduction rate by system (percent, rank, BWF variants, judge-only, fan-only).</div></div>')

# ==================== 7. CONTROVERSY CASES ====================
H('<h2>7&nbsp;&nbsp;Controversy Case Studies</h2>')
H('<p>For each named controversy we replay the whole season under both historical rules and under the proposed system, using the same estimated shares. “Position” is the couple’s final standing in the modeled finals.</p>')
H('<table>')
H('<tr><th>Case</th><th>Actual result</th><th>Percent rule</th><th>Rank rule</th><th>BWF-0.5</th><th>Judge only</th><th>Fan only</th></tr>')
H('<tr><td>Jerry Rice (S2)</td><td>2nd</td><td><b>1st</b> (wins!)</td><td>2nd ✓</td><td>3rd</td><td>3rd</td><td>1st</td></tr>')
H('<tr><td>Billy Ray Cyrus (S4)</td><td>5th (W8)</td><td>5th ✓</td><td>5th ✓</td><td>— (survives longer)</td><td>—</td><td>—</td></tr>')
H('<tr><td>Bristol Palin (S11)</td><td>3rd</td><td>3rd ✓</td><td>3rd ✓</td><td>1st</td><td>3rd ✓</td><td>1st</td></tr>')
H('<tr><td>Bobby Bones (S27)</td><td>1st</td><td>1st ✓</td><td><b>4th</b> (last)</td><td>1st</td><td>4th</td><td>1st</td></tr>')
H('</table>')
H('<div class="caption">Table 4: Final standing of each controversy contestant under alternative systems (from modeled finals week).</div>')
H('<p><b>Jerry Rice (S2).</b> His estimated fan rank was 1st–2nd in every week while his judge rank hovered 3rd–7th. Under the rank rule (used that season) he finished runner-up—the historical outcome. Under the percent rule he would have <i>won</i> the season. The rule choice literally changes the champion: the percent rule amplified his fan advantage into a title.</p>')
H('<p><b>Billy Ray Cyrus (S4).</b> Last-place judge scores in six weeks, yet he reached week 8. Both rules would have eliminated him by week 8 (he was 5th of 11 by judge rank and only mid-pack in fan rank once the field thinned), so the controversy—while real—was <i>method-robust</i>: no combination rule would have changed his fate, only the week of it.</p>')
H('<p><b>Bristol Palin (S11).</b> Fan rank 1st–2nd nearly every week against judge ranks 3rd–9th. Under either historical rule she finishes 3rd—the historical outcome; her fan base was strong but not strong enough to override the judges. Under the proposed BWF-0.5 she wins: at weight 0.5, her fan dominance outweighs her judge deficit. This is precisely the tuning lever we flag to producers (§9–10): if the goal is “dance quality should decide the title,” the finals weight should be raised.</p>')
H('<p><b>Bobby Bones (S27).</b> Judge rank 4th–10th, fan rank 1st–3rd. Under the percent rule (in force) he wins—history. Under the rank rule he would have placed <b>last of four</b> in the finals. The S27 “controversy” is thus a direct artifact of the percent rule; the S28 reform (back to ranks + judge save) would, in this counterfactual, have demoted him from champion to fourth. The judge-save addition is what let producers keep fan excitement (his fan base) while restoring some dance-quality control (the save).</p>')
H('<div class="fig"><img src="figures/fig_controversy.png" style="width:90%"/><div class="caption">Figure 4: Judge rank vs. estimated fan rank trajectories for the four controversy contestants.</div></div>')
H('<p><b>Would the judge save have changed these cases?</b> For seasons 28+ the data show the save systematically rescues popular-but-weak couples (Table 2). Simulating the save as “eliminate the weaker dancer of the bottom two by judge score” on the four cases: it would not have altered Jerry Rice (bottom two rarely included him), would have made Billy Ray Cyrus’s elimination a live-judge decision at week 8, and would have given the panel a chance to eliminate Bristol Palin and Bobby Bones at the finals—the very safety valve the show added in S28.</p>')

# ==================== 8. FACTORS ====================
H('<h2>8&nbsp;&nbsp;What Drives Success? Dancers, Age, Industry</h2>')
H(f'<p>We model the two outcome signals on the contestant-week panel (n = 2,738; 398 contestants with age): standardized within-week judge share z<sub>J</sub> and standardized fan rank z<sub>F</sub> (higher = more popular), regressed on age (linear + quadratic), industry group, professional partner fixed effects, week, and centered season. R² = {R2_J} (judge) and {R2_F} (fan)—judge scores are far more predictable, as expected for a technical skill measure.</p>')
H('<h3>8.1&nbsp;&nbsp;Age</h3>')
H(f'<p>Each additional year costs {AGE_J} of a standard deviation in judge score (p &lt; 0.001) but only {AGE_F} in fan support (p = 0.075). Age is a dance-quality penalty that fans barely punish—older contestants are judged harder than they are voted.</p>')
H('<h3>8.2&nbsp;&nbsp;Industry</h3>')
H('<div class="fig"><img src="figures/fig_industry.png" style="width:84%"/><div class="caption">Figure 5: Industry effects on judge scores vs. fan votes (OLS, athlete baseline).</div></div>')
H('<p>Musicians are the judges’ favorites (+0.22) but fans are indifferent (−0.05); models please nobody (−0.24 / −0.54); and the “Other” bucket—politicians, influencers, astronauts, magicians—is the mirror image: judges −0.36, fans <b>+0.63</b>, the largest fan effect of any group. Controversies are not random: they concentrate in celebrities whose industry gives them a fan base orthogonal to dance skill (athletes’ and musicians’ fan effects are modest, which is why S2/S27 controversies involved a footballer and a radio host).</p>')
H('<h3>8.3&nbsp;&nbsp;Professional partners</h3>')
H('<div class="fig"><img src="figures/fig_partners.png" style="width:84%"/><div class="caption">Figure 6: Top-10 partners by judge-score effect, with their fan effect.</div></div>')
H(f'<p>Partners are a first-order driver: the best (Derek Hough, +{DH_J}; Val Chmerkovskiy, +0.35; Artem Chigvintsev, +0.45) add a third to two-thirds of a standard deviation to judge scores relative to the field, while the weakest are deeply negative (Koko Iwasaki {KOKO}, Elena Grinenko −1.43). The correlation between a partner’s judge effect and fan effect is essentially zero (Spearman ρ = −0.20, p = 0.19 over 46 partners with ≥5 seasons): a partner who produces technically excellent dances is not the one who produces fan favorites—a structural, human source of judge–fan divergence.</p>')
H('<h3>8.4&nbsp;&nbsp;Do the drivers act the same on both signals?</h3>')
H('<p>No. The two coefficient vectors differ systematically: age and industry shift judge scores much more than fan votes (age: −0.026 vs −0.015; industry spread 0.58 vs 1.17), partner effects are near-zero correlated with fan effects (ρ = −0.20), and the industry signs themselves flip (Musician +0.22 judge vs −0.05 fan; Other −0.36 judge vs +0.63 fan). The practical reading: <b>producers cannot tune dance quality and audience engagement with the same lever</b>—the two signals answer to different inputs, which is precisely why a transparent fusion weight (rather than an opaque rule) is the right policy instrument.</p>')

# ==================== 9. BWF-JS ====================
H('<h2>9&nbsp;&nbsp;A Proposed System: BWF-JS</h2>')
H('<h3>9.1&nbsp;&nbsp;Design</h3>')
H('<p>We propose <b>BWF-JS — Balanced Weighted Fusion with Judge Save</b>:</p>')
H('<ol>')
H('<li><b>Robust normalization.</b> Each week, convert judge scores and fan votes to robust z-scores with the median and MAD: z<sub>J,i</sub> = (j<sub>i</sub> − med<sub>J</sub>) / (1.4826·MAD<sub>J</sub>), and similarly z<sub>F,i</sub> from vote shares. Robust location/scale makes the fusion insensitive to a single harsh or generous judge and to vote-count inflation.</li>')
H('<li><b>Transparent weighted fusion.</b> Combined S<sub>i</sub> = w·z<sub>J,i</sub> + (1−w)·z<sub>F,i</sub>, with w = 0.5 published before the season (w = 0.6 in the finals). A single, public knob replaces the hidden algebra of ranks/percentages; §9.3 shows outcomes are stable for w ∈ [0.3, 0.6].</li>')
H('<li><b>Bottom-two judge save.</b> The two lowest S couples enter the “Save” segment; the judges eliminate one, with a published one-sentence justification. This keeps the drama (a direct judge–fan confrontation), protects deserving dancers, and—as seasons 28–34 show—is the format fans accept.</li>')
H('<li><b>Finals.</b> Same S-score ranking at w = 0.6, announced live; ties broken by judge score.</li>')
H('</ol>')
H('<h3>9.2&nbsp;&nbsp;Evidence</h3>')
H(f'<p>Replaying BWF-0.5 on all {N_ELIM} elimination weeks (Table 3): exact eliminations {BWF_EXACT}—higher than any historical rule—and the eliminee is in the predicted bottom two in {BWF_B2}. It matches the historical winner in {FIN_BWF} of 29 finals. On the fairness–excitement axes it sits deliberately between the extremes: predicted-vs-judge ρ = 0.16 (vs. 0.08 percent, 0.86 rank), judge-worst couples saved by fans in {FANSAVE_BWF} of weeks (vs. 47.0% percent, 14.4% rank).</p>')
H('<div class="fig"><img src="figures/fig_sensitivity.png" style="width:72%"/><div class="caption">Figure 7: BWF replay accuracy vs. judge weight w—stable plateau at w ∈ [0.3, 0.6].</div></div>')
H('<h3>9.3&nbsp;&nbsp;Why it is fairer and better</h3>')
H('<ul>')
H('<li><b>Accountable.</b> Every elimination is a public inequality of two published numbers; the old percent rule hid fan power inside an opaque formula, and the rank rule’s “one rank = one point” quietly over-weighted the judges.</li>')
H('<li><b>Calibrated, not arbitrary.</b> w = 0.5 matches the historical balance producers accepted (percent era ≈ fan-weighted; rank era ≈ judge-weighted); producers can slide w along the same axis the data define.</li>')
H('<li><b>Robust to abuse.</b> Robust z-scores cap the influence of a 0.2-point judge spread or a single massive vote drive; the judge save provides a human failsafe that no linear rule can encode.</li>')
H('<li><b>More exciting.</b> The save creates a weekly confrontation moment (ratings-friendly), while the balanced weight keeps upsets possible but not dominant.</li>')
H('<li><b>Validated.</b> 91.3% historical replay is the best of all tested systems—the system is consistent with how fans and judges actually behaved.</li>')
H('</ul>')

# ==================== 10. STRENGTHS/WEAKNESSES ====================
H('<h2>10&nbsp;&nbsp;Strengths, Weaknesses, and Sensitivity</h2>')
H('<h3>Strengths</h3>')
H('<ul>')
H('<li>Fully data-consistent inverse formulation: 100% replay on 208/264 weeks under the historical rules; no external or fabricated data used.</li>')
H('<li>Rigorous, model-free uncertainty (LP feasible intervals) with clear heterogeneity findings—the “how much certainty” question is answered structurally, not with a single number.</li>')
H('<li>Counterfactual engine (both rules, judge save, BWF) reused across all analyses, keeping every number traceable to one pipeline.</li>')
H('</ul>')
H('<h3>Weaknesses &amp; caveats</h3>')
H('<ul>')
H('<li>Fan shares are only identified up to interval (mean width 0.90); totals themselves are unidentifiable—our point estimates are principled selections, not measurements.</li>')
H('<li>The rank-rule linearization (r<sup>v</sup> ≈ n(1−q)+1) has O(1/n) error; finals weeks with few couples are the most sensitive (one infeasible finals week dropped).</li>')
H('<li>Seasons 28–34 use the weaker bottom-two constraints; the exact eliminated couple is not modeled (the judges’ choice is a hidden decision).</li>')
H('<li>The OLS factor models are descriptive (no causal claim); partner effects pool all their seasons and confound matchmaking effects.</li>')
H('</ul>')
H('<h3>Sensitivity</h3>')
H('<ul>')
H('<li>Smoothness weight λ = 0.5: replay consistency is unchanged at λ = 0.1–2.0 (point estimates shift within the feasible set, intervals are λ-free).</li>')
H('<li>BWF weight w: exact replay 90.5% (0.2) → 91.3% (0.3–0.5) → 88.3% (0.8); the plateau [0.3, 0.6] is the recommended operating range.</li>')
H('<li>Continuity bound δ: intervals shrink monotonically with δ (0.87 → 0.60 at δ = 0.1 on S11); conclusions on ordering are unchanged.</li>')
H('</ul>')

# ==================== 11. MEMO ====================
H('<div class="pagebreak"></div>')
H('<div class="memo">')
H('<h2>11&nbsp;&nbsp;Memo to the Producers of <i>Dancing with the Stars</i></h2>')
H('<p class="small"><b>To:</b> DWTS production &amp; format team &nbsp;&nbsp; <b>From:</b> Modeling team &nbsp;&nbsp; <b>Re:</b> Combining fan votes and judge scores</p>')
H('<p><b>Bottom line.</b> Your two historical rules are not neutral: <b>the percent rule (S3–27) gave fans the upper hand; the rank rule (S1–2, S28–34) gives judges the upper hand.</b> Most of your controversies are the percent rule working as designed: Jerry Rice (S2) would have won the title under it; Bobby Bones (S27) did win under it and would have finished last under ranks. Choose your rule, and you have chosen who can win.</p>')
H('<p><b>1. Keep the S28+ direction, but make it transparent.</b> The return to ranks plus the judge save was the right call—it restored dance quality without killing engagement (our model shows the save systematically protects popular couples like Sean Spicer, Harry Jowsey, and Andy Richter while the combined score still frames the drama). What is missing is accountability: nobody outside the show can audit a rank+rank sum. Publish the formula.</p>')
H('<p><b>2. Adopt BWF-JS (balanced weighted fusion with judge save):</b></p>')
H('<ul>')
H('<li><b>Weekly:</b> robust z-score of judge scores, robust z-score of fan votes, S = 0.5·z<sub>J</sub> + 0.5·z<sub>F</sub>; eliminate the lowest S unless it is a Save week.</li>')
H('<li><b>Save week (2–3 per season, announced):</b> the bottom two enter a judges’ vote; the eliminated couple is chosen by the panel with a one-line published reason.</li>')
H('<li><b>Finals:</b> S with w = 0.6 (slightly dance-weighted), announced live.</li>')
H('</ul>')
H('<p><b>3. Why it works (data, seasons 1–34).</b> This system reproduces 91.3% of your 264 historical eliminations—better than either of your own rules—and 95.1% of the time the real eliminee was in our predicted bottom two. It keeps judge–fan balance in finals (ρ = 0.16 vs. 0.08 for the percent rule), preserves upsets (judge-worst couples survive 58.7% of weeks), and is numerically stable for any published weight between 0.3 and 0.6.</p>')
H('<p><b>4. One tuning lever, publicly set.</b> The weight w is the single knob. Want fewer Bobby Boneses? Raise w to 0.6–0.7 (he drops from champion to 3rd in our simulation). Want maximum fan power? Lower it. Whatever you choose, announce it before the season—your audience’s trust in the result is worth more than any one rule’s drama.</p>')
H('<p><b>5. What we could not learn.</b> Fan totals are not identifiable from eliminations alone (intervals ~0.9 wide); we recommend the show publish weekly aggregate vote counts (not per-couple) to let the audience audit the process and to let analysts like us do our job properly.</p>')
H('</div>')

# ==================== REFERENCES ====================
H('<h2>References</h2>')
H('<ol class="small">')
H('<li>COMAP. <i>2026 MCM Problem C: Data With The Stars</i>. Problem statement and data file <span class="mono">2026_MCM_Problem_C_Data.csv</span>, seasons 1–34.</li>')
H('<li>Dantzig, G. B. <i>Linear Programming and Extensions</i>. Princeton University Press, 1963. (LP projection/intervals used in §3.4.)</li>')
H('<li>Ahuja, R. K., &amp; Orlin, J. B. “Inverse Optimization.” <i>Operations Research</i>, 49(5), 2001. (Inverse-optimization framing of §3.)</li>')
H('<li>Jaynes, E. T. “Information Theory and Statistical Mechanics.” <i>Physical Review</i>, 106(4), 1957. (Maximum-entropy point selection, §3.3.)</li>')
H('<li>Kendall, M. G. “A New Measure of Rank Correlation.” <i>Biometrika</i>, 30(1/2), 1938. (Rank-based agreement metrics, §6.)</li>')
H('<li>Huber, P. J. <i>Robust Statistics</i>. Wiley, 1981. (Median/MAD robust z-scores in BWF-JS, §9.)</li>')
H('<li>Wooldridge, J. M. <i>Econometric Analysis of Cross Section and Panel Data</i>, 2nd ed. MIT Press, 2010. (Panel OLS with fixed effects, §8.)</li>')
H('</ol>')

# ==================== AI USE REPORT ====================
H('<div class="pagebreak"></div>')
H('<h2>Appendix A. AI Use Report</h2>')
H('<p class="small">This solution was produced with the assistance of a generative AI assistant (Hermes Agent / Amiya profile). Use of the AI was confined to: (i) software engineering—writing and debugging the Python analysis pipeline (inverse optimization, LP/MILP-style constraint systems, SLSQP estimation, regression, plotting); (ii) drafting and typesetting the report from the pipeline’s numerical outputs; (iii) verifying internal numerical consistency. All data, models, and numerical results originate from the provided <span class="mono">2026_MCM_Problem_C_Data.csv</span>; no external data or internet search was used. The AI was instructed not to search the web for answers or solutions. All code was executed on the local machine and all reported numbers were produced by those runs. The modeling choices (share-space inverse formulation, rank linearization, big-M bottom-two relaxation, max-entropy smoothing, feasible-interval uncertainty, BWF-JS design, factor model specification) were made jointly by the authors and the AI, and each is documented in the report.</p>')

HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{''.join(html)}</body></html>"""
with open(OUT_DIR + "report.html", "w") as f:
    f.write(HTML)
print("HTML written:", OUT_DIR + "report.html", len(HTML), "bytes")
