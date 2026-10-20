#!/usr/bin/env python3
"""Runner-side task executor for env-suite two-cell runs on GitHub-hosted runners.

  python cell_run.py --task ID --cell base|target --variant gh-xxx --how HOW --mode ref|naive|agent|smoke
                     [--bundle tasks_b64.txt] [--out out] [--model M] [--cmd "..."]

One invocation runs one task in one cell for each listed mode (comma list allowed; agent always last) and prints
exactly ONE JSON line per mode on stdout ({"kind": "cell_result", ...}). Everything else goes to stderr.
The full result.json (and trace.jsonl in agent mode) is written under <out>/<task>/<cell>/<mode>/ and is sealed
by the workflow before upload; the stdout line carries only the fields Gate 1 needs.

Cells (mirrors the Docker side, ~/Downloads/cl实验/envsuite/suite_runner.py + sandbox/sbx.py):
  base       ubuntu-24.04, actions/setup-python 3.12, LANG=C.UTF-8, TZ=UTC, bash, workspace /workspace
  target     the variant's runner (sandbox-verify.yml matrix) and its executor ("how"):
             plain bash | pwsh | ps5 (Windows PowerShell 5.1) | cmd | winnative (pwsh, native-toolchain PATH)
             | docker (device subset) | wsl | vm (ssh into a QEMU/KVM guest) | microvm (ssh into Firecracker)
             | android (adb shell)
Every command -- setup, solution, the agent's bash tool and the verifier -- runs through the cell's executor.

Task layout (bundle member tasks/<ID>/): task.json, workspace/, setup.*, judge/, verify.*, solution/<mode>.*
The runnable file for each role is picked by the executor's shell family: bash -> .sh then .py; pwsh -> .ps1
then .py; cmd -> .cmd/.bat then .py; sh (Android) -> .sh. A .py file runs with the cell's own python.
Runtime env for setup/verify: CELL, WORKSPACE, STAGE (judge/ is staged at $STAGE/judge only at verify time).
"""
import argparse, base64, hashlib, io, json, os, pathlib, platform, shlex, shutil, signal, stat, subprocess, sys
import tarfile, tempfile, time, urllib.error, urllib.request, uuid

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "cellexec"))
import anthropic_native  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

WIN = os.name == "nt"
MAC = sys.platform == "darwin"

# Secrets and runner plumbing never reach a cell. Python mode switches are removed too: the cell decides
# its own text encoding (gh-cp1252 is exactly that property).
SECRET_KEYS = {"LLMGATEWAY_API_KEY", "ENVSHIFT_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "ZHIPU_API_KEY",
               "COMPUTRIX_API_KEY", "ARTIFACT_PASS", "GITHUB_TOKEN", "GH_TOKEN", "TB", "ACTIONS_RUNTIME_TOKEN",
               "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_URL", "ACTIONS_RESULTS_URL",
               "ACTIONS_RUNTIME_URL", "ACTIONS_CACHE_URL"}
SCRUB_KEYS = {"PYTHONUTF8", "PYTHONIOENCODING", "PYTHONLEGACYWINDOWSSTDIO", "PYTHONPATH", "PYTHONHOME", "CELL_FP"}
API = {k: os.environ.pop(k, "") for k in ("LLMGATEWAY_API_KEY", "ANTHROPIC_API_KEY")}
for _k in list(os.environ):
    if _k in SECRET_KEYS or _k.startswith("TASKS_B64"):
        os.environ.pop(_k, None)
if API["ANTHROPIC_API_KEY"]:
    os.environ["ANTHROPIC_API_KEY"] = API["ANTHROPIC_API_KEY"]   # read by anthropic_native; scrubbed from cells
BASE_ENV = {"API_TOKEN": "tl-demo-secret-0001"}                 # sandbox/variants.py BASE["env"]
LINUX_ENV = {"LANG": "C.UTF-8", "TZ": "UTC", "SHELL": "/bin/bash"}

API_URL = os.environ.get("LLMGATEWAY_API_URL", "https://api.llmgateway.io/v1").rstrip("/")
SYSTEM_PROMPT = ("You are an autonomous software agent working inside a {os} machine. Use the bash tool to run shell "
                 "commands. Your working directory is {ws}. Work until the task is fully done, then call the finish "
                 "tool with a short summary.")
TOOLS = [
    {"type": "function", "function": {"name": "bash", "description": "Run a shell command and return its combined stdout/stderr and exit code.",
     "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "finish", "description": "Call when the task is complete.",
     "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
]


def log(*a):
    print("[cell_run]", *a, file=sys.stderr, flush=True)


def truncate(s, n=30000):
    return s if len(s) <= n else s[:n // 2] + f"\n\n[... {len(s) - n} characters omitted ...]\n\n" + s[-n // 2:]


def decode(b, fallback="utf-8"):
    if b[:200].count(b"\x00") > 20:          # wsl.exe prints its own messages in UTF-16
        try: return b.decode("utf-16-le")
        except UnicodeDecodeError: pass
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode(fallback, "replace")


def scrubbed_env():
    return {k: v for k, v in os.environ.items() if k not in SECRET_KEYS and k not in SCRUB_KEYS
            and not k.startswith(("TASKS_B64", "CELL_", "LLMGATEWAY", "ANTHROPIC", "REASONING_"))}


def rmtree(p):
    p = str(p)
    if not os.path.lexists(p):
        return
    if WIN and not p.startswith("\\\\?\\"):
        p = "\\\\?\\" + os.path.abspath(p)       # reach names Win32 normalisation would hide (con.rec, "a.")
    def onerr(fn, path, exc):
        try: os.chmod(path, os.lstat(path).st_mode | stat.S_IWRITE); fn(path)
        except Exception: pass
    if os.path.isdir(p) and not os.path.islink(p):
        shutil.rmtree(p, onerror=onerr)
    else:
        os.unlink(p)


def empty_dir(path):
    """Create a directory or remove everything inside it (the directory itself stays: /workspace's parent is
    root-owned on the runner)."""
    os.makedirs(path, exist_ok=True)
    for c in os.listdir(path):
        rmtree(os.path.join(path, c))


def run_proc(args, timeout, env=None, cwd=None, input=None):
    """Run a process, capture combined output as bytes, kill the whole tree on timeout.
    Returns (rc, bytes, timed_out)."""
    kw = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "env": env, "cwd": cwd,
          "stdin": subprocess.PIPE if input is not None else subprocess.DEVNULL}
    if WIN: kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else: kw["start_new_session"] = True
    p = subprocess.Popen(args, **kw)
    try:
        out, _ = p.communicate(input=input, timeout=timeout)
        return p.returncode, out or b"", False
    except subprocess.TimeoutExpired:
        if WIN:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            try: os.killpg(p.pid, signal.SIGKILL)
            except Exception: p.kill()
        try: out, _ = p.communicate(timeout=20)
        except Exception: out = b""
        return None, out or b"", True


# ----------------------------------------------------------------------------------------------- executors
class Executor:
    family = "bash"          # bash | sh | pwsh | cmd : which shell interprets commands
    os_name = "Linux"
    python = "python3"       # the cell's own python
    remote = False

    def __init__(self, cell, variant, extra_env):
        self.cell, self.variant = cell, variant
        self.env = dict(extra_env)          # cell-level variables on top of what the executor provides
        rt = os.environ.get("RUNNER_TEMP")
        self.tmp = pathlib.Path(os.path.realpath(tempfile.mkdtemp(prefix="cellrun-", dir=rt if rt and os.path.isdir(rt) else None)))

    # paths inside the cell
    def join(self, *parts):
        return "/".join(parts)

    def start(self):
        pass

    def stop(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def reset(self, path):
        """Empty (or create) a directory inside the cell."""
        raise NotImplementedError

    def push(self, local_dir, remote_dir):
        """Copy the contents of a local directory into a cell directory (created if needed)."""
        raise NotImplementedError

    def pull_file(self, remote_path):
        return None

    def run(self, cmd, timeout=180, cwd=None, env=None):
        """Run one command text in the cell's shell. Returns (rc, text, timed_out)."""
        raise NotImplementedError

    # how to run a file of a given kind
    def file_cmd(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".py":
            return {"pwsh": f"& {self.python} '{path}'", "cmd": f'{self.python} "{path}"'}.get(self.family, f"{self.python} {shlex.quote(path)}")
        if ext == ".ps1": return f"& '{path}'"
        if ext in (".cmd", ".bat"): return f'call "{path}"'
        if ext == ".sh": return ("sh " if self.family == "sh" else "bash ") + shlex.quote(path)
        raise ValueError(f"cannot run {path} in a {self.family} cell")

    def exts(self):
        return {"bash": [".sh", ".py"], "sh": [".sh"], "pwsh": [".ps1", ".py"], "cmd": [".cmd", ".bat", ".py"]}[self.family]


def _bash_script(cmd, cwd, env):
    lines = ["#!/bin/bash"] + [f"export {k}={shlex.quote(str(v))}" for k, v in (env or {}).items()]
    if cwd: lines.append(f"cd {shlex.quote(cwd)} || exit 125")
    return "\n".join(lines) + "\n" + cmd + "\n"


class LocalBash(Executor):
    """base cell, and plain targets (macOS, Linux, arm64): bash on the runner itself."""

    def __init__(self, cell, variant, extra_env):
        super().__init__(cell, variant, extra_env)
        self.os_name = "macOS" if MAC else "Linux"
        home = os.path.expanduser("~")
        if MAC:
            self.ws, self.stage = os.path.join(home, "workspace"), os.path.join(home, "stage")
        else:     # the Docker sandbox paths; the runner user owns them
            subprocess.run(["sudo", "mkdir", "-p", "/workspace", "/opt/stage"], capture_output=True)
            subprocess.run(["sudo", "chown", f"{os.getuid()}:{os.getgid()}", "/workspace", "/opt/stage"], capture_output=True)
            ok = os.access("/workspace", os.W_OK) and os.access("/opt/stage", os.W_OK)
            self.ws, self.stage = ("/workspace", "/opt/stage") if ok else (os.path.join(home, "workspace"), os.path.join(home, "stage"))
        if os.environ.get("CELL_LOCAL_ROOT"):    # local testing: keep the cell out of $HOME
            self.ws, self.stage = (os.path.join(os.environ["CELL_LOCAL_ROOT"], d) for d in ("workspace", "stage"))
        self.bash = "/bin/bash" if os.path.exists("/bin/bash") else shutil.which("bash")
        base = scrubbed_env()
        if cell == "base" or not MAC:
            for k in [k for k in base if k.startswith("LC_")]: base.pop(k)
            base.update(LINUX_ENV)
        else:
            base["SHELL"] = "/bin/bash"
        base.update(BASE_ENV); base.update(self.env)
        self.base_env = base

    def reset(self, path):
        empty_dir(path)

    def push(self, local_dir, remote_dir):
        os.makedirs(remote_dir, exist_ok=True)
        shutil.copytree(local_dir, remote_dir, dirs_exist_ok=True, symlinks=True)

    def pull_file(self, remote_path):
        try: return open(remote_path, "rb").read()
        except OSError: return None

    def run(self, cmd, timeout=180, cwd=None, env=None):
        f = self.tmp / f"cmd-{uuid.uuid4().hex[:8]}.sh"
        with open(f, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_bash_script(cmd, cwd or self.ws, None))
        e = dict(self.base_env); e.update(env or {})
        rc, out, to = run_proc([self.bash, str(f)], timeout, env=e)
        f.unlink(missing_ok=True)
        return rc, decode(out), to


class LocalWindows(Executor):
    """Windows targets: pwsh (PowerShell 7), ps5 (Windows PowerShell 5.1), cmd, winnative (pwsh with the
    native-toolchain PATH from sandbox_gh.py). Scripts are written to files and the file is run."""
    os_name = "Windows"
    python = "python"

    def __init__(self, cell, variant, extra_env, how):
        super().__init__(cell, variant, extra_env)
        self.how = how
        self.family = "cmd" if how == "cmd" else "pwsh"
        self.ws, self.stage = r"C:\workspace", r"C:\stage"
        if os.environ.get("CELL_LOCAL_ROOT"):
            self.ws, self.stage = (os.path.join(os.environ["CELL_LOCAL_ROOT"], d) for d in ("workspace", "stage"))
        base = scrubbed_env()
        if how == "ps5":
            self.shell = [os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")]
        elif how == "cmd":
            self.shell = [os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "cmd.exe")]
            for k in [k for k in base if k.upper() == "PSMODULEPATH"]:   # as in sandbox-verify: a plain cmd session
                base.pop(k)
        else:
            self.shell = [shutil.which("pwsh") or r"C:\Program Files\PowerShell\7\pwsh.exe"]
        if how == "winnative":
            sp = os.environ.get("SANDBOX_PATH")
            if not sp: raise RuntimeError("winnative: SANDBOX_PATH not set (sandbox_gh.py setup gh-winnative)")
            for k in [k for k in base if k.upper() == "PATH"]: base.pop(k)
            base["PATH"] = sp
        base.update(BASE_ENV); base.update(self.env)
        self.base_env = base
        import ctypes
        self.fallback = f"cp{ctypes.windll.kernel32.GetOEMCP()}"

    def join(self, *parts):
        return "\\".join(parts)

    def reset(self, path):
        empty_dir(path)

    def push(self, local_dir, remote_dir):
        os.makedirs(remote_dir, exist_ok=True)
        shutil.copytree(local_dir, remote_dir, dirs_exist_ok=True)

    def pull_file(self, remote_path):
        try: return open(remote_path, "rb").read()
        except OSError: return None

    def run(self, cmd, timeout=180, cwd=None, env=None):
        cwd = cwd or self.ws
        if self.family == "cmd":
            f = self.tmp / f"cmd-{uuid.uuid4().hex[:8]}.cmd"
            body = f'@echo off\r\ncd /d "{cwd}"\r\n' + cmd.replace("\r\n", "\n").replace("\n", "\r\n") + "\r\nexit /b %ERRORLEVEL%\r\n"
            with open(f, "w", encoding="utf-8", newline="") as fh: fh.write(body)
            args = self.shell + ["/d", "/c", str(f)]
        else:
            f = self.tmp / f"cmd-{uuid.uuid4().hex[:8]}.ps1"
            body = ("$global:LASTEXITCODE = 0\n" f"Set-Location -LiteralPath '{cwd}'\n" + cmd + "\n"
                    "if (-not $?) { if ($LASTEXITCODE) { exit $LASTEXITCODE } else { exit 1 } }\nexit $LASTEXITCODE\n")
            with open(f, "w", encoding="utf-8-sig", newline="\n") as fh: fh.write(body)   # BOM: PS 5.1 reads ANSI otherwise
            args = self.shell + ["-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(f)]
        e = dict(self.base_env); e.update(env or {})
        rc, out, to = run_proc(args, timeout, env=e)
        f.unlink(missing_ok=True)
        return rc, decode(out, self.fallback), to


class Docker(Executor):
    """gh-kc-*: a Linux container with a device subset (sandbox-verify: python:3.12-slim + --device flags)."""
    remote = True

    def __init__(self, cell, variant, extra_env):
        super().__init__(cell, variant, extra_env)
        self.ws, self.stage = "/workspace", "/opt/stage"
        self.image = os.environ.get("CELL_DOCKER_IMAGE", "python:3.12-slim")
        self.devices = shlex.split(os.environ.get("CELL_DEVICES", ""))
        self.name = f"cell-{uuid.uuid4().hex[:8]}"

    def start(self):
        env = dict(LINUX_ENV); env.update(BASE_ENV); env.update(self.env)
        args = ["docker", "run", "-d", "--init", "--name", self.name, "--hostname", "sandbox", "-w", "/workspace",
                "--memory", "4g", "--cpus", "2", "--pids-limit", "1024"] + self.devices
        for k, v in env.items(): args += ["-e", f"{k}={v}"]
        args += [self.image, "sleep", "infinity"]
        rc, out, _ = run_proc(args, 600)
        if rc: raise RuntimeError("docker run failed: " + decode(out)[-800:])
        run_proc(["docker", "exec", self.name, "mkdir", "-p", self.ws, self.stage], 60)

    def stop(self):
        run_proc(["docker", "rm", "-f", "-v", self.name], 120); super().stop()

    def reset(self, path):
        run_proc(["docker", "exec", self.name, "sh", "-c", f"rm -rf {shlex.quote(path)} && mkdir -p {shlex.quote(path)}"], 120)

    def push(self, local_dir, remote_dir):
        run_proc(["docker", "exec", self.name, "mkdir", "-p", remote_dir], 60)
        rc, out, _ = run_proc(["docker", "cp", str(local_dir).rstrip("/") + "/.", f"{self.name}:{remote_dir}"], 300)
        if rc: raise RuntimeError("docker cp: " + decode(out)[-300:])

    def pull_file(self, remote_path):
        rc, out, _ = run_proc(["docker", "exec", self.name, "cat", remote_path], 60)
        return out if rc == 0 else None

    def run(self, cmd, timeout=180, cwd=None, env=None):
        f = self.tmp / "cmd.sh"
        with open(f, "w", encoding="utf-8", newline="\n") as fh: fh.write(_bash_script(cmd, cwd or self.ws, env))
        run_proc(["docker", "cp", str(f), f"{self.name}:/tmp/_cell_cmd.sh"], 60)
        rc, out, to = run_proc(["docker", "exec", self.name, "timeout", "-k", "5", str(int(timeout)), "bash", "/tmp/_cell_cmd.sh"], timeout + 30)
        if rc == 124: to = True
        return rc, decode(out), to


class WSL(Executor):
    """gh-wsl: commands run inside the WSL distribution (Vampire/setup-wsl). The workspace lives on the WSL
    filesystem; files cross over through /mnt/<drive>. Every command is a script file run with wsl.exe -e."""
    remote = True

    def __init__(self, cell, variant, extra_env):
        super().__init__(cell, variant, extra_env)
        self.distro = os.environ.get("CELL_WSL_DISTRO")    # default: the distribution setup-wsl set as default
        self.ws, self.stage = "/workspace", "/opt/stage"
        self.wsl = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "wsl.exe")

    @staticmethod
    def mnt(p):
        p = os.path.abspath(str(p))
        return "/mnt/" + p[0].lower() + p[2:].replace("\\", "/")

    def _sh(self, script, timeout):
        f = self.tmp / f"w-{uuid.uuid4().hex[:8]}.sh"
        with open(f, "w", encoding="utf-8", newline="\n") as fh: fh.write(script)
        rc, out, to = run_proc([self.wsl] + (["-d", self.distro] if self.distro else []) + ["-u", "root", "-e", "timeout", "-k", "5",
                                str(int(timeout)), "bash", self.mnt(f)], timeout + 30, env=scrubbed_env())
        f.unlink(missing_ok=True)
        if rc == 124: to = True
        return rc, out, to

    def start(self):
        rc, out, _ = self._sh(f"mkdir -p {self.ws} {self.stage}\n", 120)
        if rc:
            _, lst, _ = run_proc([self.wsl, "-l", "-v"], 60)
            raise RuntimeError("wsl start: " + decode(out)[-400:] + " | wsl -l -v: " + decode(lst).replace("\x00", "")[-400:])

    def reset(self, path):
        self._sh(f"rm -rf {shlex.quote(path)} && mkdir -p {shlex.quote(path)}\n", 120)

    def push(self, local_dir, remote_dir):
        rc, out, _ = self._sh(f"mkdir -p {shlex.quote(remote_dir)} && cp -a {shlex.quote(self.mnt(local_dir))}/. {shlex.quote(remote_dir)}/\n", 300)
        if rc: raise RuntimeError("wsl push: " + decode(out)[-300:])

    def pull_file(self, remote_path):
        dst = self.tmp / f"pull-{uuid.uuid4().hex[:8]}"
        rc, _, _ = self._sh(f"cp {shlex.quote(remote_path)} {shlex.quote(self.mnt(dst))}\n", 60)
        return dst.read_bytes() if rc == 0 and dst.exists() else None

    def run(self, cmd, timeout=180, cwd=None, env=None):
        e = dict(LINUX_ENV); e.update(BASE_ENV); e.update(self.env); e.update(env or {})
        rc, out, to = self._sh(_bash_script(cmd, cwd or self.ws, e), timeout)
        return rc, decode(out), to


class SSH(Executor):
    """gh-vm (QEMU/KVM guest) and gh-microvm (Firecracker guest): commands run over ssh as root.
    The guest is booted by cellexec/vm_boot.sh or cellexec/microvm_boot.sh, which export CELL_SSH_*."""
    remote = True

    def __init__(self, cell, variant, extra_env):
        super().__init__(cell, variant, extra_env)
        self.ws, self.stage = "/workspace", "/opt/stage"
        host = os.environ.get("CELL_SSH_HOST")
        if not host: raise RuntimeError("CELL_SSH_HOST not set: the guest was not booted")
        self.target = f"{os.environ.get('CELL_SSH_USER', 'root')}@{host}"
        self.opts = ["-i", os.environ["CELL_SSH_KEY"], "-p", os.environ.get("CELL_SSH_PORT", "22"),
                     "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
                     "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", "-o", "ServerAliveInterval=15"]

    def ssh(self, remote_cmd, timeout, input=None):
        return run_proc(["ssh"] + self.opts + [self.target, remote_cmd], timeout, input=input)

    def start(self):
        rc, out, _ = self.ssh(f"mkdir -p {self.ws} {self.stage}", 120)
        if rc: raise RuntimeError("ssh start: " + decode(out)[-400:])

    def reset(self, path):
        self.ssh(f"rm -rf {shlex.quote(path)} && mkdir -p {shlex.quote(path)}", 120)

    def push(self, local_dir, remote_dir):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf: tf.add(str(local_dir), arcname=".")
        rc, out, _ = self.ssh(f"mkdir -p {shlex.quote(remote_dir)} && tar -C {shlex.quote(remote_dir)} -xf -", 300, input=buf.getvalue())
        if rc: raise RuntimeError("ssh push: " + decode(out)[-300:])

    def pull_file(self, remote_path):
        rc, out, _ = self.ssh(f"cat {shlex.quote(remote_path)}", 60)
        return out if rc == 0 else None

    def run(self, cmd, timeout=180, cwd=None, env=None):
        e = dict(LINUX_ENV); e.update(BASE_ENV); e.update(self.env); e.update(env or {})
        script = _bash_script(cmd, cwd or self.ws, e).encode("utf-8")
        name = f"/tmp/_cell_cmd_{uuid.uuid4().hex[:8]}.sh"
        rc, out, _ = self.ssh(f"cat > {name}", 60, input=script)
        if rc: return rc, "ssh: could not stage the command: " + decode(out)[-300:], False
        rc, out, to = self.ssh(f"timeout -k 5 {int(timeout)} bash {name}; r=$?; rm -f {name}; exit $r", timeout + 30)
        if rc == 124: to = True
        return rc, decode(out), to


class ADB(Executor):
    """gh-android: commands run with adb shell on the emulator (toybox + mksh, no python on the device)."""
    family = "sh"
    os_name = "Android"
    python = None
    remote = True

    def __init__(self, cell, variant, extra_env):
        super().__init__(cell, variant, extra_env)
        self.ws, self.stage = "/data/local/tmp/workspace", "/data/local/tmp/stage"

    def _adb(self, args, timeout, input=None):
        return run_proc(["adb"] + args, timeout, input=input)

    def start(self):
        self._adb(["shell", f"mkdir -p {self.ws} {self.stage}"], 120)

    def reset(self, path):
        self._adb(["shell", f"rm -rf {path} && mkdir -p {path}"], 120)

    def push(self, local_dir, remote_dir):
        self._adb(["shell", f"mkdir -p {remote_dir}"], 60)
        for c in sorted(os.listdir(local_dir)):
            rc, out, _ = self._adb(["push", os.path.join(local_dir, c), remote_dir + "/"], 300)
            if rc: raise RuntimeError("adb push: " + decode(out)[-300:])

    def pull_file(self, remote_path):
        rc, out, _ = self._adb(["exec-out", "cat", remote_path], 60)
        return out if rc == 0 else None

    def run(self, cmd, timeout=180, cwd=None, env=None):
        e = dict(BASE_ENV); e.update(self.env); e.update(env or {})
        lines = [f"export {k}={shlex.quote(str(v))}" for k, v in e.items()] + [f"cd {shlex.quote(cwd or self.ws)} || exit 125", cmd]
        f = self.tmp / "cmd.sh"
        with open(f, "w", encoding="utf-8", newline="\n") as fh: fh.write("\n".join(lines) + "\n")
        self._adb(["push", str(f), "/data/local/tmp/_cell_cmd.sh"], 60)
        rc, out, to = self._adb(["shell", f"timeout {int(timeout)} sh /data/local/tmp/_cell_cmd.sh"], timeout + 30)
        if rc == 124: to = True
        return rc, decode(out), to


def make_executor(cell, how, variant, extra_env):
    if cell == "base" or how in ("base", "plain"):
        return LocalBash(cell, variant, extra_env)
    if how in ("pwsh", "ps5", "cmd", "winnative"):
        return LocalWindows(cell, variant, extra_env, how)
    if how == "docker": return Docker(cell, variant, extra_env)
    if how == "wsl": return WSL(cell, variant, extra_env)
    if how in ("vm", "microvm"): return SSH(cell, variant, extra_env)
    if how == "android": return ADB(cell, variant, extra_env)
    raise ValueError(f"unknown how {how!r}")


# ----------------------------------------------------------------------------------------------- bundle
# Value of an unused TASKS_B64_n secret. GitHub masks every secret value in job logs, so it must be a string that
# never occurs in a log line (a "." sentinel turned every "." in the logs into "***").
UNUSED = "~unused-TASKS_B64-chunk~"

def load_bundle(path):
    """tasks_b64.txt (base64 of tar.gz with tasks/<ID>/...) -> (fingerprint, {task_id: {relpath: (bytes, mode)}})."""
    p = pathlib.Path(path)
    if not p.exists():
        return "none", {}
    b64 = p.read_text(encoding="ascii").replace(UNUSED, "").strip()
    if not b64:
        return "none", {}
    fp = hashlib.sha256(b64.encode()).hexdigest()[:16]
    tasks = {}
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(b64)), mode="r:gz") as tf:
        for m in tf.getmembers():
            parts = m.name.split("/")
            if len(parts) < 3 or parts[0] != "tasks" or not m.isfile():
                continue
            tasks.setdefault(parts[1], {})["/".join(parts[2:])] = (tf.extractfile(m).read(), m.mode)
    return fp, tasks


def materialise(files, prefix, dst):
    """Write the members under prefix/ to a local directory (bytes as-is, exec bits kept)."""
    n = 0
    for rel, (data, mode) in files.items():
        if prefix and not rel.startswith(prefix + "/"):
            continue
        sub = rel[len(prefix) + 1:] if prefix else rel
        out = pathlib.Path(dst) / sub
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        if not WIN and mode & 0o111: out.chmod(0o755)
        n += 1
    return n


# ----------------------------------------------------------------------------------------------- one run
class Run:
    def __init__(self, a, mode, fp, files):
        self.a, self.mode, self.fp, self.files = a, mode, fp, files
        self.task = json.loads(files["task.json"][0].decode("utf-8")) if files else {}
        self.tid = self.task.get("id", a.task) if files else "smoke"
        sub = mode if mode != "agent" else f"agent-{a.model}{a.tag}"
        self.dir = pathlib.Path(a.out).resolve() / (self.tid if files else f"_smoke-{a.variant}") / a.cell / sub
        self.dir.mkdir(parents=True, exist_ok=True)
        self.res = {"task": self.tid, "cell": a.cell, "mode": mode, "model": a.model if mode == "agent" else None,
                    "sandbox": a.variant if a.cell == "target" else "base", "variant": a.variant, "how": a.how if a.cell == "target" else "base",
                    "sub": self.task.get("sub"), "fp": fp, "runner_os": os.environ.get("ImageOS") or platform.platform(),
                    "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                    "job": os.environ.get("CELL_JOB_LABEL")}

    def pick(self, stem):
        for ext in self.ex.exts():
            if stem + ext in self.files:
                return stem + ext
        return None

    def stage_files(self, prefix, remote):
        loc = self.ex.tmp / ("st-" + uuid.uuid4().hex[:8])
        loc.mkdir()
        n = materialise(self.files, prefix, loc)
        if n: self.ex.push(loc, remote)
        shutil.rmtree(loc, ignore_errors=True)
        return n

    def stage_one(self, rel, remote_dir):
        loc = self.ex.tmp / ("one-" + uuid.uuid4().hex[:8]); loc.mkdir()
        data, mode = self.files[rel]
        (loc / os.path.basename(rel)).write_bytes(data)
        self.ex.push(loc, remote_dir); shutil.rmtree(loc, ignore_errors=True)
        return self.ex.join(remote_dir, os.path.basename(rel))

    def cell_env(self):
        return {"CELL": self.a.cell, "WORKSPACE": self.ex.ws, "STAGE": self.ex.stage}

    def facts(self):
        """Cheap readings of the cell (public): python version, preferred encoding, UTF-8 mode, shell."""
        if not self.ex.python:
            rc, out, _ = self.ex.run("uname -a; getprop ro.build.version.release", 60); self.res["cell_facts"] = out.strip()[-300:]; return
        code = "import sys,locale,platform;print(platform.system(),sys.version.split()[0],locale.getpreferredencoding(False),sys.flags.utf8_mode)"
        q = {"pwsh": f"& {self.ex.python} -c \"{code}\"", "cmd": f'{self.ex.python} -c "{code}"'}.get(self.ex.family, f"{self.ex.python} -c {shlex.quote(code)}")
        rc, out, _ = self.ex.run(q, 120)
        self.res["cell_facts"] = out.strip()[-300:]

    def start(self):
        self.ex = make_executor(self.a.cell, self.a.how, self.a.variant, {})
        self.ex.start()
        self.ex.reset(self.ex.ws); self.ex.reset(self.ex.stage)
        self.facts()
        if not self.files:
            return
        self.stage_files("workspace", self.ex.ws)
        setup = self.pick("setup")
        if setup:
            path = self.stage_one(setup, self.ex.join(self.ex.stage, "setup"))
            rc, out, _ = self.ex.run(self.ex.file_cmd(path), 600, env=self.cell_env())
            self.res["setup_out"] = truncate(out, 3000)
            if rc: raise RuntimeError(f"setup rc={rc}: {out[-1200:]}")
        self.ex.reset(self.ex.stage)

    def run_solution(self, which):
        sol = self.pick(f"solution/{which}")
        if not sol: raise RuntimeError(f"no solution/{which}{{{','.join(self.ex.exts())}}} for a {self.ex.family} cell")
        sd = self.ex.join(self.ex.stage, "solution")
        self.stage_files("solution", sd)
        path = self.ex.join(sd, *sol.split("/")[1:])
        rc, out, to = self.ex.run(self.ex.file_cmd(path), self.task.get("timeout_sec", 900), env={"SOLUTION_DIR": sd})
        self.res["solution_rc"] = rc; self.res["solution_out"] = truncate(out, 4000)
        self.ex.reset(self.ex.stage)

    def verify(self):
        v = self.pick("verify")
        if not v: raise RuntimeError(f"no verify{{{','.join(self.ex.exts())}}} for a {self.ex.family} cell")
        self.ex.reset(self.ex.stage)
        self.stage_files("judge", self.ex.join(self.ex.stage, "judge"))
        path = self.stage_one(v, self.ex.stage)
        rc, out, to = self.ex.run(self.ex.file_cmd(path), self.task.get("verify_timeout", 300), env=self.cell_env())
        self.res["pass"] = rc == 0; self.res["verify_rc"] = rc; self.res["verify_out"] = truncate(out, 6000)
        if to: self.res["verify_timed_out"] = True
        if self.task.get("deliverable"):
            b = self.ex.pull_file(self.ex.join(self.ex.ws, self.task["deliverable"]))
            if b is not None:
                self.res["deliverable_sha256"] = hashlib.sha256(b).hexdigest()
                (self.dir / "deliverable").mkdir(exist_ok=True)
                (self.dir / "deliverable" / os.path.basename(self.task["deliverable"])).write_bytes(b)

    def smoke(self):
        rc, out, to = self.ex.run(self.a.cmd, 300)
        self.res.update(smoke_rc=rc, smoke_out=truncate(out, 3000), smoke_timed_out=to, **{"pass": rc == 0})

    # ---- agent (port of suite_runner.Run.call_model / run_agent)
    def call_model(self, messages):
        model = self.a.model
        if anthropic_native.is_native(model):
            if not os.environ.get("ANTHROPIC_API_KEY"): raise RuntimeError("channel error: no ANTHROPIC_API_KEY secret")
            return anthropic_native.call(model, messages, TOOLS)
        req_body = {"model": model, "messages": messages, "tools": TOOLS, "max_tokens": 32768}
        req_body.update(REASONING.get(model, {}))
        body = json.dumps(req_body).encode(); last = None; filtered = 0
        for attempt in range(12):
            try:
                req = urllib.request.Request(API_URL + "/chat/completions", data=body,
                                             headers={"Authorization": f"Bearer {API['LLMGATEWAY_API_KEY']}", "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    d = json.loads(r.read().decode())
                if (d.get("choices") or [{}])[0].get("finish_reason") == "content_filter" and filtered < 5:
                    filtered += 1; self.res["filter_retries"] = self.res.get("filter_retries", 0) + 1
                    time.sleep(3 * filtered); continue
                return d
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
                if e.code in (401, 402, 403, 404) or (e.code == 400 and "reasoning_content" not in last): break
            except Exception as e:
                last = repr(e)
            time.sleep(min(60, 5 * 2 ** attempt))
        raise RuntimeError("channel error: " + str(last))

    def run_agent(self):
        max_steps = self.task.get("max_steps", 40); budget = self.task.get("timeout_sec", 1500); t0 = time.time()
        sysp = SYSTEM_PROMPT.format(os=self.ex.os_name, ws=self.ex.ws)
        messages = [{"role": "system", "content": sysp}, {"role": "user", "content": self.task["prompt"]}]
        trace = open(self.dir / "trace.jsonl", "w", encoding="utf-8")
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "cost": 0.0, "requests": 0}
        steps = 0; nudged = False; finish = None
        while steps < max_steps and time.time() - t0 < budget:
            resp = self.call_model(messages); usage["requests"] += 1; u = resp.get("usage") or {}
            usage["prompt_tokens"] += u.get("prompt_tokens", 0) or 0; usage["completion_tokens"] += u.get("completion_tokens", 0) or 0
            usage["cost"] += float(u.get("cost") or 0)
            usage["reasoning_tokens"] += ((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
            ch = resp["choices"][0]; msg = ch["message"]
            am = {"role": "assistant", "content": msg.get("content") or "", "reasoning_content": msg.get("reasoning_content") or msg.get("reasoning") or ""}
            if msg.get("reasoning_details"): am["reasoning_details"] = msg["reasoning_details"]   # signed thinking blocks go back verbatim
            if msg.get("anthropic_content"): am["anthropic_content"] = msg["anthropic_content"]
            tcs = msg.get("tool_calls") or []
            if tcs: am["tool_calls"] = [{"id": t["id"], "type": "function", "function": {"name": t["function"]["name"], "arguments": t["function"].get("arguments") or "{}"}} for t in tcs]
            messages.append(am); steps += 1
            trace.write(json.dumps({"step": steps, "finish_reason": ch.get("finish_reason"), "content": am["content"], "reasoning": am["reasoning_content"][:4000], "tool_calls": am.get("tool_calls")}, ensure_ascii=False) + "\n")
            if not tcs:
                if ch.get("finish_reason") == "content_filter": finish = "content_filter"; break
                if ch.get("finish_reason") == "length": finish = "length"; break
                if nudged: finish = "no_tool_call"; break
                nudged = True; messages.append({"role": "user", "content": "If the task is complete, call the finish tool. Otherwise, continue working."}); continue
            done = False
            for t in am["tool_calls"]:
                try: a = json.loads(t["function"]["arguments"] or "{}")
                except Exception: a = {}
                if t["function"]["name"] == "finish": out = "ok"; done = True; finish = "finish"
                elif t["function"]["name"] == "bash":
                    to = max(1, min(int(a.get("timeout") or 180), 600))
                    rc, o, timed_out = self.ex.run(a.get("command", ""), timeout=to)
                    out = truncate(o) + (f"\n[command timed out after {to}s]" if timed_out else f"\n[exit code: {rc}]")
                else: out = f"unknown tool {t['function']['name']}"
                messages.append({"role": "tool", "tool_call_id": t["id"], "content": out})
                trace.write(json.dumps({"tool": t["function"]["name"], "args": a, "output": out[:6000]}, ensure_ascii=False) + "\n")
            if done: break
        trace.close()
        self.res.update(steps=steps, finish=finish or ("max_steps" if steps >= max_steps else "budget"), usage=usage, wall=round(time.time() - t0, 1))

    def go(self):
        t0 = time.time(); self.ex = None
        try:
            self.start()
            if self.mode == "smoke": self.smoke()
            else:
                if self.mode in ("ref", "naive"): self.run_solution(self.mode)
                elif self.mode == "agent": self.run_agent()
                else: raise ValueError(f"unknown mode {self.mode}")
                self.verify()
        except Exception as e:
            self.res.update(error=str(e)[:3000], invalid=True, **{"pass": None})
            log(f"{self.tid} {self.a.cell} {self.mode}: error {str(e)[:300]}")
        finally:
            try:
                if self.ex: self.ex.stop()
            except Exception: pass
            self.res["total_wall"] = round(time.time() - t0, 1)
            with open(self.dir / "result.json", "w", encoding="utf-8", newline="\n") as fh:
                json.dump(self.res, fh, ensure_ascii=False, indent=1)
        return self.res


def public_line(r):
    """The one stdout line per mode. No task text beyond the verifier's last line (200 chars)."""
    keep = ("task", "cell", "mode", "variant", "how", "sandbox", "pass", "verify_rc", "solution_rc", "invalid", "fp",
            "runner_os", "run_id", "run_attempt", "job", "cell_facts", "total_wall", "steps", "finish", "usage", "smoke_rc",
            "smoke_out", "deliverable_sha256", "verify_timed_out")
    d = {"kind": "cell_result"}
    d.update({k: r[k] for k in keep if k in r})
    if r.get("error"): d["error"] = r["error"][:400]
    vo = [l for l in (r.get("verify_out") or "").strip().splitlines() if l.strip()]
    if vo and os.environ.get("CELL_PUBLIC_TAIL", "1") == "1": d["verify_tail"] = vo[-1][:200]
    return json.dumps(d, ensure_ascii=True)


REASONING = {}


def main():
    global REASONING
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=""); ap.add_argument("--cell", required=True, choices=["base", "target"])
    ap.add_argument("--variant", required=True); ap.add_argument("--how", required=True)
    ap.add_argument("--mode", required=True); ap.add_argument("--bundle", default="tasks_b64.txt")
    ap.add_argument("--out", default="out"); ap.add_argument("--model", default="deepseek-v4.1-flash")
    ap.add_argument("--tag", default=""); ap.add_argument("--cmd", default="")
    a = ap.parse_args()
    if os.environ.get("REASONING_JSON"): REASONING = json.loads(os.environ["REASONING_JSON"])
    elif os.environ.get("REASONING_PARAMS"): REASONING = json.load(open(os.environ["REASONING_PARAMS"]))
    modes = [m for m in a.mode.split(",") if m]
    modes = [m for m in modes if m != "agent"] + (["agent"] if "agent" in modes else [])
    fp, tasks = load_bundle(a.bundle) if a.task else ("none", {})
    files = {}
    if a.task:
        if a.task not in tasks:
            line = {"kind": "cell_result", "task": a.task, "cell": a.cell, "mode": a.mode, "variant": a.variant, "fp": fp,
                    "invalid": True, "pass": None, "error": f"task not in bundle ({len(tasks)} tasks)"}
            print(json.dumps(line), flush=True); return 2
        files = tasks[a.task]; tasks = None
    rc = 0
    for m in modes:
        if m == "agent" and a.task:
            # the agent shares this host with local cells: no task material may stay on disk
            for p in (a.bundle, "tasks_b64.txt"):
                try: os.remove(p)
                except OSError: pass
        if m == "smoke" and not a.cmd:
            print(json.dumps({"kind": "cell_result", "mode": "smoke", "error": "no --cmd", "invalid": True}), flush=True); rc = 2; continue
        r = Run(a, m, fp, files).go()
        print(public_line(r), flush=True)
        log(f"{r['task']} {r['cell']} {m}: pass={r.get('pass')} verify_rc={r.get('verify_rc')} wall={r.get('total_wall')}")
        if r.get("invalid"): rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
