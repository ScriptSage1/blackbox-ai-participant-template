"""Experiment 2 — one-at-a-time sweep from the midpoint baseline (39 queries)."""
import json
from bb import BASELINE, FIELDS, SITES, query

rows, labels = [], []
for k, (lo, hi) in FIELDS.items():
    for frac in (0, 0.25, 0.75, 1):
        r = dict(BASELINE); r[k] = lo + frac * (hi - lo)
        rows.append(r); labels.append((k, r[k]))
for s in SITES[1:]:
    r = dict(BASELINE); r["site"] = s
    rows.append(r); labels.append(("site", s))

out = []
for i in range(0, len(rows), 25):
    resp = query(rows[i:i + 25], tag="E2_oat")
    out.append(resp)
print(json.dumps(out[0], indent=1)[:1500])
