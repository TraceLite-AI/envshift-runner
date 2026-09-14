"""Restore both phases from local archives, with no network or model calls."""
import hashlib, json, pathlib, tarfile

root=pathlib.Path(__file__).resolve().parent
paths=sorted((root/'archives').glob('*.tar.xz'))+sorted((root/'diagnostics/window-fit/archives').glob('*.tar.xz'))
for path in paths:
    run,name=path.name[:-7].split('-',1)
    dest=path.parent.parent/'evidence'/run/name;dest.mkdir(parents=True,exist_ok=True)
    with tarfile.open(path,'r:xz') as tar:
        for member in tar.getmembers():
            rel=pathlib.PurePosixPath(member.name)
            assert not rel.is_absolute() and '..' not in rel.parts
            assert member.isfile() or member.isdir()
        tar.extractall(dest)
    manifest=json.loads((dest/'evidence/EVIDENCE_SHA256.json').read_text())
    for name,digest in manifest.items():
        rel=pathlib.PurePosixPath(name)
        assert not rel.is_absolute() and '..' not in rel.parts
        assert hashlib.sha256((dest/'evidence'/name).read_bytes()).hexdigest()==digest
    print(path.name,len(manifest),'files verified')
