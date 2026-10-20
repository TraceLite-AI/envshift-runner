#!/usr/bin/env python3
"""Expand a cell-run plan into a job matrix.

Input (env PLAN): JSON list of cells, e.g.
  [{"task": "T1", "variant": "gh-cp1252", "cell": "base",   "modes": "ref,naive"},
   {"task": "T1", "variant": "gh-cp1252", "cell": "target", "modes": "ref,naive"},
   {"task": null, "variant": "gh-vm",     "cell": "target", "modes": "smoke", "cmd": "uname -a"}]
The runner of each variant (os, how, devices) is read from the matrix of sandbox-verify.yml, so the
two workflows cannot drift. The base cell always runs on ubuntu-24.04 (how=base).
Prints `matrix=<json>` for $GITHUB_OUTPUT.
"""
import json, os, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
ROW = re.compile(r'-\s*\{id:\s*([\w.-]+),\s*os:\s*([\w.-]+),\s*how:\s*(\w+)(?:,\s*devices:\s*"([^"]*)")?\s*\}')


def table():
    src = (HERE.parent / ".github" / "workflows" / "sandbox-verify.yml").read_text(encoding="utf-8")
    t = {m.group(1): {"os": m.group(2), "how": m.group(3), "devices": m.group(4) or ""} for m in ROW.finditer(src)}
    if len(t) < 21:
        sys.exit(f"plan: parsed only {len(t)} variants from sandbox-verify.yml")
    return t


def main():
    plan = json.loads(os.environ["PLAN"])
    t = table(); out = []
    for i, c in enumerate(plan):
        v = c["variant"]; cell = c.get("cell", "target")
        if v not in t:
            sys.exit(f"plan: unknown variant {v!r}")
        if cell == "base":
            row = {"os": "ubuntu-24.04", "how": "base", "devices": ""}
        elif cell == "target":
            row = dict(t[v])
        else:
            sys.exit(f"plan: cell must be base or target, got {cell!r}")
        task = c.get("task") or ""
        modes = c.get("modes", "ref,naive")
        out.append({"idx": i, "task": task, "variant": v, "cell": cell, "modes": modes, "cmd": c.get("cmd", ""),
                    "label": f"{task or 'smoke'} | {cell} | {v} | {row['how']}", **row})
    print("matrix=" + json.dumps(out, separators=(",", ":")))
    print(f"plan: {len(out)} cells", file=sys.stderr)


if __name__ == "__main__":
    main()
