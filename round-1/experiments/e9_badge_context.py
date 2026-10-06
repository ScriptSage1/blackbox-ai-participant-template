"""Experiment 9 - locate the badge_age bend at anchor P vs baseline. 3 queries."""
from bb import BASELINE, query
from e5_oat_anchor2 import P
if __name__ == "__main__":
    query([P | {"badge_age_days": 55}, P | {"badge_age_days": 60}, BASELINE | {"badge_age_days": 55}], tag="E9_badge_context")
