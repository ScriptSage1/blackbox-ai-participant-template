"""Experiment 5 — OAT at a second anchor P (path-1 t=0.15 point, score 0.5803, near the cut-off). 19 queries."""
from bb import BASELINE, query

P = BASELINE | dict(badge_age_days=50.775, history_score=645.0, linked_badges=8.5, recent_denials=2.875,
                    requested_zone=57.5, tenure_years=17.0)
levels = dict(tenure_years=(0, 10, 30, 40), requested_zone=(0, 25, 75, 100), history_score=(300, 900),
              linked_badges=(0, 20), badge_age_days=(18, 75), recent_denials=(0, 5))
if __name__ == "__main__":
  rows = [P | {k: v} for k, vs in levels.items() for v in vs] + [P | {"site": s} for s in "BCD"]
  assert len(rows) == 19
  query(rows, tag="E5_oat_anchorP")
