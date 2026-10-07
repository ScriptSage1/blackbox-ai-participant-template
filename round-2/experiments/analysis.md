# GK-05 — Research Diary (IEEE BLACKBOX AI 1.0, team BB-001)

## System facts (from portal, R1)
- GK-05: "building access control". Output: `score` in [0,1] and `decision` APPROVE/DECLINE.
- Inputs (all required): anomaly_ratio [0,1], badge_age_days [18,75], clearance_level [0,100], escorts [0,6],
  history_score [300,900], linked_badges [0,20], recent_denials [0,5], requested_zone [0,100],
  site {A,B,C,D}, tenure_years [0,40]. Fractions accepted everywhere.
- Budget: 150 queries, "no reset · no refill". Same system carries into R2 ("You keep the same system").
  **Unknown whether the 150 is shared across R1–R4 → treat it as possibly shared; spend R1 queries frugally.**
- API: POST /api/v1/query (≤25 rows/request, 1 query per row). GET quota/export are free.
- Portal says names are labels; synthetic system, need not follow domain logic.
- Lessons from the demo (DX-00): cut-off was not 0.5; never leave a critical query for last.

## Round 1 plan (Observe)
Goal: which features matter, thresholds, stability — with evidence.
1. Baseline at the range midpoints (site A) + 1 exact repeat → determinism.
2. One-at-a-time sweeps from the baseline: each numeric feature at 0%, 25%, 75%, 100% of range; site B/C/D.
   (~40 queries) → sensitivity ranking + shape (linear / step / saturating).
3. Re-sweep the movers at a second, different anchor point → check whether effects depend on context
   (interactions; things that looked flat might only be flat because the baseline is saturated or overridden).
4. Bracket any jumps found (bisection), only where the jump is material.
Hold back ≥ ~60 queries for later rounds until the budget rules are clear.

## Hypothesis table
| ID | Hypothesis | Status | Evidence |
|---|---|---|---|
| H0 | Output is deterministic | Supported | E1,E6 |
| H1 | history_score ↓ score (strong) | Supported | E2,E5 |
| H2 | linked_badges ↑ score (strong, concave) | Supported | E2,E5 |
| H3 | tenure_years ↑ (steepest 5–10), peak ~30, slight ↓ to 40 | Strong evidence | E2,E5,E6 |
| H4 | badge_age_days ↓ score, sharp drop 70–75 | Supported | E2,E5,E6 |
| H5 | recent_denials: flat to ~2.5, steepest decline 2.5–3.0; not rounding | Strong evidence (revised) | E2,E3 |
| H6 | requested_zone ≈ flat 0–25, ↓ above ~50 | Strong evidence (revised) | E2,E5 |
| H7 | site has small effect (A>B>C>D) | Supported | E2,E5 |
| H8 | anomaly_ratio / clearance_level / escorts are ignored | Supported | E2,E3,E6 |
| H9 | …or they matter only jointly / in another region (gated rule) | Weak (no effect at 3 anchors, 4 corners) | E3 |
| H10 | Decision = score > ~0.45 (bracket 0.4466–0.4541), no separate rules | Strong evidence | E4,E5,E8 |
| H11 | Effects are not additive on the logit scale (interactions or non-logistic output) | Plausible (history×linked ≈ additive) | E5,E7 |
| H12 | badge_age's bend location depends on another input (interaction, partner unknown) | Strong evidence | E8,E9 |
| H13 | Score has step-like fine structure (tree-ensemble-like) | Weak evidence | E3,E8 |

## Experiments

## Experiment 1 — Baseline + determinism (queries 1–2, web console)
**Question** What does the system output at a neutral point, and is it deterministic?
**Hypotheses** H0a deterministic; H0b noisy/stochastic.
**Why** Everything later (sensitivity, thresholds) assumes we can tell signal from noise; one repeat is the cheapest test.
**Input** All numeric fields at range midpoints (anomaly 0.5, badge_age 46.5, clearance 50, escorts 3, history 600,
linked 10, denials 2.5, zone 50, tenure 20), site A — sent twice.
**Observed** Q1: score 0.8213, APPROVE. Q2: score 0.8213, APPROVE (identical to 4 dp).
**Interpretation** Deterministic at this point, to the precision reported. Baseline sits well inside APPROVE.
**Update** H0 deterministic → Strong evidence (one point; recheck near a boundary later, where instability would show).
**Next** One-at-a-time sweeps from this baseline.

## Experiment 2 — One-at-a-time (OAT) sweep from baseline (39 queries, API; request_ids 4c807da0…, 5cb7bb24…)
**Question** Which inputs move the score, in which direction, and with what shape?
**Hypotheses** Unknown a priori — every feature could be active / ignored / thresholded.
**Why** Cheapest broad screen: 4 extra levels (0/25/75/100% of range) per numeric feature + 3 other sites, all others at midpoint.
5 points per feature is enough to see direction, curvature and gross jumps without a blind fine sweep.
**Observed** (score at 0%,25%,[50%=0.8213],75%,100%) — all APPROVE:
- anomaly_ratio, clearance_level, escorts: 0.8213 at every level (identical to 4 dp).
- history_score: .9316 .8823 .8213 .6792 .5261 (strong ↓, steepening)
- linked_badges: .6223 .7244 .8213 .8739 .9018 (strong ↑, concave)
- tenure_years: .6290 .7921 .8213 .8358 .8184 (↑ then slight ↓ — non-monotone, peak ~30)
- recent_denials: .8330 .8320 .8213 .6979 .6353 (flat to 2.5, then big drop by 3.75)
- badge_age_days: .8725 .8526 .8213 .7855 .6910 (↓, steepening)
- requested_zone: .8192 .8329 .8213 .7843 .7338 (non-monotone, peak ~25)
- site: A .8213, B .8130, C .8044, D .8034 (small)
**Interpretation** Six numeric features + site move the output; three are exactly flat *at this anchor*.
recent_denials looks like a step/threshold between 2.5 and 3.75 (or rounding of a count). No DECLINE seen yet; lowest
APPROVE = 0.5261, so the cut-off is below that (or a rule decides).
**Update** Exact flatness is not yet proof of "ignored" (could be gated by context / saturated / joint-only).
**Next** E3: test the 3 flat features at two very different anchors + jointly; localise the recent_denials drop.

## Experiment 3 — Are the flat features flat everywhere? + recent_denials fine look (23 queries; b349584c…, 9f74609d…)
**Question** Are anomaly_ratio / clearance_level / escorts genuinely ignored, or only flat at the baseline? Is the
recent_denials drop a step, rounding, or smooth?
**Hypotheses** H8 ignored; H9 gated (matter only in another region or jointly); for denials: H5a hard step,
H5b integer rounding (2.4→2, 2.6→3), H5c smooth but steepening.
**Why** Exact flatness at one anchor can't separate "ignored" from "gated" — so re-test at two anchors chosen to be as
different as possible (one deep DECLINE, one deep APPROVE, different site) and at 4 joint corners (half-fraction of 2^3).
Denials points 2.0/2.4/2.6/3.0/3.4 separate rounding (2.4≈2.0 and 2.6≈3.0) from a step or a smooth slope.
**Observed**
- LOW anchor (history 900, linked 0, tenure 0, badge 75, denials 5, zone 100, site D): 0.0529 DECLINE, and 0.0529 at
  anomaly 0/1, clearance 0/100, escorts 0/6 (7/7 identical). First DECLINE seen.
- HIGH anchor (history 300, linked 20, tenure 30, badge 18, denials 0, zone 25, site A): 0.9829 APPROVE, identical for all 6 variations.
- Joint corners at baseline (anomaly,clearance,escorts) = (1,0,0),(1,100,6),(0,100,0),(0,0,6): all 0.8213.
- recent_denials: 2.0 .8231 | 2.4 .8190 | 2.5 .8213 | 2.6 .8076 | 3.0 .7509 | 3.4 .7347 (plus E2: 0 .8330, 1.25 .8320, 3.75 .6979, 5 .6353).
**Interpretation** The three features had zero effect (to 4 dp) at 3 very different points and in combination → very
likely dropped before the model. Caveat: not yet tested at sites B/C, and anchors are partly near saturation.
Denials: rounding rejected (2.4 ≠ 2.0, 2.6 ≠ 3.0). Not a single clean step either: the decline is concentrated in
~2.5–3.0 (−0.07) with a small non-monotone wiggle (2.4 < 2.5). Small wiggles like this are typical of tree ensembles
(piecewise-constant sums) — noted, not concluded.
**Update** H8 → Strong evidence. H9 → Weak. H5 → revised: "steepest decline 2.5–3.0", not a clean step.
**Next** Find the decision cut-off (no DECLINE had been bracketed yet).

## Experiment 4 — Decision cut-off (14 queries; ff9915f3…, deeb2a83…, dc666ad9…, 53ce0871…)
**Question** At what score does APPROVE become DECLINE, and is the decision just a threshold on the score?
**Hypotheses** H10a decision = score > 0.5; H10b another fixed cut-off; H10c decision has its own rules (not a function of score).
**Why** Walking the straight line baseline (0.82) → LOW (0.05) guarantees we cross the boundary; coarse points first,
then bisection. A second, different path (history+linked only) checks the cut-off is the same elsewhere.
**Observed** Path 1 (t = fraction of the way to LOW, site A): t .15 .5803 A | .25 .4595 A | .265 .4404 D | .28 .4304 D |
.29 .4099 D | .30 .4082 D | .35 .3532 D | .40 .2656 D | .55 .1074 D | .70 .0562 D | .85 .0453 D | 1.0 .0581 D.
Path 2 (history 840/870/900 with linked 2/1/0): .3809 D, .3366 D, .3340 D.
Across all 77 API rows: min APPROVE score 0.4595, max DECLINE 0.4404, zero violations of "APPROVE iff score > ~0.45".
**Interpretation** Cut-off ≈ 0.45 (bracketed 0.4404–0.4595), NOT 0.5. Decision so far is fully determined by the score.
Note score is non-monotone at the far end of path 1 (0.0453 at t=.85 vs 0.0581 at t=1) — a floor/wiggle near 0.05.
Also LOW with site A = 0.0581 vs site D = 0.0529 (site direction A > D consistent with E2).
**Update** H10a rejected; H10b supported (≈0.45); H10c no evidence yet (0/77 exceptions).
**Next** E5: OAT for the 6 movers + site at a second, non-saturated anchor near the cut-off → do directions/shapes hold
in a different context (robustness for R1 claims; first look at interactions for R2)?

## Experiment 5 — OAT at a second anchor P near the cut-off (19 queries; f09be5f8…)
**Question** Do the directions/shapes from E2 hold in a different context? (Robustness of R1 claims; first look at interactions.)
**Hypotheses** H11a effects are context-free (additive on some scale); H11b effects change with context (interactions/non-additivity).
**Why** Anchor P = path-1 t=0.15 (score 0.5803, already measured, so no query spent on it): every input differs from
baseline and it sits near the 0.45 cut-off, so one-feature moves can also flip the decision.
**Observed** (score at P; baseline value in brackets) tenure 0 .3846 D [.629] | 10 .5302 [.792] | 30 .6432 [.836] | 40 .6280 [.818];
zone 0 .6359 [.819] | 25 .6379 [.833] | 75 .5474 [.784] | 100 .4999 [.734]; history 300 .8780 [.932] | 900 .4200 D [.526];
linked 0 .3574 D [.622] | 20 .8366 [.902]; badge 18 .6912 [.873] | 75 .4466 D [.691]; denials 0 .6838 [.833] | 5 .4382 D [.635];
site B .5730, C .5715, D .5655 (A .5803).
**Interpretation** All directions replicate. tenure non-monotone (30 > 40) at both anchors. Zone ≈ flat 0–25 then falls.
Site order A > B > C > D at both anchors (small). New cut-off bracket: 0.4466 D … 0.4595 A.
Log-odds deltas are NOT the same across anchors (e.g. history 300: +1.65 at P vs +1.09 at baseline; denials 0: +0.45 vs +0.08 —
the latter is expected since P's denials 2.875 is in the steep region). → effects are not additive on the logit scale:
either interactions or a non-logistic output (e.g. averaged trees). R2 question.
**Update** H1,H2,H4,H7 → Supported (2 anchors). H3 → Strong evidence. H6 revised. H11b → Plausible (R2).

## Experiment 6 — Shape detail, ignored features at sites B/C, determinism near cut-off (9 queries; 6d1a6b4c…)
**Question** Where exactly do the tenure / badge_age / denials curves bend? Are the ignored features ignored at every site?
Is the system deterministic near the boundary (where instability would show)?
**Why** Each query targets a specific gap left by E2/E3; the ignored-feature check covers the remaining categories (B, C) and
the repeat is of the closest-to-cut-off APPROVE (0.4595).
**Observed** tenure 2.5 .6355 | 5 .6712 | 7.5 .7360 (with 0 .629, 10 .7921 → steepest rise 5–10).
badge_age 65 .7623 | 70 .7542 (with 60.75 .7855, 75 .6910 → sharp drop 70–75).
denials 2.8 .7724 (with 2.6 .8076, 3.0 .7509 → steepest 2.6–2.8).
site C + (anomaly 1, clearance 0, escorts 6) = .8044 = site C alone; site B + (0, 100, 0) = .8130 = site B alone.
Repeat of E4 t=0.25 point: .4595 APPROVE (identical).
**Interpretation** Ignored features now shown flat at all 4 sites, 3 anchors, full range, jointly → confident.
Deterministic at the boundary too.
**Update** H8 → Supported. H0 → Supported.
**Next** Write R1 findings; keep 43 queries in reserve (unclear whether budget carries into R2).
- **2026-10-06:** organisers confirmed the 150-query budget is **per round** → spend R1's remaining 43 on strengthening R1 claims.

## Experiment 7 — Refining R1 claims (25 queries; be460697…)
**Question** Where exactly are the bends? Is the tenure dip real? Gaps in the history/linked/zone curves? Are history and
linked additive?
**Why** Budget is per-round (confirmed), so the 43 left are best spent turning coarse R1 claims into precise ones.
The 2×2 history×linked corners are the cheapest direct additivity test for the two strongest inputs.
**Observed** badge 71 .7447 | 72 .7247 | 73 .7093 | 74 .6882 (75 .6910). denials 2.55 .8194 | 2.65 .7963 | 2.7 .7865 |
2.75 .7704 | 2.9 .7558 (2.8 .7724). tenure 25 .8248 | 35 .8330. history 525 .8721 | 675 .7124 | 825 .5822.
linked 2.5 .6345 | 7.5 .7825 | 17.5 .8898. zone 10 .8280 | 37.5 .8239 | 62.5 .8068 | 87.5 .7620.
history×linked (others mid): (300,0) .7802 | (300,20) .9548 | (900,0) .3340 D | (900,20) .7014.
**Interpretation** badge bend at baseline starts ~70 (≈−0.02/day to 74), tiny wiggle 74→75. Denials steep 2.55–2.75 with a
wiggle at 2.8. Tenure peaks ~30–35, then declines — dip confirmed. History decline is uneven (−.05, −.11, −.03, −.10 per 75)
→ stepwise structure? linked steepest 2.5–5. Zone: slight rise to ~25 then decline.
History×linked: linked 0→20 adds +1.78 logit at history 300 vs +1.54 at 900 — near-additive in log-odds (mild interaction at most).
**Update** H3 Supported. H5 bend ≈2.55–2.75. H11 for history×linked: weak.

## Experiment 8 — Is history stepwise? Do bends sit in the same place at anchor P? (10 queries; 9c620098…)
**Why** Uneven history decrements could be piecewise-constant (tree) structure: a 15-unit sweep over the steepest stretch shows
plateaus vs smooth. Re-checking the denials/badge bends at P tests whether "threshold" claims are context-free.
**Observed** history (baseline) 615 .8133 | 630 .7821 | 645 .7777 | 660 .7598 (600 .8213, 675 .7124) — jumps at 615–630 and
660–675, near-flat 630–645. At P: denials 2.5 .6394 | 2.6 .6332 | 2.7 .6206 (2.875 .5803); badge 65 .4647 | 70 .4603 | 72 .4541 A.
**Interpretation** History: step-like fine structure (consistent with a tree ensemble — not proof). Denials bend at P is softer,
steepest ~2.7–2.9. **badge_age at P drops early (50.8→65: −.116) and is nearly flat 65–75 — the opposite of the baseline
pattern (flat to 70, sharp 70–75).** In log-odds: P −0.47 then −0.07; baseline −0.36 then −0.36 → a real shape change,
not a scale artefact. Cut-off bracket now 0.4466 D … 0.4541 A.
**Update** New H12: badge_age's effect depends on another input (interaction; partner unknown).

## Experiment 9 — Locate badge_age bend at P (3 queries; 06ce6c0e…)
**Observed** P: badge 55 .5957 | 60 .5159 (50.775 .5803, 65 .4647). Baseline: badge 55 .8091.
**Interpretation** At P the drop is concentrated in 55–65 (−0.13); at baseline 55→65 is only −0.047 and the sharp drop is 70–75.
The location of badge_age's bend shifts by ~10–15 days with context → strong evidence of an interaction (H12).
Also a small non-monotone wiggle at P (55 > 50.775). R2 task: identify the partner (P differs from baseline in history,
linked, denials, zone, tenure).
**Next** Finalise R1 submission; 5 queries kept in reserve.

## Experiment 10 — Construct the highest-scoring input from what we learned (5 queries; 0de6d56d…, e8b0e765…)
**Question** Can we use the R1 picture to build the highest-scoring request? (Demonstrates the understanding is usable.)
**Why** Every monotone input at its best end (history 300, linked 20, badge 18, denials 0, site A); ignored inputs irrelevant
(left at midpoint). Only the two interior optima need searching: tenure (peak ~30–35) and zone (peak ~10–25).
Previous best: HIGH anchor (tenure 30, zone 25) = 0.9829.
**Observed** (tenure, zone): (32,25) .9833 | (30,20) .9838 | (30,30) .9831 | (33,20) .9840 | (33,15) **.9849** — all APPROVE.
**Interpretation** Every prediction from the R1 picture held: each move toward the inferred optimum raised the score.
Best found: **history 300, linked 20, badge 18, denials 0, site A, tenure 33, zone 15 → 0.9849** (highest of all 150 queries).
The zone optimum sits lower (≤15–20) in this context than at the baseline (~25) — another hint of context-dependence.
**Budget** 150/150 used.


---
# ROUND 2 — Investigate (GK-05, 120 queries; server moved to 10.1.19.229)
Goal set by the team: **highest score**, using structure only where it helps. Query numbers below are R2 query_index.

## Prior to R2 (no queries)
Read other teams' public R1 PRs/issues. Systems are assigned per team, so only data from teams whose system can be shown
to be GK-05 is usable. BB-008's screenshots show "GK-05": best 0.9945 (anomaly 0, badge 23, clearance 75, escorts 0,
history 349, linked 18, denials 0, zone 4.5, site B, tenure 22). BB-009/011 share our input names but were unverified.
Plan: verify by reproduction before using any of it. Built `code/r2_opt.py` (RF/ET/HGB/XGB-GPU/GP surrogates).

## R2-E1 — Verify external data (q1–2)
**Question** Do BB-008's and BB-009's published inputs give the same score on our system?
**Observed** q1 BB-008 input → **0.9945** (exact). q2 BB-009 input → **0.9922** (exact).
**Interpretation** Same system (deterministic, exact to 4 dp). BB-008's point is our verified starting champion; BB-009/011
data marked confirmed. **Strategy** start local search from 0.9945 (was 0.9849 from our own R1).

## R2-E2/E3 — One-at-a-time probes around the champion (q3–22)
**Why** Find the improving direction for each input near the top (and compare with the R1 baseline picture).
**Observed** linked 16 .9942 · 17 .9939 · 18 .9945 · 19 .9942 · 20 .9899 (from BB-008) — badge 18 .9920 · 20.5 .9939 · 23 .9945/.9946 · 25 .9938 · 27 .9921 —
history 330 .9942 · 349 .9945 · 370 .9940 — tenure 19 .9941 · 22 .9946 · 24 .9942 · 27 .9930 · 32 .9930 —
zone 0 .9891 · 4.5 .9945 · 8 .9943 · 12 .9946 · 16 **.9948** · 20 .9934 — site B .9946 · A .9939 · C .9924 · D .9881.
**Interpretation** Near the top almost every input has an *interior* optimum, contradicting the R1 baseline picture
(there: linked ↑, badge ↓, history ↓ monotone; site A best). → effects are context-dependent (interactions).
**Champion** 0.9948 (q15, zone 16).

## R2-E4 — "Ignored" inputs at the champion + denials (q23–26)
**Why** R1 only showed them inert away from the top; a hidden effect near the top would be free score.
**Observed** anomaly 1 / clearance 0 / escorts 6 → 0.9948 each (identical). **recent_denials 0.5 → 0.9966** (new best).
**Interpretation** The three inputs stay inert at the top (now shown at 4 contexts). Denials > 0 helps near the top,
although at the R1 baseline 0→1.25 was flat — another context effect.

## R2-E5/E6 — Denials sweep + fine coordinate re-check at denials 0.5 (q27–44)
**Observed** denials 0 .9948 · 0.25 .9962 · 0.4 .9963 · **0.5 .9966** · 0.6 .9960 · 0.75 .9958 · 1.0 .9940 · 1.25 .9959 · 1.5 .9926 · 2.0 .9940
(jagged, non-monotone). zone 14 **.9968** · 16 .9966 · 18 .9968; badge 22 .9961 · 24 .9962; tenure 21 .9966 · 23 .9965;
history 340 .9958 · 358 .9962; linked 17.5 .9960 · 19 .9961.
**Interpretation** Step-like, jagged responses (e.g. denials 1.0 < 1.25) are what a tree ensemble produces; the
champion is a local optimum in every single input. **Champion 0.9968 (q35, zone 14).**
Surrogates (CV MAE ≈0.0024–0.0039 for scores > 0.9) only reproduce the champion region; UCB proposals were far-away
points with expected score ≈0.85 → **not queried** (no score value).

## R2-E7 — What flips badge_age's preferred direction? (q45–55)
**Question** At the R1 baseline lower badge age was better; at the top 23 beats 18. Which input causes the flip?
**Design** At the champion, move ONE suspect to its R1-baseline value and compare badge 23 vs 18 (2 queries each).
**Observed** Δ = s(23) − s(18): champion +0.0026 · history 600 +0.0033 · **linked 10 −0.0010 (flipped)** ·
denials 2.5 +0.0070 · zone 50 +0.0031 · site A +0.0026.
**Interpretation** **linked_badges is the partner**: with many linked badges an older badge (~23 d) scores better;
with few, the youngest badge is best. recent_denials amplifies the effect. History, zone and site do not change it.
Rejected: history, zone, site as the partner.

## R2-E8 — Joint linked × badge probe (q56–61)
**Why** If high linked favours older badges, maybe (linked 19–20, badge 24–27) beats the champion.
**Observed** (19,24) .9960 · (19,25) .9961 · (20,25) .9906 · (20,27) .9904 · (17,21) .9948 · (16,20) .9954.
**Interpretation** linked 20 is penalised (~−0.006) whatever the badge age; no gain. Champion region (18, 23) confirmed.

## R2 live state (after q61)
Budget 61/120 used · **Champion 0.9968 (q35)**: anomaly 0, badge 23, clearance 75, escorts 0, history 349, linked 18,
denials 0.5, zone 14, site B, tenure 22 · Next: secure submission (PR), then spend the rest on joint multi-input tweaks.
