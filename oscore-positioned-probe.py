"""Native append handle + positioned write observation; no fabricated OS result."""
import ctypes
import json
import os
import platform
import tempfile
from pathlib import Path


def positioned_write(fd, payload, offset):
    if os.name != 'nt':
        return os.pwrite(fd, payload, offset)
    import msvcrt
    from ctypes import wintypes as w
    class OVERLAPPED(ctypes.Structure):
        _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                    ('Offset', w.DWORD), ('OffsetHigh', w.DWORD), ('hEvent', w.HANDLE)]
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.WriteFile.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD), ctypes.POINTER(OVERLAPPED)]
    k.WriteFile.restype = w.BOOL
    ov = OVERLAPPED()
    ov.Offset = offset & 0xFFFFFFFF
    ov.OffsetHigh = offset >> 32
    written = w.DWORD()
    data = ctypes.create_string_buffer(payload)
    if not k.WriteFile(msvcrt.get_osfhandle(fd), data, len(payload), ctypes.byref(written), ctypes.byref(ov)):
        raise ctypes.WinError(ctypes.get_last_error())
    return written.value


def observe(root):
    rows = {}
    for mode in ('append_handle', 'update_handle'):
        p = root / mode
        p.write_bytes(b'0000:payload')
        flags = os.O_RDWR | getattr(os, 'O_BINARY', 0)
        if mode == 'append_handle':
            flags |= os.O_APPEND
        fd = os.open(str(p), flags)
        try:
            count = positioned_write(fd, b'0007', 0)
        finally:
            os.close(fd)
        rows[mode] = {'write_count': count, 'bytes_after': p.read_bytes().decode(),
                      'size': p.stat().st_size, 'matches_expected': p.read_bytes() == b'0007:payload'}
    return rows


if __name__ == '__main__':
    result = {'system': platform.system(), 'machine': platform.machine(),
              'python': platform.python_version(), 'trials': []}
    for trial in range(3):
        with tempfile.TemporaryDirectory(prefix='envshift-positioned-') as temp:
            result['trials'].append(observe(Path(temp)))
    Path('positioned-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
