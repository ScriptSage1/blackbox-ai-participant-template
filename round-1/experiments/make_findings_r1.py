"""Build template/round-1/findings.json from data/export_r1.json (evidence ids = query_index)."""
import json
from bb import BASELINE, FIELDS, ROOT

Q = json.load(open(ROOT / "data" / "export_r1.json"))
P = BASELINE | dict(badge_age_days=50.775, history_score=645.0, linked_badges=8.5, recent_denials=2.875,
                    requested_zone=57.5, tenure_years=17.0)
LOW = BASELINE | dict(history_score=900, linked_badges=0, tenure_years=0, badge_age_days=75,
                      recent_denials=5, requested_zone=100, site="D")
HIGH = BASELINE | dict(history_score=300, linked_badges=20, tenure_years=30, badge_age_days=18,
                       recent_denials=0, requested_zone=25, site="A")
KEYS = list(FIELDS) + ["site"]


def varies_only(anchor, feats):
    """rows that equal `anchor` everywhere except (possibly) in `feats`."""
    return [str(q["query_index"]) for q in Q if all(q[k] == anchor[k] for k in KEYS if k not in feats)]


def oat(k, anchors=(BASELINE, P)):
    return sorted({i for a in anchors for i in varies_only(a, [k])}, key=int)


IGN = ["anomaly_ratio", "clearance_level", "escorts"]


def ignored_ids():
    ids = set()
    for a in (BASELINE, LOW, HIGH):
        ids |= set(varies_only(a, IGN))
    ids |= set(varies_only(BASELINE, IGN + ["site"]))
    return sorted(ids, key=int)


def score_ids(lo, hi):
    return [str(q["query_index"]) for q in Q if lo <= q["score"] <= hi]


def fe(feature, direction, strength, conf, summary, ids=None):
    return dict(type="feature_effect", feature=feature, direction=direction, strength=strength,
                confidence=conf, evidence=dict(query_ids=ids or oat(feature), summary=summary))


MAX_IDS = [str(q["query_index"]) for q in Q if q["query_index"] >= 146]  # E10 score maximisation
BEST = max(Q, key=lambda q: q["score"])
BEST_TXT = (f"Best score of all {len(Q)} queries: {BEST['score']} (query {BEST['query_index']}: history_score "
            f"{BEST['history_score']:g}, linked_badges {BEST['linked_badges']:g}, badge_age_days {BEST['badge_age_days']:g}, "
            f"recent_denials {BEST['recent_denials']:g}, site {BEST['site']}, tenure_years {BEST['tenure_years']:g}, "
            f"requested_zone {BEST['requested_zone']:g}).")
lo_app = min(q["score"] for q in Q if q["decision"] == "APPROVE")
hi_dec = max(q["score"] for q in Q if q["decision"] == "DECLINE")

claims = [
    fe("history_score", "decreases", "strong", 0.95,
       "OAT from the all-midpoint baseline (site A): 300→.932, 450→.882, 525→.872, 600→.821, 615→.813, 630→.782, "
       "645→.778, 660→.760, 675→.712, 750→.679, 825→.582, 900→.526. Monotone decreasing at all 12 levels, but unevenly "
       "(jumps at 615–630 and 660–675, near-flat 630–645), i.e. step-like. Same direction at a second anchor P (score .580): "
       "300→.878, 900→.420 (flips to DECLINE). Largest single-feature effect."),
    fe("linked_badges", "increases", "strong", 0.95,
       "Baseline OAT: 0→.622, 2.5→.635, 5→.724, 7.5→.783, 10→.821, 15→.874, 17.5→.890, 20→.902 — monotone increasing, "
       "steepest 2.5–5, diminishing returns above 10. Anchor P: 0→.357 (DECLINE), 20→.837. In a 2×2 with history_score "
       "300/900, linked 0→20 adds +1.78 vs +1.54 in log-odds: same direction, roughly additive with history."),
    fe("tenure_years", "non_monotonic", "strong", 0.75,
       "Baseline: 0→.629, 2.5→.636, 5→.671, 7.5→.736, 10→.792, 20→.821, 25→.825, 30→.836, 35→.833, 40→.818 — strong rise "
       "(steepest 5–10), peak ~30–35, then a decline to 40. Anchor P shows the same: 0→.385, 10→.530, 17→.580, 30→.643, "
       "40→.628. The fall after the peak is small (~0.015–0.018) but replicated at both anchors; the dominant effect is increasing. "
       "Score maximisation (all monotone inputs at their best end, queries 146–150) confirms an interior optimum: tenure 32–33 "
       "beat 30 (.9833/.9840 vs .9829). " + BEST_TXT, oat("tenure_years") + MAX_IDS),
    fe("badge_age_days", "decreases", "moderate", 0.9,
       "Decreasing overall at both anchors (18 vs 75: .873→.691 at baseline, .691→.447 at P), but WHERE it drops depends on "
       "the other inputs. Baseline: 46.5 .821, 55 .809, 61 .786, 65 .762, 70 .754, 71 .745, 72 .725, 73 .709, 74 .688, "
       "75 .691 (sharp drop 70–74). Anchor P: 50.8 .580, 55 .596, 60 .516, 65 .465, 70 .460, 72 .454, 75 .447 (sharp drop "
       "55–65, flat after). Small non-monotone wiggles at both (74→75, 50.8→55)."),
    fe("recent_denials", "decreases", "moderate", 0.9,
       "Baseline: 0→.833, 1.25→.832, 2→.823, 2.4→.819, 2.5→.821, 2.55→.819, 2.6→.808, 2.65→.796, 2.7→.787, 2.75→.770, "
       "2.8→.772, 2.9→.756, 3→.751, 3.4→.735, 3.75→.698, 5→.635: nearly flat to ~2.5, steep 2.55–2.75, then steady decline. "
       "Anchor P: 0→.684, 2.5→.639, 2.6→.633, 2.7→.621, 2.875→.580, 5→.438 (DECLINE)."),
    fe("requested_zone", "decreases", "weak", 0.7,
       "Baseline: 0→.819, 10→.828, 25→.833, 37.5→.824, 50→.821, 62.5→.807, 75→.784, 87.5→.762, 100→.734; anchor P: "
       "0→.636, 25→.638, 57.5→.580, 75→.547, 100→.500. Slight rise (or flat) over 0–25, then steadily decreasing. "
       "Weakest of the active numeric inputs; dominant direction decreasing. Score maximisation (queries 146–150): with all other "
       "inputs at their best, zone 15 > 20 > 25 > 30 (.9849, .9840/.9838, .9833, .9831), so in that context the optimum is "
       "≤15–20. " + BEST_TXT, oat("requested_zone") + MAX_IDS),
    fe("site", "decreases", "weak", 0.6,
       "Categorical: same ordering A > B > C > D at three anchors. Baseline A .821, B .813, C .804, D .803; anchor P "
       "A .580, B .573, C .572, D .566; LOW anchor A .058 vs D .053. 'decreases' = in the order A→D. Small effect (≤0.02).",
       sorted(set(varies_only(BASELINE, ["site"]) + varies_only(P, ["site"])), key=int)),
]
for f in IGN:
    claims.append(dict(type="ignored_feature", feature=f, confidence=0.9, evidence=dict(query_ids=ignored_ids(), summary=(
        f"{f} varied over its full range (min/25%/75%/max at baseline; min/max at a deep-DECLINE anchor (.0529) and a "
        "deep-APPROVE anchor (.9829)), plus 4 joint corners of anomaly_ratio×clearance_level×escorts, and at sites B and C. "
        "Score identical to all 4 reported decimals in every case (.8213 / .0529 / .9829 / .8130 / .8044). "
        "Caveat: we cannot exclude an effect smaller than the 4-dp output resolution, or one confined to an untested region."))))
claims += [
    dict(type="threshold", feature="recent_denials", value=2.65, tolerance=0.15, confidence=0.6, evidence=dict(
        query_ids=oat("recent_denials"), summary=(
            "Baseline sweep: nearly flat from 0 to 2.55 (.833→.819), then the steepest stretch between 2.55 and 2.75 "
            "(.819→.770, ~0.25/unit vs <0.01/unit below 2.5), slower decline after. A sharp bend rather than a clean step; "
            "not integer rounding (2.4≠2.0, 2.6≠3.0). At anchor P the bend is softer (steepest ~2.7–2.9), so the location "
            "may shift slightly with context."))),
    dict(type="threshold", feature="badge_age_days", value=72, tolerance=2, confidence=0.35, evidence=dict(
        query_ids=oat("badge_age_days"), summary=(
            "At the all-midpoint baseline: 65→.762, 70→.754, 71→.745, 72→.725, 73→.709, 74→.688 — the drop starts at ~70–71 "
            "(.066 over 70–74 vs .008 over 65–70). LOW confidence as a context-free threshold: at a second anchor P the sharp "
            "drop is instead at 55–65 (.596→.465) and 65–75 is nearly flat, so the bend location depends on other inputs "
            "(an interaction we will identify in Round 2)."))),
    dict(type="threshold", feature="score", value=0.450, tolerance=0.004, confidence=0.9, evidence=dict(
        query_ids=[str(q["query_index"]) for q in Q], summary=(
            "Decision cut-off on the score, not 0.5: walking from the baseline toward a low-score corner and bisecting gave "
            "APPROVE at .4595 and DECLINE at .4404; anchor-P queries add DECLINE at .4466 and APPROVE at .4541. Across all "
            f"{len(Q)} queries the lowest APPROVE score is {lo_app} and the highest DECLINE is {hi_dec} — zero exceptions to "
            "'APPROVE iff score > ~0.45', so no decision rule separate from the score has been seen. Repeating the .4595 "
            "query gave the identical result (deterministic at the boundary). Evidence lists all queries because every one "
            "of them is a check of this rule. " + BEST_TXT))),
]

out = dict(round="round-1", team="BB-001", queries_used=len(Q), claims=claims)
p = ROOT / "template" / "round-1" / "findings.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print("min APPROVE", lo_app, "max DECLINE", hi_dec)
for c in claims:
    print(c["type"], c.get("feature"), len(c["evidence"]["query_ids"]), "ids")
