"""Round 2 surrogate optimizer (offline; spends no queries).

Usage:  python code/r2_opt.py [--top 15] [--no-export] [--n 200000]
- loads every observed query (R1 export + any R2 rows from the free export endpoint),
- fits several surrogates, reports k-fold CV error (overall and on the high-score region),
- generates many candidates offline (local perturbations of the champion + global samples),
- ranks them by ensemble mean with a disagreement penalty / bonus, prints the top-N.
"""
import argparse, json, time, warnings
warnings.filterwarnings("ignore")
import numpy as np
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
from sklearn.model_selection import KFold
import xgboost as xgb
from bb import FIELDS, SITES, ROOT

NUM = list(FIELDS)
ALL_EXT = False  # set by --external-all: also use teams whose system is not confirmed to be GK-05
LO = np.array([FIELDS[k][0] for k in NUM], float)
HI = np.array([FIELDS[k][1] for k in NUM], float)


def load(use_export=True):
    rows = json.load(open(ROOT / "data" / "export_r1.json"))
    if use_export:
        try:
            from bb import client
            rows = client().export()
            json.dump(rows, open(ROOT / "data" / "export_latest.json", "w"), indent=1)
        except Exception as e:  # offline / not signed in: fall back to the saved R1 export
            print("export unavailable, using saved R1 data:", e)
    return rows


def load_external():
    """Other teams' published GK-05 observations (data/external_obs.json) -- tagged, not our own queries."""
    p = ROOT / "data" / "external_obs.json"
    obs = json.load(open(p)) if p.exists() else []
    return obs if ALL_EXT else [o for o in obs if o.get("system_confirmed")]


def featurize(rows_or_X):
    """dict rows -> matrix [9 numeric scaled to 0..1, 4 site one-hot]."""
    if isinstance(rows_or_X, np.ndarray):
        return rows_or_X
    X = np.array([[r[k] for k in NUM] for r in rows_or_X], float)
    S = np.array([[r["site"] == s for s in SITES] for r in rows_or_X], float)
    return np.hstack([(X - LO) / (HI - LO), S])


def to_row(z):
    r = {k: float(round(LO[i] + z[i] * (HI[i] - LO[i]), 4)) for i, k in enumerate(NUM)}
    r["site"] = SITES[int(np.argmax(z[9:13]))]
    return r


def models():
    return {
        "RF": RandomForestRegressor(500, min_samples_leaf=1, n_jobs=-1, random_state=0),
        "ET": ExtraTreesRegressor(800, min_samples_leaf=1, n_jobs=-1, random_state=0),
        "HGB": HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, min_samples_leaf=3),
        "XGB": xgb.XGBRegressor(n_estimators=600, learning_rate=0.03, max_depth=4, subsample=0.9,
                                colsample_bytree=0.9, device="cuda", tree_method="hist"),
        "GP": GaussianProcessRegressor(ConstantKernel() * Matern(length_scale=np.full(13, 0.5), nu=2.5)
                                       + WhiteKernel(1e-5), normalize_y=True, n_restarts_optimizer=2),
    }


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def sig(z):
    return 1 / (1 + np.exp(-z))


def cv(X, y, k=5):
    out = {}
    for name in models():
        pred = np.zeros_like(y)
        for tr, te in KFold(k, shuffle=True, random_state=1).split(X):
            m = models()[name].fit(X[tr], logit(y[tr]))
            pred[te] = sig(m.predict(X[te]))
        hi = y > 0.9
        out[name] = (np.mean(np.abs(pred - y)), np.mean(np.abs(pred[hi] - y[hi])) if hi.any() else np.nan)
    return out


def candidates(champ, n, rng, local_only=False, sds=(0.03, 0.07, 0.15)):
    z0 = featurize([champ])[0]
    out = []
    if local_only:
        Z = np.repeat(z0[None], n, 0)
        for i in range(n):
            dims = rng.choice(9, rng.integers(2, 5), replace=False)
            Z[i, dims] += rng.normal(0, rng.choice(sds), len(dims))
        Z[:, :9] = np.clip(Z[:, :9], 0, 1)
        return Z
    # 60% local: perturb 1-4 numeric dims around the champion (scaled sd 0.03-0.15), keep or flip site
    nl = int(n * 0.6)
    Z = np.repeat(z0[None], nl, 0)
    for i in range(nl):
        dims = rng.choice(9, rng.integers(1, 5), replace=False)
        Z[i, dims] += rng.normal(0, rng.choice([0.03, 0.07, 0.15]), len(dims))
        if rng.random() < 0.1:
            Z[i, 9:13] = np.eye(4)[rng.integers(4)]
    out.append(Z)
    # 40% global: uniform in the box, random site
    ng = n - nl
    G = np.hstack([rng.random((ng, 9)), np.eye(4)[rng.integers(0, 4, ng)]])
    out.append(G)
    Z = np.vstack(out)
    Z[:, :9] = np.clip(Z[:, :9], 0, 1)
    return Z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--n", type=int, default=200_000)
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--external", action="store_true", help="also train on confirmed-GK-05 points in data/external_obs.json")
    ap.add_argument("--external-all", action="store_true", help="include unconfirmed teams too (only after verifying)")
    ap.add_argument("--local", action="store_true", help="only small multi-input moves around the champion")
    ap.add_argument("--mindist", type=float, default=0.0, help="min scaled distance between chosen candidates")
    ap.add_argument("--kappa", type=float, default=0.0, help="score = mean + kappa*std (UCB); <0 = conservative")
    a = ap.parse_args()
    t0 = time.time()
    rows = load(not a.no_export)
    global ALL_EXT
    ALL_EXT = a.external_all
    if a.external or a.external_all:
        ext = load_external()
        print(f"+ {len(ext)} external observations (other teams' published GK-05 queries)")
        rows = rows + ext
    X, y = featurize(rows), np.array([r["score"] for r in rows])
    best = max(rows, key=lambda r: r["score"])
    champ = {k: best[k] for k in NUM + ["site"]}
    print(f"{len(rows)} observations | champion {best['score']} (query {best.get('query_index')}, "
          f"round {best.get('round')}, source {best.get('source', 'ours')})")
    print("CV mean-abs-error (all / score>0.9):")
    for k, (e1, e2) in cv(X, y).items():
        print(f"  {k:4s} {e1:.4f} / {e2:.4f}")
    Z = candidates(champ, a.n, np.random.default_rng(int(t0)), local_only=a.local, sds=(0.005, 0.01, 0.02, 0.04))
    if a.local:
        print("local-only candidates (2-4 inputs moved, small steps, site kept)")
    preds = {}
    for name, m in models().items():
        if name == "GP" and len(y) > 600:
            continue
        m.fit(X, logit(y))
        preds[name] = sig(m.predict(Z))
    P = np.vstack(list(preds.values()))
    mu, sd = P.mean(0), P.std(0)
    acq = mu + a.kappa * sd
    order = []
    for i in np.argsort(-acq):  # greedy: skip candidates within min-dist of an already chosen one (scaled space)
        if all(np.linalg.norm(Z[i] - Z[j]) > a.mindist for j in order):
            order.append(i)
        if len(order) == a.top:
            break
    print(f"\n{a.n} candidates scored in {time.time() - t0:.1f}s. Top {a.top} (kappa={a.kappa}):")
    for i in order:
        r = to_row(Z[i])
        d = {k: v for k, v in r.items() if v != champ[k]}
        print(f"  mean {mu[i]:.4f} sd {sd[i]:.4f} | " + " ".join(f"{n}={preds[n][i]:.4f}" for n in preds) + f" | vs champ: {d}")
    json.dump([to_row(Z[i]) for i in order], open(ROOT / "data" / "r2_candidates.json", "w"), indent=1)


if __name__ == "__main__":
    main()
