"""Round 2 query helper: send rows, log them, print results, track the champion.

    from r2q import send, CHAMP
    send([row, ...], tag="R2_xxx")
"""
import json
from bb import query, ROOT, FIELDS

STATE = ROOT / "data" / "r2_state.json"
KEYS = list(FIELDS) + ["site"]


def _load():
    return json.load(open(STATE)) if STATE.exists() else {"best_score": 0.0, "best_input": None, "best_qi": None}


def send(rows, tag):
    st = _load()
    resp = query(rows, tag=tag)
    qi0 = resp.get("query_index")
    for i, (r, o) in enumerate(zip(rows, resp["outputs"])):
        qi = (qi0 + i) if qi0 is not None else None
        new = o["score"] > st["best_score"]
        if new:
            st.update(best_score=o["score"], best_input={k: r[k] for k in KEYS}, best_qi=qi)
        print(f"  q{qi} {o['score']:.4f} {o['decision']:8s}{' <-- NEW BEST' if new else ''} {r}")
    json.dump(st, open(STATE, "w"), indent=1)
    print(f"quota {resp['quota']} | champion {st['best_score']} (q{st['best_qi']})")
    return resp
