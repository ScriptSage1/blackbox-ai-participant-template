"""Validation suite for round-4/surrogate.py. Run from round-4/:  python experiments/validate_replica.py

1. Out-of-distribution test: fit on R1 + R2 + public rows, predict the 80 Round 4 queries (never seen in fitting).
2. Leave-one-group-out: R1 / R2 / public / R4 space-filling / R4 disagreement.
3. 5-fold CV on all rows.  4. Champion check.  5. Interaction fidelity.  6. Worst errors.  7. Residual vs input plots.
"""
import csv, json, sys
from pathlib import Path
import numpy as np
from sklearn.model_selection import KFold

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import surrogate as S  # noqa: E402

rows = list(csv.DictReader(open(HERE / "gk05_canonical.csv", encoding="utf-8")))
y = np.array([float(r["score"]) for r in rows])


def m(yt, p):
    e = yt - p
    return dict(n=len(yt), MAE=round(float(np.mean(abs(e))), 4), RMSE=round(float(np.sqrt(np.mean(e ** 2))), 4),
                R2=round(float(1 - np.sum(e ** 2) / np.sum((yt - yt.mean()) ** 2)), 4), MaxErr=round(float(np.max(abs(e))), 4),
                DecisionAcc=round(float(np.mean((yt > S.CUTOFF) == (p > S.CUTOFF))), 4))


def holdout(test_idx):
    tr = [rows[i] for i in range(len(rows)) if i not in set(test_idx)]
    te = [rows[i] for i in test_idx]
    return S.predict_scores(te, S.fit(tr))


out = {}
grp = {"R1": [i for i, r in enumerate(rows) if r["round"] == "R1"], "R2": [i for i, r in enumerate(rows) if r["round"] == "R2"],
       "public": [i for i, r in enumerate(rows) if r["round"] == "public"],
       "R4-space-filling": [i for i, r in enumerate(rows) if r["tag"] == "R4_B1_lhs"],
       "R4-disagreement": [i for i, r in enumerate(rows) if r["tag"] == "R4_B2_disagree"]}
r4 = grp["R4-space-filling"] + grp["R4-disagreement"]
p4 = holdout(r4)
out["R4_unseen_80"] = m(y[r4], p4)
out["leave_group_out"] = {g: m(y[ix], holdout(ix)) for g, ix in grp.items()}
cv = np.zeros(len(rows))
for a, b in KFold(5, shuffle=True, random_state=0).split(rows):
    cv[b] = holdout(list(b))
out["cv5_all"] = m(y, cv)

full = S.fit(rows)
ref = dict(badge_age_days=23.5, history_score=349, linked_badges=18.4, recent_denials=0.5, requested_zone=18, tenure_years=22,
           site="B", anomaly_ratio=0, clearance_level=75, escorts=0)
pc = float(S.predict_scores([ref], full)[0]); pc_cv = float(S.predict_scores([ref], S.fit([r for r in rows if not (
    r["site"] == "B" and abs(float(r["badge_age_days"]) - 23.5) < 1e-9 and abs(float(r["linked_badges"]) - 18.4) < 1e-9
    and abs(float(r["history_score"]) - 349) < 1e-9)]))[0])
out["champion"] = dict(actual=0.9972, replica_full=round(pc, 4), replica_without_champion_rows=round(pc_cv, 4))


def P(**kw):
    return float(S.predict_scores([{**ref, **kw}], full)[0])


# observed pairs from the R2 interaction experiments (actual GK-05 differences) vs replica differences
out["interaction_fidelity"] = {
    "badge23_minus_badge18 at linked 18 (obs +0.0026)": round(P(badge_age_days=23, requested_zone=14) - P(badge_age_days=18, requested_zone=14), 4),
    "badge23_minus_badge18 at linked 10 (obs -0.0010)": round(P(badge_age_days=23, requested_zone=14, linked_badges=10) - P(badge_age_days=18, requested_zone=14, linked_badges=10), 4),
    "denials0.5_minus_0 at linked 18 (obs +0.0018)": round(P(recent_denials=0.5, linked_badges=18, requested_zone=16, history_score=349) - P(recent_denials=0, linked_badges=18, requested_zone=16), 4),
    "denials0.5_minus_0 at linked 10 (obs -0.0001)": round(P(recent_denials=0.5, linked_badges=10, requested_zone=16) - P(recent_denials=0, linked_badges=10, requested_zone=16), 4),
    "site-B tenure 10 vs 12 (gate; obs 0.032 vs normal)": [round(P(tenure_years=10), 4), round(P(tenure_years=12), 4)],
    "inert check: escorts 0 vs 6, anomaly 0 vs 1 (should be equal)": [round(P(escorts=0, anomaly_ratio=0), 4), round(P(escorts=6, anomaly_ratio=1), 4)],
}
err = y[r4] - p4
out["worst_unseen_R4"] = [dict(source=rows[r4[i]]["source"], observed=float(y[r4[i]]), predicted=round(float(p4[i]), 4),
                               site=rows[r4[i]]["site"], tenure=float(rows[r4[i]]["tenure_years"]))
                          for i in np.argsort(-abs(err))[:8]]
json.dump(out, open(HERE / "validation_results.json", "w"), indent=1)
print(json.dumps(out, indent=1))

try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plots = HERE.parent / "plots"; plots.mkdir(exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    ax[0].plot([0, 1], [0, 1], color="#999", lw=1)
    for g, c in (("R4-space-filling", "#2a7ab9"), ("R4-disagreement", "#d9822b")):
        ix = [r4.index(i) for i in grp[g]]
        ax[0].scatter(y[grp[g]], p4[ix], s=22, c=c, label=f"{g} ({len(ix)})")
    ax[0].set(xlabel="GK-05 observed score", ylabel="replica prediction (not trained on these)", title="80 unseen Round 4 queries")
    ax[0].legend()
    B = [i for i, r in enumerate(rows) if r["site"] == "B"]
    t = np.array([float(rows[i]["tenure_years"]) for i in B])
    ax[1].scatter(t, y[B], s=14, c=["#c0392b" if v < S.FLOOR_TENURE else "#2a7ab9" for v in t])
    ax[1].axvline(S.FLOOR_TENURE, color="#c0392b", ls="--", lw=1)
    ax[1].set(xlabel="tenure_years", ylabel="GK-05 score", title=f"Site B: score = 0.032 whenever tenure < {S.FLOOR_TENURE} ({len(B)} rows)")
    fig.tight_layout(); fig.savefig(plots / "r4_validation.png", dpi=120)
    res = y - cv
    keys = list(S.RANGES)
    fig, axs = plt.subplots(2, 3, figsize=(12, 6.5))
    for a, k in zip(axs.flat, keys):
        a.scatter([float(r[k]) for r in rows], res, s=8, c="#2a7ab9"); a.axhline(0, color="#999", lw=1)
        a.set(xlabel=k, ylabel="residual (5-fold CV)")
    fig.suptitle("Residuals vs inputs (observed - held-out prediction, all 435 rows)"); fig.tight_layout()
    fig.savefig(plots / "r4_residuals.png", dpi=120)
except Exception as e:  # plots are optional
    print("plotting skipped:", e)
