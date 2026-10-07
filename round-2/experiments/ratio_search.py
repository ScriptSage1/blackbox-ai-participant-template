"""Offline search for derived features (ratios etc.) in GK-05 using all observed queries. Spends no queries.

1. Exact-pair test: query pairs where exactly two inputs differ and their ratio is (nearly) unchanged.
2. Model test: repeated-CV error of ExtraTrees / HistGB on logit(score) with base features vs base + one engineered
   feature (ratio / product / difference of a pair). Big, consistent CV gains point to a derived feature.
"""
import json, itertools, warnings
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import KFold
from bb import ROOT

warnings.filterwarnings("ignore")
ACTIVE = ["history_score", "linked_badges", "badge_age_days", "recent_denials", "requested_zone", "tenure_years"]
SITES = ["A", "B", "C", "D"]

rows = json.load(open(ROOT / "data" / "export_r1.json")) + json.load(open(ROOT / "data" / "export_r2.json"))
ext = [o for o in json.load(open(ROOT / "data" / "external_obs.json")) if o.get("system_confirmed")]
y = np.array([r["score"] for r in rows])
EPS = {"history_score": 1, "linked_badges": 0.5, "badge_age_days": 1, "recent_denials": 0.5, "requested_zone": 1, "tenure_years": 0.5}


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def base(R):
    X = np.array([[r[k] for k in ACTIVE] for r in R], float)
    S = np.array([[r["site"] == s for s in SITES] for r in R], float)
    return np.hstack([X, S])


def eng(R, a, b, kind):
    xa = np.array([r[a] for r in R], float)
    xb = np.array([r[b] for r in R], float)
    if kind == "ratio":
        return (xa + EPS[a] * 0) / (xb + EPS[b])
    if kind == "product":
        return xa * xb
    return xa - xb  # difference (raw units; trees are scale-invariant per feature)


def cv(X, t, model, reps=3):
    errs = []
    for rep in range(reps):
        pred = np.zeros_like(t)
        for tr, te in KFold(5, shuffle=True, random_state=rep).split(X):
            m = model().fit(X[tr], t[tr])
            pred[te] = m.predict(X[te])
        p = 1 / (1 + np.exp(-pred))
        errs.append(np.mean(np.abs(p - y)))
    return np.mean(errs)


ET = lambda: ExtraTreesRegressor(400, n_jobs=-1, random_state=0)
HGB = lambda: HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, min_samples_leaf=3)

if __name__ == "__main__":
    # ---- 1. exact pairs
    print("== exact-pair test (only two inputs differ, ratio within 1%) ==")
    n = 0
    for i, j in itertools.combinations(range(len(rows)), 2):
        a, b = rows[i], rows[j]
        diff = [k for k in ACTIVE + ["site", "anomaly_ratio", "clearance_level", "escorts"] if a[k] != b[k]]
        diff = [k for k in diff if k in ACTIVE]
        others_same = all(a[k] == b[k] for k in ACTIVE + ["site"] if k not in diff)
        if len(diff) == 2 and others_same:
            k1, k2 = diff
            if a[k2] and b[k2] and abs(a[k1] / a[k2] - b[k1] / b[k2]) <= 0.01 * abs(a[k1] / a[k2]):
                n += 1
                print(f"  {k1}/{k2}: {a[k1]}/{a[k2]} -> {a['score']}  vs  {b[k1]}/{b[k2]} -> {b['score']}")
    print(f"  {n} ratio-preserving pairs found")

    # ---- 2. model test
    t = logit(y)
    X0 = base(rows)
    b_et, b_hgb = cv(X0, t, ET), cv(X0, t, HGB)
    print(f"\n== model test: CV MAE base  ET {b_et:.5f}  HGB {b_hgb:.5f}  (n={len(rows)}) ==")
    res = []
    for a, b in itertools.permutations(ACTIVE, 2):
        for kind in ("ratio",) + (("product", "difference") if a < b else ()):
            Xf = np.hstack([X0, eng(rows, a, b, kind)[:, None]])
            e1, e2 = cv(Xf, t, ET), cv(Xf, t, HGB)
            res.append(((e1 - b_et) / b_et + (e2 - b_hgb) / b_hgb) / 2 * 100)
            res[-1] = (res[-1], kind, a, b, e1, e2)
    res.sort()
    print("  top 12 (negative % = CV error reduced):")
    for d, kind, a, b, e1, e2 in res[:12]:
        sym = {"ratio": "/", "product": "*", "difference": "-"}[kind]
        print(f"   {d:+6.1f}%  {a}{sym}{b:16s}  ET {e1:.5f}  HGB {e2:.5f}")
    print("  worst 3:", [(round(d, 1), k, a, b) for d, k, a, b, *_ in res[-3:]])
    json.dump([dict(change_pct=d, kind=k, a=a, b=b, et=e1, hgb=e2) for d, k, a, b, e1, e2 in res],
              open(ROOT / "data" / "ratio_search.json", "w"), indent=1)
