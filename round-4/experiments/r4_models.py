"""Round 4: canonical GK-05 dataset, feature sets and candidate model zoo for the reconstruction."""
import json, warnings
import numpy as np
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel, WhiteKernel
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler, PolynomialFeatures
from sklearn.linear_model import RidgeCV
import xgboost as xgb
from bb import ROOT, FIELDS

warnings.filterwarnings("ignore")
NUM = list(FIELDS)
ACTIVE = ["badge_age_days", "history_score", "linked_badges", "recent_denials", "requested_zone", "tenure_years"]
INERT = ["anomaly_ratio", "clearance_level", "escorts"]
SITES = ["A", "B", "C", "D"]


def canonical():
    """Every trustworthy GK-05 observation, unrounded, with provenance:
    our server export (R1, R2), our Round 4 queries, and public results from teams confirmed to have GK-05."""
    rows, seen = [], set()

    def add(r, **meta):
        key = tuple(r[k] for k in NUM + ["site"])
        if key in seen and meta["origin"] == "public":
            return  # same input already observed by us (scores were checked to agree)
        seen.add(key)
        rows.append({**{k: float(r[k]) for k in NUM}, "site": r["site"], "score": float(r["score"]),
                     "decision": r.get("decision"), **meta})

    for r in json.load(open(ROOT / "data" / "export_r4_preflight.json", encoding="utf-8")):
        add(r, origin="own", round=r["round"], query_index=r["query_index"], source=f"{r['round']}-q{r['query_index']}")
    p = ROOT / "data" / "r4_obs.json"
    for r in (json.load(open(p, encoding="utf-8")) if p.exists() else []):
        add(r, origin="own", round="R4", query_index=r["query_index"], source=f"R4-q{r['query_index']}", tag=r["tag"])
    for r in json.load(open(ROOT / "data" / "external_obs.json", encoding="utf-8")):
        if r.get("system_confirmed"):
            add(r, origin="public", round="public", query_index=None, source=r["source"])
    return rows


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def sigm(z):
    return 1 / (1 + np.exp(-np.asarray(z, float)))


def feats(rows, kind="active"):
    """active: 6 active inputs (range-scaled) + site one-hot.  all: also the 3 apparently inert inputs.
    eng: active + earlier-round findings (linked_badges gate at ~15, linked x badge_age, linked x denials)."""
    cols = NUM if kind == "all" else ACTIVE
    X = np.array([[(r[k] - FIELDS[k][0]) / (FIELDS[k][1] - FIELDS[k][0]) for k in cols] for r in rows], float)
    S = np.array([[r["site"] == s for s in SITES] for r in rows], float)
    out = [X, S]
    if kind == "eng":
        L = np.array([r["linked_badges"] for r in rows], float)
        B = (np.array([r["badge_age_days"] for r in rows], float) - 18) / 57
        D = np.array([r["recent_denials"] for r in rows], float) / 5
        g = (L >= 15).astype(float)
        out.append(np.c_[g, g * B, g * D, L / 20 * B, L / 20 * D])
    return np.hstack(out)


def make(name, d):
    if name == "GP":
        return GaussianProcessRegressor(ConstantKernel() * Matern(length_scale=np.ones(d), nu=1.5) + WhiteKernel(1e-3),
                                        normalize_y=True, n_restarts_optimizer=1, random_state=0)
    return {
        "Ridge": lambda: make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 13))),
        "Poly2-Ridge": lambda: make_pipeline(StandardScaler(), PolynomialFeatures(2), RidgeCV(alphas=np.logspace(-3, 3, 13))),
        "Spline-GAM": lambda: make_pipeline(SplineTransformer(n_knots=6), RidgeCV(alphas=np.logspace(-3, 3, 13))),
        "kNN": lambda: KNeighborsRegressor(5, weights="distance"),
        "RF": lambda: RandomForestRegressor(500, n_jobs=-1, random_state=0),
        "ET": lambda: ExtraTreesRegressor(500, n_jobs=-1, random_state=0),
        "GBR": lambda: GradientBoostingRegressor(n_estimators=400, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=0),
        "HGB": lambda: HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, min_samples_leaf=3),
        "XGB": lambda: xgb.XGBRegressor(n_estimators=600, max_depth=4, learning_rate=0.04, subsample=0.8,
                                        colsample_bytree=0.8, n_jobs=20),
    }[name]()


MODELS = ["Ridge", "Poly2-Ridge", "Spline-GAM", "kNN", "RF", "ET", "GBR", "HGB", "XGB", "GP"]


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    e = y - p
    return dict(MAE=float(np.mean(np.abs(e))), RMSE=float(np.sqrt(np.mean(e ** 2))),
                R2=float(1 - np.sum(e ** 2) / np.sum((y - y.mean()) ** 2)), MaxErr=float(np.max(np.abs(e))),
                DecAcc=float(np.mean((y > 0.45) == (p > 0.45))))
