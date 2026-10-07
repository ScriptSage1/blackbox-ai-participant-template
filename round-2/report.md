# round-2 — Investigate

**Team:** BB-001
**System:** GK-05
**Queries used:** see `findings.json` (`queries_used`); budget 120
**Best score this round:** stated in the last claim of `findings.json`, kept current as the round runs

## What we concluded

1. **The Round 1 picture was a picture of one region, not of the system.** At the all-midpoint baseline every
   input looked monotone: lowest `badge_age_days`, highest `linked_badges`, lowest `history_score`, 0 `recent_denials`
   and site A were each best. Near the top of the score range, almost every input has an *interior* optimum:
   - `badge_age_days` ≈ 23
   - `linked_badges` 18
   - `history_score` ≈ 350
   - `recent_denials` ≈ 0.5
   - `requested_zone` ≈ 14–18
   - `tenure_years` ≈ 22
   - site B

   The best joint input is not the combination of the per-input optima from Round 1.
2. **`badge_age_days` interacts with `linked_badges`.** This explains Round 1's open question about why the badge-age
   drop moved between operating points. With linked_badges 18 an older badge (23 d) beats the youngest (18 d) by
   +0.0026. Moving linked_badges to 10, with nothing else changed, reverses it (−0.0010). Moving `history_score`,
   `requested_zone` or `site` to their baseline values does not reverse it. High `recent_denials` makes the
   older-badge advantage larger (+0.0070 at 2.5).
3. **`recent_denials` has a context-dependent, jagged effect.** Near the top, 0.5 beats 0 (0.9966 vs 0.9948), and
   the curve zig-zags (1.0 .9940, 1.25 .9959, 1.5 .9926). At the Round 1 baseline, 0–1.25 was flat.
4. **`anomaly_ratio`, `clearance_level` and `escorts` are dropped.** Their opposite extremes leave the score
   unchanged at the high-score champion too. Together with Round 1 that makes four contexts, all sites, full ranges.
5. **The response is step-like, not smooth.** Small non-monotone zig-zags in several inputs (denials 1.0 < 1.25,
   zone 16 < 14 = 18, linked 17 < 16 < 18) are typical of a tree ensemble's piecewise-constant output. This is a
   hypothesis, not a proven fact (see below).

## How we got there

1. **Starting point, verified (q1–2).** Other teams' public Round 1 issues reported GK-05 results. Systems differ by
   team, so we used them only after reproducing them ourselves. BB-008's published input returned exactly **0.9945**
   (q1), and BB-009's returned exactly 0.9922 (q2). Same system, deterministic. Credit for the 0.9945 starting input
   goes to team BB-008 (their issue #63); everything after q1 is our own investigation.
2. **One-at-a-time probes around the champion (q3–22).** This showed interior optima for nearly every input, unlike
   the Round 1 baseline. That points to interactions, since the per-input shapes depend on where you stand.
3. **Testing the "ignored" inputs at the champion (q23–25), plus `recent_denials` 0.5 (q26).** The dropped inputs
   stayed dropped. Denials 0.5 gave the biggest single jump of the round (0.9948 → 0.9966).
4. **Fine re-check of every input at the new point (q27–44).** The champion is a local optimum in each single
   input. Best 0.9968 at zone 14 (q35).
5. **Which input flips badge_age's preferred direction? (q45–55).** We moved one suspect at a time and compared badge
   23 against 18. Only `linked_badges` flips it. This is the experiment that tells the competing explanations apart.
6. **Joint linked × badge probe (q56–61).** If high linked favours older badges, maybe linked 19–20 with badge 24–27
   would be better. It isn't: linked 20 costs about 0.006 at any badge age.

The surrogate models (random forest, extra trees, gradient boosting, XGBoost, Gaussian process; CV error ≈0.002–0.004
on scores above 0.9) were used to rank candidates. They could not see above the observed maximum. Their high-uncertainty
proposals were far-away points with an expected score near 0.85, so we did not spend queries on them.

The full diary is in `experiments/analysis.md`, and every Round 2 query is in `experiments/queries_r2.csv`.

## What we ruled out

- **"Lower badge age is always better."** Near the top, 23 days beats 18 (0.9945 vs 0.9920).
- **"More linked badges is always better."** Near the top, 18 beats 20 by about 0.005.
- **"Lower history is always better."** 349 beats 330 and 370, and 300 was worse in BB-009's verified context.
- **"Zero denials is best."** 0.5 beats 0 near the top.
- **History, zone or site as badge_age's interaction partner.** None of them flips the badge-age comparison.
- **The dropped inputs acting near the maximum.** They are unchanged at the champion too.
- **Site A as best everywhere.** Near the top B .9946 > A .9939 > C .9924 > D .9881.
- **linked 19–20 with an older badge beating the champion.** It is 0.004–0.006 worse.

## What we are still unsure about

- **Whether the model is a tree ensemble.** The zig-zags fit that, but a smooth model with many interactions could
  produce some of them. We have not found a clean split boundary in this round.
- **The exact form of the linked × badge interaction** (product, ratio, or a tree split on both). We tested two
  linked levels for the flip and four pairs jointly.
- **The global maximum.** The champion is a local optimum in every single input and in the joint moves we tried. A
  better region elsewhere cannot be excluded.
