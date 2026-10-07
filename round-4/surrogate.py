"""BB-001 Round 4 reconstruction of GK-05.

    from surrogate import predict
    predict([{"badge_age_days": 23.5, "history_score": 349, "linked_badges": 18.4, "recent_denials": 0.5,
              "requested_zone": 18, "tenure_years": 22, "site": "B",
              "anomaly_ratio": 0, "clearance_level": 75, "escorts": 0}])
    -> [{"score": ..., "decision": "APPROVE"}]

Architecture (chosen by error on 80 GK-05 queries the model had not seen, see report.md):
  1. Gate: site B with tenure_years < 10.86 -> score 0.032 exactly (198/198 site-B rows separated, no exceptions).
  2. Otherwise: average, in logit space, of
       a. an additive spline model (GAM: cubic B-splines per input + ridge) - the smooth global shape, and
       b. a Gaussian process (Matern 3/2, one length scale per input) - the local interactions near observed data.
  3. decision = APPROVE if score > 0.4484 (observed: max DECLINE 0.4466, min APPROVE 0.4502).
Inputs used: the 6 active inputs + site. anomaly_ratio, clearance_level and escorts are accepted and ignored
(no effect in any test across four rounds of data, and including them never improved held-out error).

Requires numpy and scikit-learn. Trains on experiments/gk05_canonical.csv on first use (~20 s), then caches.
"""
import csv
from pathlib import Path
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel, WhiteKernel
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer

DATA = Path(__file__).parent / "experiments" / "gk05_canonical.csv"
RANGES = {"badge_age_days": (18, 75), "history_score": (300, 900), "linked_badges": (0, 20),
          "recent_denials": (0, 5), "requested_zone": (0, 100), "tenure_years": (0, 40)}
SITES = ["A", "B", "C", "D"]
FLOOR_SCORE, FLOOR_TENURE = 0.032, 10.858     # site-B gate; tenure threshold midway between 10.338 and 11.377
CUTOFF = 0.4484
_models = None


def _features(rows):
    X = np.array([[(float(r[k]) - lo) / (hi - lo) for k, (lo, hi) in RANGES.items()] for r in rows])
    S = np.array([[r["site"] == s for s in SITES] for r in rows], float)
    return np.hstack([X, S])


def _gated(rows):
    return np.array([r["site"] == "B" and float(r["tenure_years"]) < FLOOR_TENURE for r in rows])


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def fit(rows):
    """Fit the replica on observed GK-05 rows (dicts with the inputs and 'score')."""
    rows = [r for r, g in zip(rows, _gated(rows)) if not g]   # the gate explains the floor rows
    X, z = _features(rows), _logit([float(r["score"]) for r in rows])
    gam = make_pipeline(SplineTransformer(n_knots=6), RidgeCV(alphas=np.logspace(-3, 3, 13))).fit(X, z)
    gp = GaussianProcessRegressor(ConstantKernel() * Matern(length_scale=np.ones(X.shape[1]), nu=1.5) + WhiteKernel(1e-3),
                                  normalize_y=True, n_restarts_optimizer=1, random_state=0).fit(X, z)
    return gam, gp


def _load():
    global _models
    if _models is None:
        with open(DATA, encoding="utf-8") as f:
            _models = fit(list(csv.DictReader(f)))
    return _models


def predict_scores(rows, models=None):
    gam, gp = models or _load()
    X = _features(rows)
    z = (gam.predict(X) + gp.predict(X)) / 2
    return np.where(_gated(rows), FLOOR_SCORE, 1 / (1 + np.exp(-z)))


def predict(rows):
    """rows: list of dicts with the GK-05 inputs. Returns [{'score': float, 'decision': 'APPROVE'|'DECLINE'}]."""
    s = predict_scores(rows)
    return [{"score": round(float(v), 4), "decision": "APPROVE" if v > CUTOFF else "DECLINE"} for v in s]


if __name__ == "__main__":
    import json, sys
    demo = [{"badge_age_days": 23.5, "history_score": 349, "linked_badges": 18.4, "recent_denials": 0.5, "requested_zone": 18,
             "tenure_years": 22, "site": "B", "anomaly_ratio": 0, "clearance_level": 75, "escorts": 0},
            {"badge_age_days": 46.5, "history_score": 600, "linked_badges": 10, "recent_denials": 2.5, "requested_zone": 50,
             "tenure_years": 20, "site": "A", "anomaly_ratio": 0.5, "clearance_level": 50, "escorts": 3},
            {"badge_age_days": 46.5, "history_score": 600, "linked_badges": 10, "recent_denials": 2.5, "requested_zone": 50,
             "tenure_years": 5, "site": "B", "anomaly_ratio": 0.5, "clearance_level": 50, "escorts": 3}]
    rows = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else demo
    for r, p in zip(rows, predict(rows)):
        print(p, "<-", {k: r[k] for k in list(RANGES) + ["site"]})
