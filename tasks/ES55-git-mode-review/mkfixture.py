import json, os, pathlib, sys
import os, shutil, subprocess
def git(repo, *args):
    return subprocess.run([shutil.which("git") or "git", *args], cwd=repo, check=True, capture_output=True, timeout=60).stdout

root = pathlib.Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
repo = root / "repo"
repo.mkdir()
git(repo, "init", "-q")
git(repo, "config", "user.name", "fixture")
git(repo, "config", "user.email", "fixture@example.com")
rows = []
for i in range(1, 8):
    name = "script%02d.sh" % i
    (repo / name).write_bytes(b"#!/bin/sh\nexit 0\n")
    os.chmod(repo / name, 0o644)
    rows.append(dict(seq=i, name=name, group="alpha" if i % 2 else "beta", mode="100755" if i % 3 else "100644", changed=bool(i % 3)))
git(repo, "add", ".")
# 固定提交的业务起点，不改 core.fileMode 或其他宿主差异。
git(repo, "update-index", "--chmod=-x", "--", *[e["name"] for e in rows])
git(repo, "-c", "core.hooksPath=", "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
for e in rows:
    os.chmod(repo / e["name"], 0o755 if e["changed"] else 0o644)

(root / "ledger.jsonl").write_bytes(("\n".join(json.dumps(e, ensure_ascii=True) for e in rows) + "\n").encode("utf-8"))
app = pathlib.Path(os.environ.get("ES55_APP", "/app"))
app.mkdir(parents=True, exist_ok=True)
(app / "audit.py").write_bytes(b'import argparse, json, pathlib, sys\nimport os, shutil, subprocess\ndef git(repo, *args):\n    return subprocess.run([shutil.which("git") or "git", *args], cwd=repo, check=True, capture_output=True, timeout=60).stdout\n\ndef collect(root):\n    rows = [json.loads(line) for line in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]\n    repo = root / "repo"\n    tracked = {line.split("\\t", 1)[1]: line.split()[0] for line in git(repo, "ls-files", "--stage").decode("utf-8").splitlines()}\n    status_names = {line[3:] for line in git(repo, "status", "--porcelain").decode("utf-8").splitlines()}\n    return [(e, e["name"] in status_names) for e in rows]\n\nif __name__ == "__main__":\n    items = collect(pathlib.Path(sys.argv[1]))\n    print("entries,%d" % len(items))\n    print("matched,%d" % sum(ok for e, ok in items))\n')
