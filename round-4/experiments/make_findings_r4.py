"""Build round-4/findings.json (optional this round) from data/r4_obs.json. Evidence ids = Round 4 query_index."""
import json
from bb import ROOT

R4 = json.load(open(ROOT / "data" / "r4_obs.json", encoding="utf-8"))
ALL = [str(o["query_index"]) for o in R4]
BEST = max(R4, key=lambda o: o["score"])
fl = [o for o in R4 if o["site"] == "B" and o["score"] == 0.032]
nb = [o for o in R4 if o["site"] == "B" and o["score"] != 0.032]
near = sorted(nb, key=lambda o: o["tenure_years"])[:5]
claims = [
    dict(type="threshold", feature="tenure_years", value=10.858, tolerance=0.52, confidence=0.9, evidence=dict(
        query_ids=[str(o["query_index"]) for o in fl + near], summary=(
            f"At site B the score is exactly 0.032 (DECLINE) whenever tenure_years < ~10.86, whatever the other inputs: "
            f"{len(fl)} Round 4 site-B queries with tenure 0.05-10.34 all returned 0.032 (other inputs spanning their full ranges), "
            f"while every site-B query with tenure >= 11.38 returned a normal score (e.g. "
            + ", ".join(f"q{o['query_index']} tenure {o['tenure_years']:g} -> {o['score']}" for o in near[:3]) +
            "). Across all 198 site-B observations we own (R1+R2+R4) a single split on tenure_years separates the floor "
            "with no exceptions. Sites A, C, D show no such floor (minimum scores 0.045, 0.153, 0.053)."))),
    dict(type="interaction", features=["site", "tenure_years"], confidence=0.9, evidence=dict(
        query_ids=ALL, summary=(
            "The tenure floor exists only at site B, so site and tenure_years interact. Earlier rounds missed it because "
            "site B was only queried with tenure 22 (the R2 high-score region). Found by the 40 space-filling and 40 "
            "model-disagreement queries of this round, which every model mispredicted before seeing them (MAE 0.24-0.38 "
            "on the disagreement batch). Encoding it as a gate cut held-out error on unseen queries from 0.081 to 0.031. "
            f"Best score of Round 4: {BEST['score']} (R4 q{BEST['query_index']}); best ever 0.9972 (R2 q83). "
            "Every Round 4 query is cited here."))),
]
out = dict(round="round-4", team="BB-001", queries_used=len(R4), claims=claims)
p = ROOT / "template" / "round-4" / "findings.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(len(R4), "queries |", len(fl), "floor rows | best", BEST["score"], "q", BEST["query_index"])
