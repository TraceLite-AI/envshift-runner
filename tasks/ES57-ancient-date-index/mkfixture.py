import json, os, pathlib, sys
import datetime

root = pathlib.Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
rows = []
for i, (y, m, d) in enumerate([(1,3,4),(99,3,4),(875,3,4),(1900,3,4),(2024,2,29),(7,12,31),(999,1,1)], 1):
    rows.append(dict(seq=i, name="record%02d" % i, group="alpha" if i % 2 else "beta", year=y, month=m, day=d, key="%04d-%02d-%02d" % (y,m,d)))

(root / "ledger.jsonl").write_bytes(("\n".join(json.dumps(e, ensure_ascii=True) for e in rows) + "\n").encode("utf-8"))
app = pathlib.Path(os.environ.get("ES57_APP", "/app"))
app.mkdir(parents=True, exist_ok=True)
(app / "audit.py").write_bytes(b'import argparse, json, pathlib, sys\nimport datetime\n\ndef collect(root):\n    rows = [json.loads(line) for line in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]\n    dates = {e["name"]: datetime.date(e["year"], e["month"], e["day"]) for e in rows}\n    return [(e, dates[e["name"]].strftime("%Y-%m-%d") == e["key"]) for e in rows]\n\nif __name__ == "__main__":\n    items = collect(pathlib.Path(sys.argv[1]))\n    print("entries,%d" % len(items))\n    print("matched,%d" % sum(ok for e, ok in items))\n')
