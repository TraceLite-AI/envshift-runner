#!/usr/bin/env python3
"""Local dispatcher and collector for the cell-run workflow (env-suite two-cell runs on GitHub runners).

  # Gate 1 for some tasks (task dirs live outside this repo), plus executor smoke cells:
  python cell_dispatch.py dispatch --tasks-dir ~/Downloads/cl实验/envsuite/tasks_gh --tasks ID1,ID2 \
         --modes ref,naive --run gate1-gh --results ~/Downloads/cl实验/envsuite/results \
         [--smoke gh-kc-noloop,gh-wsl,gh-vm --cmd 'uname -a; echo $SHELL; python3 -V'] [--max-parallel 6]
  python cell_dispatch.py collect --run gate1-gh --results ~/Downloads/cl实验/envsuite/results --wait
  python cell_dispatch.py table   --run gate1-gh --results ~/Downloads/cl实验/envsuite/results

dispatch: packs the tasks (deterministic tar.gz -> base64), writes the TASKS_B64_1..12 secrets (unused chunks
          = UNUSED), waits until every secret reports the new updated_at and a settle delay has passed, prints the
          bundle fingerprint, dispatches cell-run.yml with that fingerprint and records results/<run>/dispatch.json.
          Refuses to start while another cell-run is queued or running (it would read the new bundle).
collect:  lists every job with `gh api .../jobs?per_page=100 --paginate`, reads the {"kind":"cell_result"} lines
          from each job log, rejects lines whose fingerprint differs from the dispatched one, and writes
          results/<run>/<task>/<cell>/<mode>/result.json (smoke: results/<run>/_smoke/<variant>/smoke/result.json).
          With ARTIFACT_PASS in the local environment it also decrypts the sealed artifacts and stores the full
          result.json (verify_out, solution_out, trace.jsonl in agent mode) in the same place.
"""
import argparse, base64, datetime, gzip, hashlib, io, json, os, pathlib, random, re, shutil, string, subprocess
import sys, tarfile, tempfile, time

REPO = os.environ.get("CELLRUN_REPO", "TraceLite-AI/envshift-runner")
WORKFLOW = "cell-run.yml"
NCHUNK, CHUNK = 12, 48000          # 12 secrets x 48 KB = the workflow's 12 chunk steps (~576 KB)
SKIP = {"__pycache__", ".DS_Store"}
UNUSED = "~unused-TASKS_B64-chunk~"     # GitHub masks secret values in logs: never a string that occurs in one


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def gh(args, input=None, check=True):
    p = subprocess.run(["gh"] + args, input=input, capture_output=True, text=True)
    if check and p.returncode:
        raise SystemExit("gh %s failed: %s" % (" ".join(args[:3]), p.stderr.strip()[-500:]))
    return p.stdout


def utcnow():
    return datetime.datetime.utcnow().replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------------------------------------ bundle
def build_bundle(tasks_dir, ids):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tf:
        for tid in ids:
            root = pathlib.Path(tasks_dir) / tid
            if not (root / "task.json").exists():
                raise SystemExit("no task.json in %s" % root)
            for p in sorted(root.rglob("*")):
                if any(part in SKIP for part in p.relative_to(root).parts) or not p.is_file():
                    continue
                ti = tarfile.TarInfo("tasks/%s/%s" % (tid, p.relative_to(root).as_posix()))
                data = p.read_bytes()
                ti.size = len(data); ti.mtime = 0; ti.uid = ti.gid = 0; ti.uname = ti.gname = ""
                ti.mode = 0o755 if os.access(str(p), os.X_OK) else 0o644
                tf.addfile(ti, io.BytesIO(data))
    b64 = base64.b64encode(gzip.compress(raw.getvalue(), 9, mtime=0)).decode()
    return b64, hashlib.sha256(b64.encode()).hexdigest()[:16]


def busy_runs():
    out = []
    for st in ("queued", "in_progress", "waiting", "pending"):
        js = gh(["run", "list", "-R", REPO, "-w", WORKFLOW, "-s", st, "-L", "20", "--json", "databaseId,displayTitle"], check=False)
        try: out += json.loads(js or "[]")
        except ValueError: pass
    return out


def push_bundle(b64, settle):
    chunks = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    if len(chunks) > NCHUNK:
        raise SystemExit("bundle is %d chars: more than %d chunks of %d" % (len(b64), NCHUNK, CHUNK))
    t0 = utcnow()
    time.sleep(1)
    for i in range(NCHUNK):
        val = chunks[i] if i < len(chunks) else UNUSED
        gh(["secret", "set", "TASKS_B64_%d" % (i + 1), "-R", REPO], input=val)
    log("secrets written: %d data chunks + %d empty, waiting until visible" % (len(chunks), NCHUNK - len(chunks)))
    for _ in range(60):
        stamps = [gh(["api", "repos/%s/actions/secrets/TASKS_B64_%d" % (REPO, i + 1), "--jq", ".updated_at"]).strip()
                  for i in range(NCHUNK)]
        if all(s >= t0 for s in stamps):
            break
        time.sleep(5)
    else:
        raise SystemExit("secrets did not report the new updated_at in 5 minutes")
    log("all chunks report updated_at >= %s; settling %ds" % (t0, settle))
    time.sleep(settle)


# ------------------------------------------------------------------------------------------------ dispatch
def cmd_dispatch(a):
    ids = [t for t in (a.tasks or "").split(",") if t]
    plan, fp = [], ""
    rd = pathlib.Path(a.results).expanduser() / a.run
    if rd.exists() and (rd / "dispatch.json").exists() and not a.force:
        raise SystemExit("%s already has a dispatch.json; pick another --run or pass --force" % rd)
    if ids:
        b64, fp = build_bundle(pathlib.Path(a.tasks_dir).expanduser(), ids)
        log("bundle: %d tasks, %d base64 chars, fingerprint %s" % (len(ids), len(b64), fp))
        for tid in ids:
            t = json.loads((pathlib.Path(a.tasks_dir).expanduser() / tid / "task.json").read_text(encoding="utf-8"))
            for cell in a.cells.split(","):
                plan.append({"task": tid, "variant": t["cells"]["target"]["sandbox"], "cell": cell, "modes": a.modes})
    for v in [v for v in (a.smoke or "").split(",") if v]:
        plan.append({"task": None, "variant": v, "cell": "target", "modes": "smoke", "cmd": a.cmd})
    if not plan:
        raise SystemExit("nothing to run")
    busy = busy_runs()
    if busy and not a.force:
        raise SystemExit("another cell-run is queued or running (%s); it would read the new bundle" % busy)
    if ids:
        push_bundle(b64, a.settle)
    tag = "%s-%s" % (a.run, "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6)))
    print("BUNDLE_FP=%s" % (fp or "none"), flush=True)
    gh(["workflow", "run", WORKFLOW, "-R", REPO, "--ref", a.ref, "-f", "plan=" + json.dumps(plan),
        "-f", "fp=" + fp, "-f", "tag=" + tag, "-f", "model=" + a.model, "-f", "max_parallel=%d" % a.max_parallel,
        "-f", "public_tail=" + ("1" if a.public_tail else "0")])
    run_id = None
    for _ in range(40):
        time.sleep(5)
        runs = json.loads(gh(["run", "list", "-R", REPO, "-w", WORKFLOW, "-L", "20", "--json", "databaseId,displayTitle"]))
        hit = [r for r in runs if r["displayTitle"] == "cell-run " + tag]
        if hit:
            run_id = hit[0]["databaseId"]; break
    if not run_id:
        raise SystemExit("dispatched, but no run named 'cell-run %s' appeared" % tag)
    rd.mkdir(parents=True, exist_ok=True)
    rec = {"run": a.run, "run_id": run_id, "tag": tag, "fp": fp, "tasks": ids, "plan": plan, "repo": REPO, "model": a.model,
           "dispatched_at": utcnow(), "url": "https://github.com/%s/actions/runs/%s" % (REPO, run_id)}
    (rd / "dispatch.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    print("RUN_ID=%s %s" % (run_id, rec["url"]), flush=True)


# ------------------------------------------------------------------------------------------------ collect
LINE = re.compile(r'(\{"kind": "cell_result".*\})\s*$')


def result_key(r, sub):
    return (r.get("task"), r.get("cell"), sub, r.get("variant") if r.get("mode") == "smoke" else None)


def jobs_of(run_id):
    out = gh(["api", "repos/%s/actions/runs/%s/jobs?per_page=100" % (REPO, run_id), "--paginate", "--jq", ".jobs[] | tojson"])
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def decrypt_artifacts(run_id, rd, accepted):
    pw = os.environ.get("ARTIFACT_PASS")
    if not pw:
        log("ARTIFACT_PASS not in the local environment: keeping the log-line results only")
        return 0
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="cellrun-art-"))
    n = 0
    try:
        gh(["run", "download", str(run_id), "-R", REPO, "-D", str(tmp)], check=False)
        for enc in tmp.rglob("out.tgz.enc"):
            tgz = enc.with_suffix("")
            p = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:ARTIFACT_PASS",
                                "-in", str(enc), "-out", str(tgz)], capture_output=True)
            if p.returncode:
                log("cannot decrypt %s" % enc); continue
            with tarfile.open(str(tgz)) as tf:
                tf.extractall(str(enc.parent / "x"))
            for res in (enc.parent / "x" / "out").rglob("result.json"):
                full = json.loads(res.read_text(encoding="utf-8"))
                key = result_key(full, res.parent.name)
                if key not in accepted:
                    continue
                dst = accepted[key]
                merged = dict(full); merged.update({k: v for k, v in json.loads(dst.read_text(encoding="utf-8")).items()
                                                    if k.startswith("job_") or k in ("collected_at", "accepted")})
                dst.write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding="utf-8")
                for extra in res.parent.iterdir():
                    if extra.name != "result.json":
                        t = dst.parent / extra.name
                        if extra.is_dir(): shutil.copytree(str(extra), str(t), dirs_exist_ok=True)
                        else: shutil.copy2(str(extra), str(t))
                n += 1
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    return n


def cmd_collect(a):
    rd = pathlib.Path(a.results).expanduser() / a.run
    rec = json.loads((rd / "dispatch.json").read_text(encoding="utf-8"))
    run_id = a.run_id or rec["run_id"]; want_fp = rec["fp"] or "none"
    if a.wait:
        while True:
            st = json.loads(gh(["run", "view", str(run_id), "-R", REPO, "--json", "status,conclusion"]))
            if st["status"] == "completed": break
            log("run %s: %s; next check in %ds" % (run_id, st["status"], a.poll)); time.sleep(a.poll)
    jobs = jobs_of(run_id)
    summary, accepted, rejected = [], {}, []
    for j in jobs:
        if j["name"] == "plan":
            continue
        txt = gh(["api", "repos/%s/actions/jobs/%s/logs" % (REPO, j["id"])], check=False)
        fps = sorted(set(re.findall(r"BUNDLE_FP=([0-9a-f]{16}|none)", txt)))
        lines = []
        for l in txt.splitlines():
            m = LINE.search(l)
            if m:
                try: lines.append(json.loads(m.group(1)))
                except ValueError: pass
        summary.append({"job_id": j["id"], "name": j["name"], "conclusion": j["conclusion"], "results": len(lines), "bundle_fp": fps})
        for r in lines:
            r.update(job_id=j["id"], job_name=j["name"], job_conclusion=j["conclusion"], collected_at=utcnow())
            if r.get("mode") == "smoke":
                dst = rd / "_smoke" / r.get("variant", "unknown") / "smoke" / "result.json"
            else:
                if r.get("fp") != want_fp:
                    rejected.append({"job": j["name"], "fp": r.get("fp"), "want": want_fp, "task": r.get("task"), "mode": r.get("mode")})
                    continue
                sub = r["mode"] if r["mode"] != "agent" else "agent-%s" % rec.get("model", "model")
                dst = rd / r["task"] / r["cell"] / sub / "result.json"
            dst.parent.mkdir(parents=True, exist_ok=True)
            r["accepted"] = True
            dst.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
            accepted[result_key(r, dst.parent.name)] = dst
        if not lines:
            tail = [l[29:] if len(l) > 29 else l for l in txt.splitlines()[-25:]]
            (rd / "_jobs").mkdir(exist_ok=True)
            (rd / "_jobs" / ("%s.tail.txt" % j["id"])).write_text("\n".join(tail), encoding="utf-8")
    full = decrypt_artifacts(run_id, rd, accepted)
    (rd / "_jobs.json").write_text(json.dumps({"run_id": run_id, "fp": want_fp, "jobs": summary, "rejected": rejected,
                                              "full_results": full}, indent=1, ensure_ascii=False), encoding="utf-8")
    log("collected %d result lines from %d jobs; rejected %d (fingerprint); full results merged: %d"
        % (len(accepted), len(summary), len(rejected), full))
    if rejected:
        log("REJECTED (stale bundle): %s" % rejected)
    cmd_table(a)


def cmd_table(a):
    rd = pathlib.Path(a.results).expanduser() / a.run
    rec = json.loads((rd / "dispatch.json").read_text(encoding="utf-8"))
    def cell(t, c, m):
        p = rd / t / c / m / "result.json"
        if not p.exists(): return "-"
        r = json.loads(p.read_text(encoding="utf-8"))
        return "E" if r.get("invalid") or r.get("pass") is None else ("P" if r["pass"] else "F")
    print("| task | variant | ref base | ref target | naive base | naive target | gate 1 | run id |")
    print("|---|---|---|---|---|---|---|---|")
    for tid in rec["tasks"]:
        v = next(p["variant"] for p in rec["plan"] if p["task"] == tid)
        rb, rt, nb, nt = cell(tid, "base", "ref"), cell(tid, "target", "ref"), cell(tid, "base", "naive"), cell(tid, "target", "naive")
        ok = "PASS" if (rb, rt, nb, nt) == ("P", "P", "P", "F") else "FAIL"
        print("| %s | %s | %s | %s | %s | %s | %s | %s |" % (tid, v, rb, rt, nb, nt, ok, rec["run_id"]))
    sm = sorted((rd / "_smoke").glob("*/smoke/result.json")) if (rd / "_smoke").exists() else []
    for p in sm:
        r = json.loads(p.read_text(encoding="utf-8"))
        print("smoke %-14s how=%-8s rc=%s | %s" % (r.get("variant"), r.get("how"), r.get("smoke_rc"),
                                                (r.get("smoke_out") or r.get("error") or "").strip().replace("\n", " / ")[:300]))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="action")
    d = sp.add_parser("dispatch")
    d.add_argument("--tasks-dir", default="~/Downloads/cl实验/envsuite/tasks_gh"); d.add_argument("--tasks", default="")
    d.add_argument("--cells", default="base,target"); d.add_argument("--modes", default="ref,naive")
    d.add_argument("--smoke", default=""); d.add_argument("--cmd", default="uname -a; echo $SHELL; python3 -V")
    d.add_argument("--run", required=True); d.add_argument("--results", default="~/Downloads/cl实验/envsuite/results")
    d.add_argument("--model", default="deepseek-v4.1-flash"); d.add_argument("--max-parallel", type=int, default=6)
    d.add_argument("--ref", default="main"); d.add_argument("--settle", type=int, default=45)
    d.add_argument("--force", action="store_true")
    d.add_argument("--public-tail", action="store_true",
                   help="also print the verifier's last line and error text in the public job log (judge data; off by default)")
    for name in ("collect", "table"):
        c = sp.add_parser(name)
        c.add_argument("--run", required=True); c.add_argument("--results", default="~/Downloads/cl实验/envsuite/results")
        c.add_argument("--run-id", default=None); c.add_argument("--wait", action="store_true"); c.add_argument("--poll", type=int, default=60)
    a = ap.parse_args()
    if a.action == "dispatch": cmd_dispatch(a)
    elif a.action == "collect": cmd_collect(a)
    elif a.action == "table": cmd_table(a)
    else: ap.print_help()


if __name__ == "__main__":
    main()
