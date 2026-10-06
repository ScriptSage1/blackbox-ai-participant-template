"""Experiment 8 — stepwise history? bends at anchor P? 10 queries."""
from bb import BASELINE, query
from e5_oat_anchor2 import P  # noqa (module only defines P + runs under __main__)
rows = [BASELINE | {"history_score": v} for v in (615, 630, 645, 660)]
rows += [P | {"recent_denials": v} for v in (2.5, 2.6, 2.7)]
rows += [P | {"badge_age_days": v} for v in (65, 70, 72)]
query(rows, tag="E8_steps_bends")
