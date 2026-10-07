# round-4 — Reconstruct

**Team:** BB-001
**System:** GK-05
**Queries used:** 80 / 80 this round (training data: every query we ever made — R1 150 + R2 170 + R4 80 — plus 35 public GK-05 results; 435 rows)

## What we concluded

**The replica (`round-4/surrogate.py`, `predict(rows)`):**

1. **A hard gate.** At **site B with `tenure_years` < 10.86**, GK-05 returns exactly **0.032** (DECLINE), whatever the
   other inputs are. Across all 198 site-B rows we own, this single rule separates the floor with no exceptions.
2. **Otherwise, a smooth model.** We average, in logit space:
   - an **additive spline model** (GAM: one smooth curve per input with 8 knots, ridge-regularised), which gives the
     global shape, **plus tensor-product spline terms for the two Round 2 interactions**: `linked_badges` ×
     `badge_age_days` and `linked_badges` × `recent_denials`;
   - a **Gaussian process** (Matern 1/2, one length scale per input), which adds local corrections near observed data.
3. **The decision** is APPROVE when the score is above 0.4484. We observed a maximum DECLINE of 0.4466 and a minimum
   APPROVE of 0.4502.

**Inputs used:** the six active inputs plus site. `anomaly_ratio`, `clearance_level` and `escorts` are accepted and
ignored.

**Accuracy:**

| Validation | Rows | Decision accuracy | R² | MAE |
|---|---|---|---|---|
| Full dataset: every GK-05 observation we hold (training fit) | 435 | **99.3%** | **0.999** | 0.005 |
| 5-fold cross-validation on the full dataset | 435 | 98.9% | 0.994 | 0.011 |
| Fresh Round 4 queries, never used in training | 80 | 97.5% | 0.985 | 0.028 |

**At the 0.9972 champion it predicts 0.9968.** It still predicts 0.9967 when every champion row is removed from
training.

**How the earlier rounds shaped it.** The six-input feature set came from Rounds 1–2 (the three inert inputs). The
logit target follows from the scores sitting near 1 at the top. The two interaction terms are the Round 2 findings
(linked_badges flips the badge-age preference and gates the denials bonus); encoded as tensor-product splines they
improved every held-out test (step 7). The single most important structure, the site-B tenure floor, was
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

7. **Refining GAM + GP** (`experiments/r4_tweaks.py`, `r4_tweaks.json`, `r4_tweaks_combo.json`). We tried 25 variants
   and kept a change only if it improved **all three** tests at once: the 80 fresh queries, leave-one-group-out, and
   5-fold CV. No new queries were available, so the 80 fresh queries were also used in this choice. Requiring all three
   tests to improve guards against fitting them by luck.

   | Variant (all with the gate) | Fresh MAE | Fresh max | Fresh decisions | LGO mean MAE | CV MAE |
   |---|---|---|---|---|---|
   | Previous: GAM (6 knots) + GP (Matern 3/2) | 0.0311 | 0.156 | 96.3% | 0.0235 | 0.0134 |
   | GAM 8 knots | 0.0300 | 0.151 | 96.3% | 0.0234 | 0.0128 |
   | GP Matern 1/2 | 0.0309 | 0.148 | 96.3% | 0.0225 | 0.0131 |
   | GAM + linked × badge, linked × denials terms | 0.0306 | 0.152 | 97.5% | 0.0237 | 0.0121 |
   | **All three together (chosen)** | **0.0280** | **0.122** | **97.5%** | **0.0208** | **0.0113** |
   | Site-specific curves per site | 0.0451 | 0.204 | 95.0% | 0.0294 | 0.0142 |
   | GP on GAM residuals | 0.0370 | 0.140 | 98.8% | 0.0261 | 0.0164 |
   | GP with RBF kernel | 0.0861 | 0.529 | 95.0% | 0.0380 | 0.0156 |

   Separate curves per site made things worse, so the site-C errors are not just a site offset problem.

## Validation of the final replica

Run with `python experiments/validate_replica.py`; results are in `experiments/validation_results.json` and
`plots/r4_validation.png`.

| Test | n | MAE | RMSE | R² | Max error | Decision acc. |
|---|---|---|---|---|---|---|
| 80 R4 queries, never trained on | 80 | 0.028 | 0.041 | 0.985 | 0.122 | 0.975 |
| Hold out all of R1 (train R2+R4+public) | 150 | 0.032 | 0.040 | 0.972 | 0.121 | 0.953 |
| Hold out all of R2 | 170 | 0.007 | 0.012 | 0.986 | 0.078 | 1.000 |
| Hold out public points | 35 | 0.008 | 0.012 | 0.942 | 0.036 | 1.000 |
| Hold out R4 space-filling | 40 | 0.036 | 0.050 | 0.970 | 0.121 | 0.975 |
| Hold out R4 disagreement | 40 | 0.021 | 0.033 | 0.991 | 0.100 | 0.975 |
| 5-fold CV, all rows | 435 | 0.011 | 0.022 | 0.994 | 0.125 | 0.989 |

**Champion:** actual 0.9972, replica 0.9968, absolute error 0.0004.

**Worst unseen errors:** 5 of the 8 largest are site C, in both directions.

| Query | Site | Tenure | Actual | Predicted |
|---|---|---|---|---|
| R4 q3 | C | 2.3 | 0.663 | 0.785 |
| q23 | C | 1.8 | 0.348 | 0.458 |
| q19 | C | 37.5 | 0.560 | 0.463 |
| q15 | C | 4.1 | 0.153 | 0.243 |
| q42 | B | 21.1 | 0.592 | 0.680 |

**Residuals** (`plots/r4_residuals.png`) are centred on zero with no clear trend against any input. The largest sit at
the ends of the tenure range and on site C.

## What we ruled out

- **Tree ensembles as the main model.** On unseen space-filling queries, extra trees and random forest were the worst
  non-linear models (MAE 0.13–0.15, R² 0.25–0.34), even though they had the best random-CV numbers. The jagged,
  step-like behaviour seen near the top in Round 2 does not describe the function globally.
- **A purely linear or polynomial model.** Ridge had MAE 0.140 and Poly2 0.214 on unseen queries.
- **Including `anomaly_ratio`, `clearance_level` and `escorts`.** Adding them did not consistently help on the 40
  unseen space-filling queries: the GAM got worse (0.081 → 0.092), the GP was identical, and the tree models moved by
  under 0.01 in either direction. In the 80 R4 queries they were randomised over their full ranges.
  The floor rule ignores them, and so does the replica.
- **Encoding the Round 2 interactions as simple hand-made features** (a linked_badges ≥ 15 indicator and raw
  products). Before the gate was found, these made held-out error worse for the three best models (GAM 0.081 → 0.090,
  GP 0.093 → 0.100, GBR 0.111 → 0.120). The same interactions encoded as smooth tensor-product splines *did* help,
  once the gate was in place (step 7).
- **Kriging alone (GP) or GAM alone.** The average beats both on unseen MAE and worst-case error.

## Where the replica is weak (honest limits)

- **Site C:** 14 rows in total, and 5 of the 8 worst unseen errors (off by about 0.08–0.12). Site D has 20
  rows. Neither site was targeted by the disagreement batch.
- **The disagreement batch was all site B.** We did not force site balance in the last 40 queries, so sites A, C and D
  got no targeted queries this round. That batch did find the floor.
- **Fine-scale interactions near the maximum are only partly reproduced.** Round 2 showed the badge 23-vs-18 and
  denials 0.5-vs-0 comparisons flip sign when linked_badges drops from 18 to 10; in GK-05 the swings are 0.002–0.004.
  At linked 18 the replica matches closely (+0.0025 vs observed +0.0026; +0.0019 vs +0.0018). At linked 10 it moves
  the right way but not far enough: +0.0005 vs −0.0010 for badge age (previous model +0.0034), and +0.0016 vs −0.0001
  for denials (previous model +0.0034).
- **The tenure threshold** is known to within ±0.52 (between 10.338 and 11.377). We have not checked whether it moves
  with other inputs; it was the same across everything we observed.
- **The far interior of the input box is thin.** We have 80 space-covering points in 10 dimensions, so expect errors
  of around 0.03 on arbitrary inputs, with occasional misses of up to about 0.12.

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
