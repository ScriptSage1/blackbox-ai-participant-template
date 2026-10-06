"""Experiment 3 — are the flat features (anomaly_ratio, clearance_level, escorts) flat everywhere?
Also: first DECLINE region, and localise the recent_denials drop. 23 queries."""
from bb import BASELINE, query

LOW = BASELINE | dict(history_score=900, linked_badges=0, tenure_years=0, badge_age_days=75,
                      recent_denials=5, requested_zone=100, site="D")
HIGH = BASELINE | dict(history_score=300, linked_badges=20, tenure_years=30, badge_age_days=18,
                       recent_denials=0, requested_zone=25, site="A")
rows = []
for anchor in (LOW, HIGH):
    rows.append(dict(anchor))
    for k, vals in (("anomaly_ratio", (0, 1)), ("clearance_level", (0, 100)), ("escorts", (0, 6))):
        for v in vals:
            rows.append(anchor | {k: v})
# joint corners of the 3 flat features at baseline (half-fraction)
for a, c, e in ((1, 0, 0), (1, 100, 6), (0, 100, 0), (0, 0, 6)):
    rows.append(BASELINE | dict(anomaly_ratio=a, clearance_level=c, escorts=e))
# recent_denials fine look between 2 and 3.5 (rounding vs threshold)
for d in (2.0, 2.4, 2.6, 3.0, 3.4):
    rows.append(BASELINE | dict(recent_denials=d))

assert len(rows) == 23
query(rows[:14], tag="E3_flat_context")
query(rows[14:], tag="E3_joint_denials")
