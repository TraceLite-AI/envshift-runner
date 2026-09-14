import json, os, pathlib, sys
import getpass, tarfile

root = pathlib.Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
producer = getpass.getuser()
rows = []
files = root / "files"
files.mkdir()
with tarfile.open(root / "delivery.tar", "w", format=tarfile.PAX_FORMAT) as tf:
    for i in range(1, 8):
        name = "receipt%02d.txt" % i
        f = files / name
        f.write_bytes(("receipt %d\n" % i).encode("ascii"))
        def stamp(member):
            member.pax_headers["EnvShift.producer"] = producer
            return member
        tf.add(f, arcname=name, filter=stamp)
        rows.append(dict(seq=i, name=name, group="alpha" if i % 2 else "beta", producer=producer))

(root / "ledger.jsonl").write_bytes(("\n".join(json.dumps(e, ensure_ascii=True) for e in rows) + "\n").encode("utf-8"))
app = pathlib.Path(os.environ.get("ES56_APP", "/app"))
app.mkdir(parents=True, exist_ok=True)
(app / "audit.py").write_bytes(b'import argparse, json, pathlib, sys\nimport getpass, tarfile\n\ndef collect(root):\n    rows = [json.loads(line) for line in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]\n    with tarfile.open(root / "delivery.tar", "r") as tf:\n        members = {m.name: m for m in tf.getmembers()}\n    return [(e, members[e["name"]].uname == e["producer"]) for e in rows]\n\nif __name__ == "__main__":\n    items = collect(pathlib.Path(sys.argv[1]))\n    print("entries,%d" % len(items))\n    print("matched,%d" % sum(ok for e, ok in items))\n')
