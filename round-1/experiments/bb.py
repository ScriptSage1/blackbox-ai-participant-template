"""Thin wrapper over the official client (code/blackbox.py) for GK-05.

Sign-in happens once, by the user, via code/login.py -> writes token.txt in the
project root. This module only resumes that saved session (no password here).
Every query row is appended to data/queries.jsonl with the request_id.
"""
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blackbox import Blackbox  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://192.168.18.219:8000"
TEAM = "BB-001"
TOKEN_FILE = ROOT / "token.txt"
LOG = ROOT / "data" / "queries.jsonl"

FIELDS = {  # name: (min, max)  -- from the portal's query console
    "anomaly_ratio": (0, 1),
    "badge_age_days": (18, 75),
    "clearance_level": (0, 100),
    "escorts": (0, 6),
    "history_score": (300, 900),
    "linked_badges": (0, 20),
    "recent_denials": (0, 5),
    "requested_zone": (0, 100),
    "tenure_years": (0, 40),
}
SITES = ["A", "B", "C", "D"]
BASELINE = {k: (lo + hi) / 2 for k, (lo, hi) in FIELDS.items()} | {"site": "A"}

_bb = None


def client():
    global _bb
    if _bb is None:
        # empty password: works only by resuming token.txt, never signs in itself
        _bb = Blackbox(BASE, TEAM, "", token_file=str(TOKEN_FILE))
    return _bb


def query(rows, tag=""):
    """Send up to 25 rows (dicts). Logs request + raw response. Returns raw response."""
    assert 1 <= len(rows) <= 25
    for r in rows:
        for k, (lo, hi) in FIELDS.items():
            assert lo <= r[k] <= hi, (k, r[k])
        assert r["site"] in SITES
    resp = client().query(rows)
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({"t": time.time(), "tag": tag, "inputs": rows, "response": resp}) + "\n")
    return resp


if __name__ == "__main__":
    c = client()
    print(json.dumps({"me": c.me(), "quota": c.quota(), "challenge": c.challenge()}, indent=1))
