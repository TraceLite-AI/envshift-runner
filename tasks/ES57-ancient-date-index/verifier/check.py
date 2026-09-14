"""预期值只来自 ledger；不读 repo、tar 或磁盘属性计算真值。"""
import json, os, pathlib, subprocess, sys
PREFIX = 'ES57'
ROOT = pathlib.Path(os.environ.get(PREFIX + "_ROOT", "/data"))
BIN = os.environ.get(PREFIX + "_BIN", "/app/audit.py")
LOG = pathlib.Path(os.environ.get(PREFIX + "_LOG", "/logs/verifier"))
LIMIT = int(os.environ.get(PREFIX + "_TIME_LIMIT", "120"))
def main():
    LOG.mkdir(parents=True, exist_ok=True)
    checks = []
    def add(name, ok, points, detail=""):
        checks.append(dict(name=name, passed=bool(ok), points=points, detail=str(detail)[:300]))
    add("交付物存在", pathlib.Path(BIN).is_file(), 10)
    try:
        rows = [json.loads(l) for l in (ROOT / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        for group in (None, "alpha", "beta"):
            selected = [e for e in rows if group is None or e["group"] == group]
            want = dict(entries=len(selected), matched=sum(e["key"] == "%04d-%02d-%02d" % (e["year"], e["month"], e["day"]) for e in selected))
            for as_json in (False, True):
                flags = ([] if group is None else ["--group", group]) + (["--json"] if as_json else [])
                label = " ".join(flags) or "原有输出"
                ran = False
                try:
                    p = subprocess.run([sys.executable, BIN, str(ROOT), *flags], capture_output=True, timeout=LIMIT)
                    ran = True
                    add(label + " 正常结束", p.returncode == 0, 5, p.stderr[:160])
                    if as_json:
                        got = json.loads(p.stdout.decode("utf-8"))
                        ok = isinstance(got, dict) and got == want and all(type(v) is int for v in got.values())
                    else:
                        # 这些题不测 stdout 行尾；显式接受平台 LF/CRLF，不使用 strip 掩盖多余行。
                        expected = "entries,%d\nmatched,%d\n" % (want["entries"], want["matched"])
                        ok = p.stdout in (expected.encode("ascii"), expected.replace("\n", "\r\n").encode("ascii"))
                    add(label + " 业务结果", ok, 10, repr(p.stdout[:150]) + " expected=" + repr(want))
                except (OSError, subprocess.TimeoutExpired, ValueError, UnicodeError) as exc:
                    add(label + " 调用或协议失败", False, 10 if ran else 15, repr(exc))
    except Exception as exc:
        add("流水及判据可用", False, 90, repr(exc))
    points = sum(c["points"] for c in checks if c["passed"])
    total = sum(c["points"] for c in checks)
    reward = int(total > 0 and points == total)
    (LOG / "reward.txt").write_text(str(reward) + "\n", encoding="utf-8")
    (LOG / "trace_results.json").write_text(json.dumps(dict(reward=reward, points=points, total=total, checks=checks), ensure_ascii=False, indent=2), encoding="utf-8")
    for c in checks:
        if not c["passed"]:
            print("VERIFIER " + c["name"] + ": " + c["detail"], file=sys.stderr)
    sys.exit(0 if reward else 1)
if __name__ == "__main__":
    main()
