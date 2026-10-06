"""Print logged queries for given tags as diffs vs the baseline (or vs the first row of each request)."""
import json, sys
from pathlib import Path
from bb import BASELINE, LOG

tags = sys.argv[1:]
for line in LOG.read_text(encoding="utf-8").splitlines():
    rec = json.loads(line)
    if tags and rec["tag"] not in tags:
        continue
    resp = rec["response"]
    print(rec["tag"], resp["request_id"], resp["quota"])
    for inp, o in zip(rec["inputs"], resp["outputs"]):
        d = {k: v for k, v in inp.items() if v != BASELINE[k]}
        print(f"  {o['score']:.4f} {o['decision']:8s} {d}")
