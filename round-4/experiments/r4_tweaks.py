"""Round 4 tweak search: variants of the gate + GAM/GP replica, each scored on three tests at once:
fresh-80 (train R1+R2+public, predict all R4), leave-one-group-out (5 groups), 5-fold CV on all 435 rows."""
import json, sys, time, warnings
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, RBF, ConstantKernel, WhiteKernel
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold
from sklearn.preprocessing import SplineTransformer

warnings.filterwarnings("ignore")
ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
RANGES = {"badge_age_days": (18, 75), "history_score": (300, 900), "linked_badges": (0, 20),
          "recent_denials": (0, 5), "requested_zone": (0, 100), "tenure_years": (0, 40)}
SITES = ["A", "B", "C", "D"]
FLOOR_T, CUT = 10.858, 0.4484
df = pd.read_csv(ROOT / "template" / "round-4" / "experiments" / "gk05_canonical.csv")


def num(d):
    return np.column_stack([(d[k].to_numpy(float) - lo) / (hi - lo) for k, (lo, hi) in RANGES.items()])


def site(d):
    return np.column_stack([(d["site"] == s).to_numpy(float) for s in SITES])


def gated(d):
    return ((d["site"] == "B") & (d["tenure_years"] < FLOOR_T)).to_numpy()


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


class GAM:
    def __init__(self, knots=6, degree=3, site_inter=False, pairs=False):
        self.knots, self.degree, self.site_inter, self.pairs = knots, degree, site_inter, pairs

    def design(self, d):
        Xn, S = num(d), site(d)
        B = self.st.transform(Xn)
        cols = [B, S]
        if self.site_inter:
            cols += [B * S[:, [j]] for j in range(S.shape[1])]
        if self.pairs:  # tensor products: linked x badge, linked x denials
            per = B.shape[1] // Xn.shape[1]
            blk = lambda i: B[:, i * per:(i + 1) * per]
            L, Bd, D = blk(2), blk(0), blk(3)
            cols += [np.einsum("ni,nj->nij", L, Bd).reshape(len(d), -1), np.einsum("ni,nj->nij", L, D).reshape(len(d), -1)]
        return np.hstack(cols)

    def fit(self, d, z):
        self.st = SplineTransformer(n_knots=self.knots, degree=self.degree).fit(num(d))
        self.r = RidgeCV(alphas=np.logspace(-4, 4, 17)).fit(self.design(d), z)
        return self

    def predict(self, d):
        return self.r.predict(self.design(d))


def gp(nu, restarts=1):
    k = RBF(np.ones(10)) if nu == "rbf" else Matern(length_scale=np.ones(10), nu=nu)
    return GaussianProcessRegressor(ConstantKernel() * k + WhiteKernel(1e-3), normalize_y=True,
                                    n_restarts_optimizer=restarts, random_state=0)


def gpX(d):
    return np.hstack([num(d), site(d)])


def fit(cfg, d):
    d = d[~gated(d)]
    z = logit(d["score"])
    g = GAM(cfg.get("knots", 6), cfg.get("degree", 3), cfg.get("site_inter", False), cfg.get("pairs", False)).fit(d, z)
    mode = cfg.get("mode", "avg")
    if mode == "gam":
        return (cfg, g, None)
    if mode == "resid":
        p = gp(cfg.get("nu", 1.5), cfg.get("restarts", 1)).fit(gpX(d), z - g.predict(d))
    else:
        p = gp(cfg.get("nu", 1.5), cfg.get("restarts", 1)).fit(gpX(d), z)
    return (cfg, g, p)


def predict(m, d):
    cfg, g, p = m
    mode, w = cfg.get("mode", "avg"), cfg.get("w", 0.5)
    if mode == "gam":
        z = g.predict(d)
    elif mode == "resid":
        z = g.predict(d) + p.predict(gpX(d))
    else:
        z = w * g.predict(d) + (1 - w) * p.predict(gpX(d))
    return np.where(gated(d), 0.032, 1 / (1 + np.exp(-z)))


def met(y, p):
    e = y - p
    return dict(MAE=float(np.mean(abs(e))), RMSE=float(np.sqrt(np.mean(e ** 2))), Max=float(np.max(abs(e))),
                Acc=float(np.mean((y > CUT) == (p > CUT))))


def evaluate(name, cfg):
    t0 = time.time()
    y = df["score"].to_numpy()
    r4 = (df["round"] == "R4").to_numpy()
    fresh = met(y[r4], predict(fit(cfg, df[~r4]), df[r4]))
    groups = [df["round"] == "R1", df["round"] == "R2", df["round"] == "public", df["tag"] == "R4_B1_lhs", df["tag"] == "R4_B2_disagree"]
    lgo = [met(y[m.to_numpy()], predict(fit(cfg, df[~m]), df[m]))["MAE"] for m in groups]
    cv = np.zeros(len(df))
    for tr, te in KFold(5, shuffle=True, random_state=0).split(df):
        cv[te] = predict(fit(cfg, df.iloc[tr]), df.iloc[te])
    c = met(y, cv)
    return dict(name=name, fresh_MAE=fresh["MAE"], fresh_RMSE=fresh["RMSE"], fresh_max=fresh["Max"], fresh_acc=fresh["Acc"],
                lgo_mean=float(np.mean(lgo)), lgo=[round(v, 4) for v in lgo], cv_MAE=c["MAE"], cv_max=c["Max"], cv_acc=c["Acc"],
                secs=round(time.time() - t0, 1), cfg=cfg)


CANDS = {
    "current (GAM6 + GP m1.5, avg)": {},
    "GAM knots 4": {"knots": 4}, "GAM knots 8": {"knots": 8}, "GAM knots 10": {"knots": 10},
    "GAM degree 2": {"degree": 2},
    "GP Matern 2.5": {"nu": 2.5}, "GP RBF": {"nu": "rbf"}, "GP Matern 0.5": {"nu": 0.5},
    "blend 0.3 GAM": {"w": 0.3}, "blend 0.7 GAM": {"w": 0.7},
    "GAM site-specific curves": {"site_inter": True},
    "GAM + linked pair terms": {"pairs": True},
    "GAM site + pairs": {"site_inter": True, "pairs": True},
    "GP on GAM residuals": {"mode": "resid"},
    "GP on GAM residuals, M2.5": {"mode": "resid", "nu": 2.5},
    "GP on residuals of site-GAM": {"mode": "resid", "site_inter": True},
    "site-GAM + GP avg, M2.5": {"site_inter": True, "nu": 2.5},
    "GAM only": {"mode": "gam"},
    "GP restarts 4": {"restarts": 4},
}

if __name__ == "__main__":
    res = Parallel(n_jobs=min(len(CANDS), 19), verbose=0)(delayed(evaluate)(n, c) for n, c in CANDS.items())
    res.sort(key=lambda r: r["fresh_MAE"])
    json.dump(res, open(ROOT / "data" / "r4_tweaks.json", "w"), indent=1)
    base = next(r for r in res if r["name"].startswith("current"))
    print(f"{'candidate':32s} fresh: MAE   RMSE   max   acc  | LGO mean | CV: MAE   max   acc | wins all 3?")
    for r in res:
        better = r["fresh_MAE"] < base["fresh_MAE"] and r["lgo_mean"] < base["lgo_mean"] and r["cv_MAE"] < base["cv_MAE"]
        print(f"{r['name']:32s} {r['fresh_MAE']:.4f} {r['fresh_RMSE']:.4f} {r['fresh_max']:.3f} {r['fresh_acc']:.3f} | "
              f"{r['lgo_mean']:.4f}  | {r['cv_MAE']:.4f} {r['cv_max']:.3f} {r['cv_acc']:.3f} | {'YES' if better else ''}  ({r['secs']}s)")
