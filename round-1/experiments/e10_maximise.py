"""Experiment 10 — construct the highest-scoring input from R1 knowledge.
Best known: HIGH anchor = 0.9829. Every monotone input at its best end (history 300, linked 20, badge 18,
denials 0, site A); ignored inputs left at midpoint. Probe the two interior optima (tenure ~30-33, zone ~20-30)."""
import sys
from bb import BASELINE, query

BEST = BASELINE | dict(history_score=300, linked_badges=20, badge_age_days=18, recent_denials=0, site="A")
if __name__ == "__main__":
    pairs = [tuple(map(float, a.split(","))) for a in sys.argv[1:]] or [(32, 25), (30, 20), (30, 30), (33, 20)]
    query([BEST | dict(tenure_years=t, requested_zone=z) for t, z in pairs], tag="E10_maximise")
