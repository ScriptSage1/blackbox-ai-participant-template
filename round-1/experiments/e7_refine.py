"""Experiment 7 — refine R1 claims: bend locations, tenure dip, shape gaps, history x linked additivity. 25 queries."""
from bb import BASELINE, query
lv = dict(badge_age_days=(71, 72, 73, 74), recent_denials=(2.55, 2.65, 2.7, 2.75, 2.9), tenure_years=(25, 35),
          history_score=(525, 675, 825), linked_badges=(2.5, 7.5, 17.5), requested_zone=(10, 37.5, 62.5, 87.5))
rows = [BASELINE | {k: v} for k, vs in lv.items() for v in vs]
rows += [BASELINE | dict(history_score=h, linked_badges=l) for h in (300, 900) for l in (0, 20)]
assert len(rows) == 25
query(rows, tag="E7_refine")
