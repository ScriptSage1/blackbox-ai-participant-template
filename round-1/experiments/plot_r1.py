"""R1 plot: one-feature response curves at the baseline and at anchor P, from logged queries."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from bb import BASELINE, FIELDS, LOG, ROOT

P = BASELINE | dict(badge_age_days=50.775, history_score=645.0, linked_badges=8.5, recent_denials=2.875,
                    requested_zone=57.5, tenure_years=17.0)
pts = [(r_in, o) for line in LOG.read_text(encoding="utf-8").splitlines()
       for r_in, o in zip(json.loads(line)["inputs"], json.loads(line)["response"]["outputs"])]
pts.append((BASELINE, {"score": 0.8213}))  # Q1/Q2 (web console)
pts.append((P, {"score": 0.5803}))


def curve(anchor, k):
    xs = sorted({(r[k], o["score"]) for r, o in pts
                 if all(r[j] == anchor[j] for j in anchor if j != k)})
    return [x for x, _ in xs], [y for _, y in xs]


feats = list(FIELDS) + ["site"]
fig, axes = plt.subplots(2, 5, figsize=(17, 6.5), sharey=True)
for ax, k in zip(axes.flat, feats):
    for anchor, name, c in ((BASELINE, "baseline", "#1f77b4"), (P, "anchor P", "#d62728")):
        x, y = curve(anchor, k)
        if k == "site":
            order = sorted(range(len(x)), key=lambda i: x[i])
            x, y = [x[i] for i in order], [y[i] for i in order]
        ax.plot(x, y, "o-", color=c, ms=4, label=name)
    ax.axhline(0.45, color="grey", ls="--", lw=1)
    ax.set_title(k, fontsize=10)
    ax.set_ylim(0, 1)
axes.flat[0].legend(fontsize=8)
axes[0, 0].set_ylabel("score"); axes[1, 0].set_ylabel("score")
fig.suptitle("GK-05 — one-feature-at-a-time responses (dashed: APPROVE/DECLINE cut-off ≈ 0.45)")
fig.tight_layout()
out = ROOT / "plots" / "r1_oat_curves.png"
fig.savefig(out, dpi=130)
print(out)
