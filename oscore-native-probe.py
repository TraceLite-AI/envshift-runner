"""Bounded native OS probes. Only own temporary files/processes/loopback sockets.

Results are observations, never hardcoded expected outcomes. No model or secrets.
Python 3.8+; Windows APIs use explicit ctypes prototypes for pointer safety.
"""
import argparse
import ctypes
import hashlib
import json
import mmap
import os
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path

WIN = os.name == 'nt'


def wait_file(p, proc=None, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if p.exists():
            return p.read_text()
        if proc is not None and proc.poll() is not None:
            raise RuntimeError('child exited before acknowledgement: %r' % proc.returncode)
        time.sleep(.02)
    raise TimeoutError('child acknowledgement timeout')


def child(code, *args):
    return subprocess.Popen([sys.executable, '-c', code] + list(map(str, args)),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def finish(p):
    try:
        out, err = p.communicate(timeout=8)
        if p.returncode:
            raise RuntimeError('child exit %s: %s' % (p.returncode, err.decode(errors='replace')[-2000:]))
        return out.decode()
    finally:
        if p.poll() is None:
            p.kill()
            p.communicate(timeout=3)


def ads(root):
    base = root / 'record.dat'
    base.write_bytes(b'primary')
    extra = root / 'record.dat:receipt'
    extra.write_bytes(b'accepted=7')
    entries = sorted(p.name for p in root.iterdir())
    import shutil
    copied = root / 'copied.dat'
    shutil.copyfile(base, copied)
    stream_copy = root / 'copied.dat:receipt'
    return {'direct_read': extra.read_bytes().decode(), 'directory_entries': entries,
            'primary_size': base.stat().st_size, 'receipt_visible_in_directory': extra.name in entries,
            'copyfile_preserves_receipt': stream_copy.exists(),
            'listed_total_bytes': sum((root / n).stat().st_size for n in entries)}


def device_name(root):
    out = {}
    for name in ('NUL', 'nul.txt', 'ordinary.txt'):
        p = root / name
        try:
            with open(str(p), 'wb') as f:
                wrote = f.write(b'RECEIPT-123')
            out[name] = {'write_count': wrote, 'exists': p.exists(),
                         'read': p.read_bytes().decode(), 'listed': name in os.listdir(root)}
        except OSError as e:
            out[name] = {'error': type(e).__name__, 'errno': e.errno, 'winerror': getattr(e, 'winerror', None)}
    return out


LOCK_CODE = '''import os,sys,json
f=open(sys.argv[1],'r+b',buffering=0)
try:
 if sys.argv[2]=='write':
  f.write(b'X'); result={'succeeded':True}
 else:
  if os.name=='nt':
   import msvcrt; msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
  else:
   import fcntl; fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB,1)
  result={'succeeded':True}
except OSError as e: result={'succeeded':False,'errno':e.errno,'winerror':getattr(e,'winerror',None)}
f.close(); print(json.dumps(result))
'''


def lock_one(f):
    f.seek(0)
    if WIN:
        import msvcrt
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB, 1)


def record_locks(root):
    path = root / 'ledger.bin'
    path.write_bytes(b'abc')
    with open(str(path), 'r+b', buffering=0) as owner:
        lock_one(owner)
        other_lock = json.loads(finish(child(LOCK_CODE, path, 'lock')))
        raw_write = json.loads(finish(child(LOCK_CODE, path, 'write')))
    raw_after = path.read_bytes().decode()
    path.write_bytes(b'abc')
    with open(str(path), 'r+b', buffering=0) as owner:
        lock_one(owner)
        before = json.loads(finish(child(LOCK_CODE, path, 'lock')))
        with open(str(path), 'rb'):
            pass
        after = json.loads(finish(child(LOCK_CODE, path, 'lock')))
    return {'competing_lock': other_lock, 'uncooperative_write': raw_write,
            'bytes_after_write': raw_after,
            'competing_lock_before_unrelated_close': before,
            'competing_lock_after_unrelated_close': after}


def shared_memory(root):
    name = 'envshift_' + uuid.uuid4().hex
    if WIN:
        from ctypes import wintypes as w
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateFileMappingW.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD, w.DWORD, w.DWORD, w.LPCWSTR]
        k.CreateFileMappingW.restype = w.HANDLE
        k.OpenFileMappingW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
        k.OpenFileMappingW.restype = w.HANDLE
        k.MapViewOfFile.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, ctypes.c_size_t]
        k.MapViewOfFile.restype = ctypes.c_void_p
        k.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        k.UnmapViewOfFile.restype = w.BOOL
        k.CloseHandle.argtypes = [w.HANDLE]
        k.CloseHandle.restype = w.BOOL
        h = k.CreateFileMappingW(w.HANDLE(-1), None, 4, 0, 4096, name)
        if not h:
            raise ctypes.WinError(ctypes.get_last_error())
        view = None
        try:
            view = k.MapViewOfFile(h, 0xF001F, 0, 0, 4096)
            if not view:
                raise ctypes.WinError(ctypes.get_last_error())
            ctypes.memmove(view, b'READY=7', 7)
            h2 = k.OpenFileMappingW(0xF001F, False, name)
            before = bool(h2)
            if h2:
                k.CloseHandle(h2)
        finally:
            if view:
                k.UnmapViewOfFile(view)
            k.CloseHandle(h)
        h2 = k.OpenFileMappingW(0xF001F, False, name)
        after = bool(h2)
        if h2:
            k.CloseHandle(h2)
        h3 = k.CreateFileMappingW(w.HANDLE(-1), None, 4, 0, 4096, name)
        if not h3:
            raise ctypes.WinError(ctypes.get_last_error())
        v3 = k.MapViewOfFile(h3, 0xF001F, 0, 0, 4096)
        try:
            if not v3:
                raise ctypes.WinError(ctypes.get_last_error())
            data = ctypes.string_at(v3, 7).hex()
        finally:
            if v3:
                k.UnmapViewOfFile(v3)
            k.CloseHandle(h3)
    else:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.shm_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint]
        libc.shm_open.restype = ctypes.c_int
        libc.shm_unlink.argtypes = [ctypes.c_char_p]
        libc.shm_unlink.restype = ctypes.c_int
        n = ('/' + name[:25]).encode()
        def shm(flags):
            return libc.shm_open(n, flags, 0o600)
        fd = shm(os.O_CREAT | os.O_EXCL | os.O_RDWR)
        if fd < 0:
            raise OSError(ctypes.get_errno(), 'shm_open failed')
        try:
            os.ftruncate(fd, 4096)
            with mmap.mmap(fd, 4096) as v:
                v[:7] = b'READY=7'
            fd2 = shm(os.O_RDWR)
            before = fd2 >= 0
            if before:
                os.close(fd2)
            os.close(fd)
            fd = -1
            fd2 = shm(os.O_RDWR)
            after = fd2 >= 0
            if after:
                os.close(fd2)
            fd3 = shm(os.O_CREAT | os.O_RDWR)
            if fd3 < 0:
                raise OSError(ctypes.get_errno(), 'reopen failed')
            try:
                with mmap.mmap(fd3, 4096) as v:
                    data = v[:7].hex()
            finally:
                os.close(fd3)
        finally:
            if fd >= 0:
                os.close(fd)
            libc.shm_unlink(n)
    return {'can_open_while_owner_alive': before, 'can_open_after_last_close': after,
            'create_or_open_after_last_close_hex': data, 'expected_hex': b'READY=7'.hex()}


def termination(root):
    code = '''import signal,sys,time
from pathlib import Path
r=Path(sys.argv[1]); mode=sys.argv[2]
def stop(*args):
 (r/'receipt').write_text('COMMITTED=7'); sys.exit(0)
signal.signal(signal.SIGTERM,stop)
(r/'ready').write_text('ready')
while True:
 if mode=='graceful' and (r/'stop').exists(): stop()
 time.sleep(.02)
'''
    results = {}
    for mode in ('terminate', 'graceful'):
        sub = root / mode
        sub.mkdir()
        p = child(code, sub, mode)
        try:
            wait_file(sub / 'ready', p)
            if mode == 'terminate':
                p.terminate()
            else:
                (sub / 'stop').write_text('stop')
            out, err = p.communicate(timeout=5)
            results[mode] = {'returncode': p.returncode, 'receipt': (sub / 'receipt').read_text() if (sub / 'receipt').exists() else None}
        finally:
            if p.poll() is None:
                p.kill()
                p.communicate(timeout=3)
    return results


def exec_identity(root):
    after = "import os,sys;from pathlib import Path;Path(sys.argv[1]).write_text(str(os.getpid()))"
    code = "import os,sys;from pathlib import Path;Path(sys.argv[1]).write_text(str(os.getpid()));os.execv(sys.executable,[sys.executable,'-c',sys.argv[3],sys.argv[2]])"
    p = child(code, root / 'before', root / 'after', after)
    out, err = p.communicate(timeout=8)
    if p.returncode:
        raise RuntimeError(err.decode(errors='replace'))
    pid_after = int(wait_file(root / 'after'))
    pid_before = int((root / 'before').read_text())
    return {'pid_preserved': pid_before == pid_after, 'launcher_pid_matches_before': p.pid == pid_before}


def dual_stack(root):
    result = {}
    for mode in ('default', 'explicit_dual'):
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as server:
            default = server.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY)
            if mode == 'explicit_dual':
                server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            server.bind(('::', 0))
            server.listen(2)
            server.settimeout(.5)
            accepts = {}
            for family, host in ((socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')):
                with socket.socket(family, socket.SOCK_STREAM) as client:
                    client.settimeout(.5)
                    try:
                        client.connect((host, server.getsockname()[1]))
                        conn, addr = server.accept()
                        with conn:
                            client.sendall(b'ping')
                            accepts[host] = conn.recv(4) == b'ping'
                    except OSError as e:
                        accepts[host] = {'error': e.errno, 'winerror': getattr(e, 'winerror', None)}
            result[mode] = {'default_v6only': default, 'delivered': accepts}
    return result


def allocated(p):
    if not WIN:
        return p.stat().st_blocks * 512
    from ctypes import wintypes as w
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCompressedFileSizeW.argtypes = [w.LPCWSTR, ctypes.POINTER(w.DWORD)]
    k.GetCompressedFileSizeW.restype = w.DWORD
    high = w.DWORD()
    ctypes.set_last_error(0)
    low = k.GetCompressedFileSizeW(str(p), ctypes.byref(high))
    if low == 0xFFFFFFFF and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    return (high.value << 32) | low


def sparse(root):
    result = {}
    for mode in ('default', 'explicit_sparse'):
        p = root / mode
        with open(str(p), 'w+b') as f:
            if WIN and mode == 'explicit_sparse':
                from ctypes import wintypes as w
                import msvcrt
                k = ctypes.WinDLL('kernel32', use_last_error=True)
                k.DeviceIoControl.argtypes = [w.HANDLE, w.DWORD, ctypes.c_void_p, w.DWORD, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD), ctypes.c_void_p]
                k.DeviceIoControl.restype = w.BOOL
                n = w.DWORD()
                if not k.DeviceIoControl(msvcrt.get_osfhandle(f.fileno()), 0x900C4, None, 0, None, 0, ctypes.byref(n), None):
                    raise ctypes.WinError(ctypes.get_last_error())
            f.truncate(16 * 1024 * 1024)
            f.flush()
        with open(str(p), 'rb') as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        result[mode] = {'logical_bytes': p.stat().st_size, 'allocated_bytes': allocated(p), 'sha256': digest}
    return result


def unlink_readonly(root):
    p = root / 'readonly'
    p.write_bytes(b'owned test file')
    p.chmod(0o444)
    try:
        p.unlink()
        result = {'deleted': True}
    except OSError as e:
        result = {'deleted': False, 'errno': e.errno, 'winerror': getattr(e, 'winerror', None)}
    finally:
        if p.exists():
            p.chmod(0o666)
            p.unlink()
    return result


def unlink_open(root):
    p = root / 'held'
    p.write_bytes(b'v1')
    with open(str(p), 'rb') as f:
        try:
            p.unlink()
            result = {'deleted': True, 'old_handle_reads': f.read().decode()}
        except OSError as e:
            result = {'deleted': False, 'errno': e.errno, 'winerror': getattr(e, 'winerror', None)}
    return result


def cwd_remove(root):
    sub = root / 'owned-working-directory'
    sub.mkdir()
    code = "import os,sys,time;from pathlib import Path;os.chdir(sys.argv[1]);Path(sys.argv[2]).write_text('ready');time.sleep(15)"
    p = child(code, sub, root / 'ready')
    try:
        wait_file(root / 'ready', p)
        try:
            sub.rmdir()
            result = {'removed_while_child_cwd': True}
        except OSError as e:
            result = {'removed_while_child_cwd': False, 'errno': e.errno, 'winerror': getattr(e, 'winerror', None)}
    finally:
        if p.poll() is None:
            p.kill()
        p.communicate(timeout=3)
    return result


def mmap_delete(root):
    p = root / 'mapped'
    p.write_bytes(b'x' * 4096)
    with open(str(p), 'r+b') as f:
        view = mmap.mmap(f.fileno(), 4096)
    try:
        try:
            p.unlink()
            result = {'deleted_with_only_mapping_alive': True, 'view_byte': view[:1].decode()}
        except OSError as e:
            result = {'deleted_with_only_mapping_alive': False, 'errno': e.errno, 'winerror': getattr(e, 'winerror', None)}
    finally:
        view.close()
    return result


def negative_hardlink(root):
    a, b = root / 'a', root / 'b'
    a.write_bytes(b'old')
    os.link(a, b)
    a.write_bytes(b'new')
    same = os.path.samefile(a, b)
    a.unlink()
    return {'alias_saw_write': b.read_bytes().decode(), 'same_object_before_unlink': same,
            'survives_other_name_unlink': b.exists()}


def select_pipe(root):
    import select
    r, w = os.pipe()
    try:
        os.write(w, b'ack')
        try:
            ready = select.select([r], [], [], .1)[0]
            return {'ready': bool(ready)}
        except OSError as e:
            return {'error': e.errno, 'winerror': getattr(e, 'winerror', None)}
    finally:
        os.close(r)
        os.close(w)


PROBES = {f.__name__: f for f in (ads, device_name, record_locks, shared_memory,
    termination, exec_identity, dual_stack, sparse, unlink_readonly, unlink_open,
    cwd_remove, mmap_delete, negative_hardlink, select_pipe)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='native-results.json')
    parser.add_argument('--repeat', type=int, default=1)
    args = parser.parse_args()
    result = {'schema': 1, 'system': platform.system(), 'release': platform.release(),
              'machine': platform.machine(), 'python': platform.python_version(),
              'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'trials': []}
    for trial in range(args.repeat):
        facts = {}
        with tempfile.TemporaryDirectory(prefix='envshift-oscore-') as tmp:
            root = Path(tmp)
            for name, fn in PROBES.items():
                work = root / name
                work.mkdir()
                start = time.monotonic()
                try:
                    facts[name] = {'ok': True, 'observation': fn(work)}
                except Exception as e:
                    facts[name] = {'ok': False, 'probe_error': type(e).__name__ + ': ' + str(e), 'traceback': traceback.format_exc()}
                facts[name]['elapsed_seconds'] = round(time.monotonic() - start, 3)
                print('%s trial=%s %s' % (name, trial + 1, json.dumps(facts[name], ensure_ascii=True)), flush=True)
        result['trials'].append(facts)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
