# round-2 — Investigate

**Team:** BB-001
**System:** GK-05
**Queries used:** 170 / 170 (50 extra queries were granted mid-round)
**Best score this round:** **0.9972** (R2 query 83): badge_age_days 23.5, linked_badges 18.4, history_score 349, recent_denials 0.5, requested_zone 18, site B, tenure_years 22 (anomaly_ratio 0, clearance_level 75, escorts 0 — inert). Tied by 10 other queries.

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
   **`linked_badges` also gates the `recent_denials` effect**: near the top, 0.5 denials beats 0 by +0.0018, but with
   linked_badges at 10 the difference vanishes (−0.0001). Moving history, badge age or zone does not remove it.
   `linked_badges` is the hub of the interactions that make the top region differ from the Round 1 baseline.
3. **`recent_denials` has a context-dependent, jagged effect.** Near the top, 0.5 beats 0 (0.9966 vs 0.9948), and
   the curve zig-zags (1.0 .9940, 1.25 .9959, 1.5 .9926). At the Round 1 baseline, 0–1.25 was flat.
4. **`anomaly_ratio`, `clearance_level` and `escorts` are dropped.** Their opposite extremes leave the score
   unchanged at the high-score champion too. Together with Round 1 that makes four contexts, all sites, full ranges.
5. **The response is step-like, not smooth.** Small non-monotone zig-zags in several inputs (denials 1.0 < 1.25,
   zone 16 < 14 = 18, linked 17 < 16 < 18) are typical of a tree ensemble's piecewise-constant output. This is a
   hypothesis, not a proven fact (see below).

6. **Ratios between inputs: no pair acts as a pure ratio (tested directly).** With the 50 extra queries we tested
   ratios directly. If the score depends on a/b only, multiplying both inputs by the same factor leaves it unchanged.
   At the Round 1 midpoint baseline (0.8213), where every input has a large effect, we scaled each of the 15 pairs of
   active inputs by ×1.5 (q121–135). **All 15 moved the score**; for example `linked_badges/history_score` → 0.6305,
   which also rejects the offline scan's top candidate.
   - **`badge_age_days/linked_badges`:** matched at ×1.5 (0.8223), but the two separate effects simply cancel there.
     ×0.5 (0.7743) and ×1.25 (0.8111) reject it.
   - **`requested_zone/tenure_years`:** came closest (×0.5 .8194, ×0.75 .8088, ×1.5 .8121) but is not constant. It is
     kept only as a low-confidence (0.15) candidate.
   - **"Used alongside the raw inputs" versions:** we also tested `badge_age/linked` (the best badge age stays 23.5 at
     linked 15) and `denials/linked` (the denials bonus does not shift with linked). Both are rejected.
7. **The denials bonus is a step in `linked_badges`, at ≈15.** The gain from 0.5 denials over 0 is about 0 at
   linked 9–14, +0.0006 at 15, +0.0016 at 16, +0.0023 at 17 and +0.0018 at 18.
8. **The badge × linked interaction holds in a second region.** At the midpoint baseline, raising linked from 10 to
   18 shifts the badge-23-vs-18 comparison by +0.0037, near the top by +0.0036.

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
6. **Rounding test (q72–75).** linked_badges 18.4 ≠ 18 and 18.6 ≠ 19, so linked_badges is used unrounded. That test
   also found the next improvement (0.9970). tenure_years 22–22.6 is flat: rounding or a wide split cell, not resolved.
7. **What gates the denials benefit? (q97–104)** Same one-suspect-at-a-time design: only `linked_badges` removes it.
8. **Exploitation (q76–96, q105–120).** Combining the tied best cells gave **0.9972** (q83). Surrogate-picked and
   hand-picked combinations afterwards produced ten exact ties and nothing higher, so this is a plateau.
9. **Joint linked × badge probe (q56–61).** If high linked favours older badges, maybe linked 19–20 with badge 24–27
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
- **linked_badges rounded to an integer before the model.** 18.4 gives .9970 vs 18 .9968, and 18.6 gives .9958 vs 19 .9961.
- **badge_age/linked_badges acting only as a ratio.** Pairs with nearly the same ratio differ: (20, 25) .9906 vs (18, 23) .9968.
- **History, badge age or zone gating the denials benefit.** Only linked_badges removes it.
- **Any pair of inputs acting only as a ratio.** All 15 pairs fail the scale test (q121–139).
- **badge_age/linked or denials/linked as derived ratio features.** Their predicted optimum shifts do not happen
  (q143–148).
- **Low history_score (300–325) near the top.** 300 .9944, 315 .9953, 325 .9952 vs 349 .9972 (q149–152).
- **A better second region.** BB-009's 0.9922 point upgraded with our findings reaches only 0.9948 (q156–158).

## What we are still unsure about

- **Whether the model is a tree ensemble.** The zig-zags fit that, but a smooth model with many interactions could
  produce some of them. We have not found a clean split boundary in this round.
- **The exact form of the linked × badge interaction** (product, ratio, or a tree split on both). We tested two
  linked levels for the flip and four pairs jointly.
- **The global maximum.** The champion is a local optimum in every single input and in the joint moves we tried. A
  better region elsewhere cannot be excluded.
