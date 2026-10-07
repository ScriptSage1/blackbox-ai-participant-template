"""BB-001 Round 4 reconstruction of GK-05.

    from surrogate import predict
    predict([{"badge_age_days": 23.5, "history_score": 349, "linked_badges": 18.4, "recent_denials": 0.5,
              "requested_zone": 18, "tenure_years": 22, "site": "B",
              "anomaly_ratio": 0, "clearance_level": 75, "escorts": 0}])
    -> [{"score": ..., "decision": "APPROVE"}]

Architecture (chosen by error on 80 GK-05 queries the model had not seen, leave-one-group-out and 5-fold CV;
see report.md):
  1. Gate: site B with tenure_years < 10.86 -> score 0.032 exactly (198/198 site-B rows separated, no exceptions).
  2. Otherwise: average, in logit space, of
       a. an additive spline model (GAM: cubic B-splines with 8 knots per input, ridge-regularised) PLUS tensor-product
          terms for the two interactions found in Round 2: linked_badges x badge_age_days and
          linked_badges x recent_denials, and
       b. a Gaussian process (Matern 1/2, one length scale per input) - local corrections near observed data.
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
from sklearn.preprocessing import SplineTransformer

DATA = Path(__file__).parent / "experiments" / "gk05_canonical.csv"
RANGES = {"badge_age_days": (18, 75), "history_score": (300, 900), "linked_badges": (0, 20),
          "recent_denials": (0, 5), "requested_zone": (0, 100), "tenure_years": (0, 40)}
SITES = ["A", "B", "C", "D"]
FLOOR_SCORE, FLOOR_TENURE = 0.032, 10.858     # site-B gate; tenure threshold midway between 10.338 and 11.377
CUTOFF = 0.4484
KNOTS = 8
PAIRS = [("linked_badges", "badge_age_days"), ("linked_badges", "recent_denials")]   # Round 2 interactions
_models = None


def _num(rows):
    return np.array([[(float(r[k]) - lo) / (hi - lo) for k, (lo, hi) in RANGES.items()] for r in rows])


def _site(rows):
    return np.array([[r["site"] == s for s in SITES] for r in rows], float)


def _gated(rows):
    return np.array([r["site"] == "B" and float(r["tenure_years"]) < FLOOR_TENURE for r in rows])


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


class _GAM:
    """Per-input cubic splines + site offsets + tensor-product splines for the Round 2 interaction pairs."""

    def _design(self, rows):
        Xn = _num(rows)
        B = self.st.transform(Xn)
        per = B.shape[1] // Xn.shape[1]
        block = {k: B[:, i * per:(i + 1) * per] for i, k in enumerate(RANGES)}
        cols = [B, _site(rows)]
        for a, b in PAIRS:
            cols.append(np.einsum("ni,nj->nij", block[a], block[b]).reshape(len(rows), -1))
        return np.hstack(cols)

    def fit(self, rows, z):
        self.st = SplineTransformer(n_knots=KNOTS, degree=3).fit(_num(rows))
        self.ridge = RidgeCV(alphas=np.logspace(-4, 4, 17)).fit(self._design(rows), z)
        return self

    def predict(self, rows):
        return self.ridge.predict(self._design(rows))


def fit(rows):
    """Fit the replica on observed GK-05 rows (dicts with the inputs and 'score')."""
    rows = [r for r, g in zip(rows, _gated(rows)) if not g]   # the gate explains the floor rows
    z = _logit([float(r["score"]) for r in rows])
    gam = _GAM().fit(rows, z)
    X = np.hstack([_num(rows), _site(rows)])
    gp = GaussianProcessRegressor(ConstantKernel() * Matern(length_scale=np.ones(X.shape[1]), nu=0.5) + WhiteKernel(1e-3),
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
    z = (gam.predict(rows) + gp.predict(np.hstack([_num(rows), _site(rows)]))) / 2
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
