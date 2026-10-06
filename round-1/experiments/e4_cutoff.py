"""Experiment 4 — locate the APPROVE/DECLINE cut-off along the baseline->LOW path (site A held)."""
import sys
from bb import BASELINE, FIELDS, query

LOW = dict(history_score=900, linked_badges=0, tenure_years=0, badge_age_days=75, recent_denials=5, requested_zone=100)

def point(t):
    return BASELINE | {k: BASELINE[k] + t * (v - BASELINE[k]) for k, v in LOW.items()}

if __name__ == "__main__":
  ts = [float(x) for x in sys.argv[1:]] or [0.4, 0.55, 0.7, 0.85, 1.0]
  query([point(t) for t in ts], tag="E4_cutoff")
