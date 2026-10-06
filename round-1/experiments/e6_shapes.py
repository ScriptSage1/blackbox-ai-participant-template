"""Experiment 6 — shape detail where the curves bend, ignored features at sites B/C, determinism near cut-off. 9 queries."""
from bb import BASELINE, query
from e4_cutoff import point  # path-1 points
rows = [BASELINE | {"tenure_years": v} for v in (2.5, 5, 7.5)]
rows += [BASELINE | {"badge_age_days": v} for v in (65, 70)]
rows += [BASELINE | {"recent_denials": 2.8}]
rows += [BASELINE | dict(site="C", anomaly_ratio=1, clearance_level=0, escorts=6),
         BASELINE | dict(site="B", anomaly_ratio=0, clearance_level=100, escorts=0)]
rows += [point(0.25)]  # repeat of the 0.4595 APPROVE point (E4)
query(rows, tag="E6_shapes")
