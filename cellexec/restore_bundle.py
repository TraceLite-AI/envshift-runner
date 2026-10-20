#!/usr/bin/env python3
"""Check the task bundle restored from the TASKS_B64_* secret chunks.

The chunk steps append each secret to tasks_b64.txt one per step (macOS: 1 MB env+args limit). Unused chunks
hold UNUSED and are dropped here (GitHub masks secret values in logs, so the sentinel must never occur in a log).
Prints BUNDLE_FP=<sha256 prefix> and exits 3 when it differs from the fingerprint the dispatcher expects (a
secret set just before dispatch may not be visible yet).
The bundle stays base64 on disk; cell_run.py decodes it in memory. No task content is printed.
"""
import base64, hashlib, io, os, pathlib, sys, tarfile


UNUSED = "~unused-TASKS_B64-chunk~"


def fingerprint(b64):
    return hashlib.sha256(b64.encode()).hexdigest()[:16]


def load(path="tasks_b64.txt"):
    p = pathlib.Path(path)
    b64 = p.read_text(encoding="ascii").replace(UNUSED, "").strip() if p.exists() else ""
    return b64


def main():
    b64 = load()
    want = os.environ.get("CELL_FP", "").strip()
    if not b64:
        print("BUNDLE_FP=none")
        sys.exit(3 if want else 0)
    fp = fingerprint(b64)
    print(f"BUNDLE_FP={fp}")
    if want and fp != want:
        print(f"stale bundle: restored {fp}, dispatcher expected {want}", file=sys.stderr)
        sys.exit(3)
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(b64)), mode="r:gz") as tf:
        ids = sorted({n.split("/")[1] for n in tf.getnames() if n.startswith("tasks/") and n.count("/") >= 2})
    print(f"bundle: {len(ids)} tasks, {len(b64)} base64 chars", file=sys.stderr)


if __name__ == "__main__":
    main()
