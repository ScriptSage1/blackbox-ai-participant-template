# round-4 — Reconstruct

**Team:** BB-001
**System:** GK-05
**Queries used:** 80 / 80 this round (training data: every query we ever made — R1 150 + R2 170 + R4 80 — plus 35 public GK-05 results; 435 rows)

## What we concluded

**The replica (`round-4/surrogate.py`, `predict(rows)`):**

1. **A hard gate.** At **site B with `tenure_years` < 10.86**, GK-05 returns exactly **0.032** (DECLINE), whatever the
   other inputs are. Across all 198 site-B rows we own, this single rule separates the floor with no exceptions.
2. **Otherwise, a smooth model.** We average, in logit space:
   - an **additive spline model** (GAM: one smooth curve per input, ridge-regularised), which gives the global shape;
   - a **Gaussian process** (Matern 3/2, one length scale per input), which captures interactions near observed data.
3. **The decision** is APPROVE when the score is above 0.4484. We observed a maximum DECLINE of 0.4466 and a minimum
   APPROVE of 0.4502.

**Inputs used:** the six active inputs plus site. `anomaly_ratio`, `clearance_level` and `escorts` are accepted and
ignored.

**On 80 GK-05 queries it was never trained on:** MAE **0.031**, RMSE 0.049, R² **0.978**, max error 0.156, decision
accuracy 96%.

**At the 0.9972 champion it predicts 0.9967.** It still predicts 0.9966 when every champion row is removed from
training.

**How the earlier rounds shaped it.** The six-input feature set came from Rounds 1–2 (the three inert inputs). The
logit target follows from the scores sitting near 1 at the top. Note that the Round 2 interaction features did *not*
improve held-out error (see "What we ruled out"). The single most important structure, the site-B tenure floor, was
invisible to every earlier round. We had only ever queried site B with tenure 22.

## How we got there

1. **Pre-flight (no queries).** The 320 R1+R2 rows were clustered:
   - 146 lay close to just two points, the R1 midpoint baseline and the R2 champion;
   - a random input sat a median 0.47 (range-normalised) from its nearest observed row;
   - sites C and D had 4 and 10 rows.

   Random 5-fold CV on that data said MAE ≈ 0.01 for every model, which we did not trust.

2. **Data quality.** All four exact-repeat inputs returned identical scores, so GK-05 is deterministic. Of the public
   GK-05 points, 3 duplicate inputs we had already observed, and the scores agree exactly. Values are kept unrounded
   (for example linked 18.4).

3. **Queries 1–40: space-filling.** A Latin hypercube over all 9 numeric inputs, with sites balanced 10 each and the
   "inert" inputs randomised too. These double as an **out-of-distribution test set**: every model was scored on them
   *before* training on them.

   | Model (trained on R1+R2+public) | MAE on the 40 unseen | R² | random-CV MAE |
   |---|---|---|---|
   | Spline-GAM | **0.081** | 0.67 | 0.014 |
   | Gaussian process | 0.093 | 0.55 | 0.008 |
   | Gradient boosting | 0.111 | 0.52 | 0.011 |
   | XGBoost | 0.115 | 0.47 | 0.010 |
   | Random forest | 0.129 | 0.33 | 0.013 |
   | Extra trees | 0.146 | 0.25 | 0.009 |
   | Ridge (linear) | 0.140 | 0.20 | 0.027 |

   The random-CV error understated the true error about tenfold. Smooth models generalised best, and tree ensembles
   worst. The three biggest misses were all site B at exactly 0.032.

4. **Queries 41–80: model disagreement.** Five candidate replicas (GAM, GP, GBR, XGB, RF), trained on everything so
   far, scored 16,384 Sobol candidates. We took the 40 with the largest spread of predictions, each at least 0.15 from
   any observed row and at least 0.30 from each other.
   - All 40 fell on site B, because that is where the models disagreed most.
   - Before seeing them, the models' MAE on this batch was 0.24–0.38.
   - 16 returned exactly 0.032.

5. **The floor rule.** A depth-1 decision tree on the 198 site-B rows splits on `tenure_years` at 10.86 with 100%
   accuracy: floor at 0.054–10.338 and normal at 11.377–38.97. No other input separates them. Sites A, C and D never
   return 0.032; their minimum scores are 0.045, 0.153 and 0.053.

6. **Model selection with the gate** (`experiments/r4_model_selection.json`). The table shows all 80 R4 queries held
   out, leave-one-group-out, and 5-fold CV on all 435 rows.

   | Model (+ gate) | R4-unseen MAE | RMSE | R² | max err | LGO MAE (R1 / R2 / public / R4a / R4b) | CV MAE | CV max |
   |---|---|---|---|---|---|---|---|
   | **GAM + GP (chosen)** | **0.031** | 0.049 | **0.978** | 0.156 | .039 / .006 / .009 / .037 / .027 | 0.013 | **0.146** |
   | GAM + XGB residual | 0.035 | 0.049 | 0.978 | 0.123 | .044 / .006 / .013 / .033 / .028 | 0.012 | 0.167 |
   | GP | 0.035 | 0.062 | 0.965 | 0.255 | .050 / .006 / .013 / .045 / .024 | 0.013 | 0.244 |
   | Spline-GAM | 0.037 | 0.053 | 0.975 | 0.140 | .063 / .009 / .006 / .041 / .038 | 0.018 | 0.191 |
   | GAM + GBR + GP | 0.037 | 0.053 | 0.974 | 0.154 | .036 / .006 / .013 / .040 / .031 | 0.013 | 0.177 |
   | GBR | 0.058 | 0.086 | 0.934 | 0.259 | .043 / .009 / .019 / .057 / .054 | 0.018 | 0.271 |
   | XGB | 0.062 | 0.096 | 0.917 | 0.311 | .063 / .007 / .016 / .057 / .048 | 0.017 | 0.305 |

   GAM + GP has the lowest error on unseen queries and the lowest worst-case CV error. It is the best or within 0.005
   of the best on every held-out group. We preferred it to the near-tie GAM + XGB because it is two smooth models
   rather than a boosted correction, consistent with step 3.

## Validation of the final replica

Run with `python experiments/validate_replica.py`; results are in `experiments/validation_results.json` and
`plots/r4_validation.png`.

| Test | n | MAE | RMSE | R² | Max error | Decision acc. |
|---|---|---|---|---|---|---|
| 80 R4 queries, never trained on | 80 | 0.031 | 0.049 | 0.978 | 0.156 | 0.96 |
| Hold out all of R1 (train R2+R4+public) | 150 | 0.039 | 0.049 | 0.958 | 0.172 | 0.98 |
| Hold out all of R2 | 170 | 0.006 | 0.013 | 0.984 | 0.088 | 0.99 |
| Hold out public points | 35 | 0.009 | 0.013 | 0.928 | 0.047 | 1.00 |
| Hold out R4 space-filling | 40 | 0.037 | 0.056 | 0.963 | 0.153 | 0.95 |
| Hold out R4 disagreement | 40 | 0.027 | 0.040 | 0.987 | 0.121 | 0.95 |
| 5-fold CV, all rows | 435 | 0.013 | 0.025 | 0.991 | 0.146 | 0.98 |

**Champion:** actual 0.9972, replica 0.9967, absolute error 0.0005.

**Worst unseen errors:** these are all over-predictions, and 4 of the 8 largest are site C.

| Query | Site | Tenure | Actual | Predicted |
|---|---|---|---|---|
| R4 q3 | C | 2.3 | 0.663 | 0.819 |
| q29 | A | 39.1 | 0.618 | 0.765 |
| q15 | C | 4.1 | 0.153 | 0.292 |
| q27 | C | 22.3 | 0.413 | 0.549 |
| q23 | C | 1.8 | 0.348 | 0.474 |

**Residuals** (`plots/r4_residuals.png`) are centred on zero with no clear trend against any input. The largest are
over-predictions (residual −0.10 to −0.15), concentrated at tenure 0–3 and 37–40, the ends of the tenure range.

## What we ruled out

- **Tree ensembles as the main model.** On unseen space-filling queries, extra trees and random forest were the worst
  non-linear models (MAE 0.13–0.15, R² 0.25–0.34), even though they had the best random-CV numbers. The jagged,
  step-like behaviour seen near the top in Round 2 does not describe the function globally.
- **A purely linear or polynomial model.** Ridge had MAE 0.140 and Poly2 0.214 on unseen queries.
- **Including `anomaly_ratio`, `clearance_level` and `escorts`.** Adding them did not consistently help on the 40
  unseen space-filling queries: the GAM got worse (0.081 → 0.092), the GP was identical, and the tree models moved by
  under 0.01 in either direction. In the 80 R4 queries they were randomised over their full ranges.
  The floor rule ignores them, and so does the replica.
- **Encoding the Round 2 interactions as features** (a linked_badges ≥ 15 gate, linked × badge, linked × denials).
  This made held-out error worse for the three best models (GAM 0.081 → 0.090, GP 0.093 → 0.100, GBR 0.111 → 0.120)
  and was mixed for the others. Those effects are
  about 0.002–0.003 in size and only exist in the high-score region.
- **Kriging alone (GP) or GAM alone.** The average beats both on unseen MAE and worst-case error.

## Where the replica is weak (honest limits)

- **Site C:** 14 rows in total, and 4 of the 8 worst unseen errors (over-predicting by about 0.13–0.16). Site D has 20
  rows. Neither site was targeted by the disagreement batch.
- **The disagreement batch was all site B.** We did not force site balance in the last 40 queries, so sites A, C and D
  got no targeted queries this round. That batch did find the floor.
- **Fine-scale interactions near the maximum are not reproduced.** Round 2 showed the badge 23-vs-18 and
  denials 0.5-vs-0 comparisons flip sign when linked_badges drops from 18 to 10. In GK-05 the swings are 0.002–0.004.
  The replica gets the direction right at linked 18 (+0.0023 vs observed +0.0026; +0.0021 vs +0.0018). At linked 10 it
  predicts +0.0034 for both, where GK-05 gives −0.0010 and −0.0001. These effects are 10× smaller than the replica's
  typical error.
- **The tenure threshold** is known to within ±0.52 (between 10.338 and 11.377). We have not checked whether it moves
  with other inputs; it was the same across everything we observed.
- **The far interior of the input box is thin.** We have 80 space-covering points in 10 dimensions, so expect errors
  of around 0.03–0.05 on arbitrary inputs, with occasional misses of up to about 0.15.

## Reproduce

```bash
cd round-4
python surrogate.py                      # demo: champion, R1 baseline, a site-B floor row
python experiments/validate_replica.py   # full validation suite + plots
```

`surrogate.predict(rows)` takes a list of dicts with the GK-05 inputs and returns `[{"score", "decision"}]`. It needs
numpy and scikit-learn, and it fits itself from `experiments/gk05_canonical.csv` on first call (about 20 s).

**Experiments folder contents:**
- `export_all_queries.json`: `bb.export()`, all 400 of our queries.
- `gk05_canonical.csv`: the training set with provenance.
- `r4_obs.json`: every R4 query with the reason it was chosen.
- Selection results and scripts.
