#!/usr/bin/env python3
"""Pack and encrypt the cell outputs (public repo: results hold task text and agent traces).

  python cellexec/seal.py out out.tgz.enc

Same scheme as xos-agent.yml: openssl enc -aes-256-cbc -pbkdf2 -salt with the ARTIFACT_PASS secret.
Finds openssl explicitly on Windows (Git for Windows ships it) instead of going through a bash shell.
"""
import os, shutil, subprocess, sys, tarfile


def openssl():
    p = shutil.which("openssl")
    if p:
        return p
    for c in (r"C:\Program Files\Git\usr\bin\openssl.exe", r"C:\Program Files\Git\mingw64\bin\openssl.exe"):
        if os.path.exists(c):
            return c
    sys.exit("seal: openssl not found")


def main(src, dst):
    if not os.environ.get("ARTIFACT_PASS"):
        print("seal: no ARTIFACT_PASS; nothing uploaded", file=sys.stderr); return 0
    tgz = dst + ".tmp.tgz"
    with tarfile.open(tgz, "w:gz") as tf:
        if os.path.isdir(src):
            tf.add(src, arcname="out")
    r = subprocess.run([openssl(), "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:ARTIFACT_PASS",
                        "-in", tgz, "-out", dst])
    os.remove(tgz)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
