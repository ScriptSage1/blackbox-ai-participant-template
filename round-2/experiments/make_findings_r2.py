"""Build round-2/findings.json from data/export_r2.json. Evidence ids = Round 2 query_index (R2 numbering)."""
import json
from bb import ROOT

Q = json.load(open(ROOT / "data" / "export_r2.json"))
BY = {q["query_index"]: q for q in Q}
ALL = [str(q["query_index"]) for q in Q]
BEST = max(Q, key=lambda q: q["score"])
BEST_TXT = (f"Best score of Round 2: {BEST['score']} (R2 query {BEST['query_index']}: badge_age_days {BEST['badge_age_days']:g}, "
            f"linked_badges {BEST['linked_badges']:g}, history_score {BEST['history_score']:g}, recent_denials "
            f"{BEST['recent_denials']:g}, requested_zone {BEST['requested_zone']:g}, site {BEST['site']}, tenure_years "
            f"{BEST['tenure_years']:g}; anomaly_ratio {BEST['anomaly_ratio']:g}, clearance_level {BEST['clearance_level']:g}, "
            f"escorts {BEST['escorts']:g}).")


def ids(*ranges):
    out = []
    for r in ranges:
        a, b = (r, r) if isinstance(r, int) else r
        out += [str(i) for i in range(a, b + 1) if i in BY]
    return out


claims = [
    dict(type="interaction", features=["badge_age_days", "linked_badges"], confidence=0.85, evidence=dict(
        query_ids=ids(1, 3, 4, 7, 8, (17, 18), (35, 38), (45, 61)), summary=(
            "Whether a younger or older badge scores better depends on linked_badges. Design: at the champion "
            "(linked 18) move ONE suspect input to its Round-1 baseline value and compare badge_age 23 vs 18. "
            "s(23)-s(18): champion +0.0026 (q35 vs q45); history 600 +0.0033 (q47/q46); linked 10 -0.0010 (q49/q48, sign flips: "
            "younger badge better, as at the R1 baseline); denials 2.5 +0.0070 (q51/q50); zone 50 +0.0031 (q53/q52); "
            "site A +0.0026 (q55/q54). Only linked_badges flips it, so it is the interaction partner that explains Round 1's "
            "observation that badge_age's drop moved between operating points. Near the top badge_age has an interior "
            "optimum at ~23 (18 .9920, 20.5 .9939, 23 .9945, 25 .9938, 27 .9921 at linked 18)."))),
    dict(type="interaction", features=["badge_age_days", "recent_denials"], confidence=0.55, evidence=dict(
        query_ids=ids((45, 51)), summary=(
            "The older-badge advantage is larger when recent_denials is high: s(23)-s(18) = +0.0026 at denials 0.5 but "
            "+0.0070 at denials 2.5 (q50/q51), other inputs fixed. Only two levels tested, so moderate confidence."))),
    dict(type="interaction", features=["recent_denials", "linked_badges"], confidence=0.8, evidence=dict(
        query_ids=ids(15, 26, (97, 104)), summary=(
            "The benefit of a small number of recent_denials (0.5 vs 0) near the top exists only when linked_badges is high. "
            "Design: from the champion move ONE suspect to its Round-1 baseline value and compare denials 0.5 vs 0. "
            "s(0.5)-s(0): champion context +0.0018 (q26 vs q15); linked 10 -0.0001 (q98/q97, benefit vanishes); badge 46.5 "
            "+0.0026 (q100/q99); history 600 +0.0032 (q102/q101); zone 50 +0.0013 (q104/q103). linked_badges is therefore the "
            "input that gates both near-top effects (this one and the badge_age flip). It also explains why denials 0-1.25 "
            "was flat at the Round 1 baseline, where linked_badges was 10."))),
    dict(type="feature_effect", feature="recent_denials", direction="non_monotonic", strength="moderate", confidence=0.85,
         evidence=dict(query_ids=ids(15, (26, 34)), summary=(
             "Near the top (champion context, zone 16) the score is NOT best at 0 denials: 0 .9948, 0.25 .9962, 0.4 .9963, "
             "0.5 .9966, 0.6 .9960, 0.75 .9958, 1.0 .9940, 1.25 .9959, 1.5 .9926, 2.0 .9940 — jagged, peak at ~0.5. "
             "At the Round 1 baseline 0 to 1.25 was flat (.833/.832), so this is context-dependent."))),
    dict(type="feature_effect", feature="linked_badges", direction="non_monotonic", strength="moderate", confidence=0.85,
         evidence=dict(query_ids=ids(1, 3, 4, 43, 44, (56, 61), (72, 73), (76, 78)), summary=(
             "Near the top: linked 16 .9942, 17 .9939, 18 .9945, 19 .9942 (and BB-008's published 20 .9899, reproduced "
             "context) at denials 0; 17.5 .9960, 18 .9966, 19 .9961 at denials 0.5; linked 20 costs ~0.006 even with "
             "badge 25-27 (q58, q59). Fractional values matter (not rounded): 18.2/18.3/18.4 .9970, 18.5 .9967, 18.6 .9958 (q72-q78) "
             "vs 18 .9968 and 19 .9961. At the Round 1 baseline linked was monotone increasing (0 .622 -> 20 .902), "
             "so the near-top optimum (~18) reflects context/interaction."))),
    dict(type="feature_effect", feature="history_score", direction="non_monotonic", strength="moderate", confidence=0.8,
         evidence=dict(query_ids=ids(1, 9, 10, 41, 42, 2), summary=(
             "Near the top the optimum is ~350, not the minimum 300: 330 .9942, 349 .9945, 370 .9940 (denials 0) and "
             "340 .9958, 349 .9966, 358 .9962 (denials 0.5). Round 1 at the midpoint baseline showed monotone decrease "
             "(300 best), so the low-end turn-around only appears in the high-score region."))),
    dict(type="feature_effect", feature="requested_zone", direction="non_monotonic", strength="moderate", confidence=0.8,
         evidence=dict(query_ids=ids(1, 11, 12, 14, 15, 16, 35, 36, 26), summary=(
             "Near the top: zone 0 .9891 (sharp penalty), 4.5 .9945, 8 .9943, 12 .9946, 16 .9948, 20 .9934 (denials 0) and "
             "14 .9968, 16 .9966, 18 .9968 (denials 0.5). Interior optimum ~14-18 with a steep drop toward 0."))),
    dict(type="feature_effect", feature="tenure_years", direction="non_monotonic", strength="weak", confidence=0.75,
         evidence=dict(query_ids=ids(5, 6, 19, 20, 39, 40), summary=(
             "Near the top: 19 .9941, 22 .9946, 24 .9942, 27 .9930, 32 .9930 (denials 0); 21 .9966, 22 .9966, 23 .9965 "
             "(denials 0.5). Peak ~21-23 here, versus ~30-35 at the Round 1 baseline — the peak position shifts with context."))),
]
for f, q in (("anomaly_ratio", 23), ("clearance_level", 24), ("escorts", 25)):
    claims.append(dict(type="ignored_feature", feature=f, confidence=0.9, evidence=dict(
        query_ids=ids(q, 15), summary=(
            f"At the high-score champion (0.9948, q15) setting {f} to its opposite extreme gave exactly 0.9948 (q{q}). "
            "Together with Round 1 (flat at three other operating points and all sites) this shows it is ignored in every "
            "region tested, including near the maximum."))))
claims.append(dict(type="interaction", features=["badge_age_days", "linked_badges", "recent_denials", "requested_zone",
                                                 "history_score", "tenure_years", "site"], confidence=0.8, evidence=dict(
    query_ids=ALL, summary=(
        "The joint optimum is not the combination of per-input optima found at the Round 1 baseline: there, lowest badge "
        "age, highest linked_badges, lowest history, 0 denials and site A were each best; near the top the best values "
        "are badge ~23, linked 18, history ~350, denials ~0.5, zone ~14-18, tenure ~22, site B (B .9946 > A .9939 > C .9924 > "
        "D .9881, q12/q13/q21/q22). Every Round 2 query is a comparison against this joint optimum. Starting point: "
        "BB-008's published 0.9945 input, verified by our own reproduction (q1, exact). " + BEST_TXT))))

out = dict(round="round-2", team="BB-001", queries_used=len(Q), claims=claims)
p = ROOT / "template" / "round-2" / "findings.json"
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(len(Q), "queries;", len(claims), "claims; cited:", len({i for c in claims for i in c["evidence"]["query_ids"]}), "| best", BEST["score"])
