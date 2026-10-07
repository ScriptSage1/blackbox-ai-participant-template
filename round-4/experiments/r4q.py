"""Round 4 query helper: send rows in chunks of 25, log them with the reason they were chosen, append to data/r4_obs.json.

    from r4q import send
    send(rows, tag="R4_lhs", why="space-filling coverage of the full input box")
"""
import json
from bb import query, ROOT, FIELDS

OBS = ROOT / "data" / "r4_obs.json"
KEYS = list(FIELDS) + ["site"]


def load():
    return json.load(open(OBS, encoding="utf-8")) if OBS.exists() else []


def send(rows, tag, why):
    obs = load()
    for i in range(0, len(rows), 25):
        chunk = rows[i:i + 25]
        resp = query(chunk, tag=tag)
        qi0 = resp.get("query_index")
        for j, (r, o) in enumerate(zip(chunk, resp["outputs"])):
            obs.append({**{k: r[k] for k in KEYS}, "score": o["score"], "decision": o["decision"],
                        "query_index": (qi0 + j) if qi0 is not None else None, "tag": tag, "why": why})
        print(f"  sent {len(chunk)} | quota {resp['quota']}")
    json.dump(obs, open(OBS, "w", encoding="utf-8"), indent=1)
    return obs
