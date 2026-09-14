"""Restore original screenshots from a repository checkout, with no network or model calls."""
import hashlib, json, pathlib, tarfile

root=pathlib.Path(__file__).resolve().parent
for path in sorted((root/'archives').glob('*.tar.xz')):
    dest=root/'evidence'/path.name[:-7];dest.mkdir(parents=True,exist_ok=True)
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
