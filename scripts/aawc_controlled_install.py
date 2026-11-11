"""Install one explicitly selected, hash-pinned candidate; never guess latest."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile

from verify_aawc_release_candidate import MOD_NAME, descriptor_version, tree_payload
from aawc_hook_only_control import verify_record as verify_derivation, read_archive
from aawc_paths import MOD_SOURCE_ROOT, default_mod_dir

ROOT = Path(__file__).resolve().parents[1]
MOD_DIR = default_mod_dir()
OUTER = MOD_NAME + '.mod'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def hashes(payload: dict[str, bytes]) -> dict[str, str]:
    return {name: digest(data) for name, data in sorted(payload.items())}


def assert_closed() -> None:
    if os.name == 'nt':
        result = subprocess.run(['powershell', '-NoProfile', '-Command',
            "@(Get-Process -Name ck3,dowser,'Paradox Launcher' -ErrorAction SilentlyContinue).Count"],
            capture_output=True, text=True, check=True)
        if result.stdout.strip() != '0':
            raise RuntimeError('Close CK3 and the Paradox launcher before installation/session changes')


def reject_links(path: Path) -> None:
    """Never follow junctions/reparse points during replacement or inventory."""
    for item in [path, *path.parents]:
        if item.exists() and (item.is_symlink() or
                getattr(item.lstat(), 'st_file_attributes', 0) & 0x400):
            raise RuntimeError(f'Reparse point is not an installation target: {item}')
    if path.is_dir():
        for item in path.rglob('*'):
            if item.is_symlink() or getattr(item.lstat(), 'st_file_attributes', 0) & 0x400:
                raise RuntimeError(f'Reparse point in tree: {item}')


def candidate_payload(archive: Path, manifest: Path, expected_sha256: str,
                      version: str, workspace: Path,
                      derivation_manifest: Path | None = None) -> tuple[dict[str, bytes], dict]:
    raw = archive.read_bytes()
    if not re.fullmatch(r'[a-fA-F0-9]{64}', expected_sha256) or digest(raw) != expected_sha256.upper():
        raise RuntimeError('Selected archive SHA-256 does not match the required pin')
    payload, seen = {}, set()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for info in z.infolist():
            name, parts = info.filename, PurePosixPath(info.filename).parts
            if ('\\' in name or not parts or name.startswith('/') or
                    any(p in ('..', '.') or ':' in p or p.endswith((' ', '.')) for p in parts) or
                    PurePosixPath(name).as_posix() != name.rstrip('/') or
                    parts[0] not in (MOD_NAME, OUTER) or
                    (parts[0] == OUTER and len(parts) != 1) or
                    stat.S_ISLNK(info.external_attr >> 16)):
                raise RuntimeError(f'Unsafe/unexpected archive entry: {name}')
            key = name.rstrip('/').casefold()
            if key in seen:
                raise RuntimeError(f'Duplicate/case-colliding archive entry: {name}')
            seen.add(key)
            if not info.is_dir():
                payload[name] = z.read(info)
    required = {OUTER, MOD_NAME + '/descriptor.mod'}
    if not required <= payload.keys():
        raise RuntimeError('Missing descriptors')
    for name in required:
        if descriptor_version(payload[name]) != version:
            raise RuntimeError(f'Descriptor version mismatch: {name}')
    entries, manifest_raw = {}, manifest.read_bytes()
    for line in manifest_raw.decode('utf-8').splitlines():
        match = re.fullmatch(r'([0-9A-Fa-f]{64})  (.+)', line)
        if not match or match[2] in entries:
            raise RuntimeError('Malformed or duplicate manifest entry')
        entries[match[2]] = match[1].upper()
    if entries != hashes(payload):
        raise RuntimeError('Manifest does not match the complete archive payload')
    reject_links(workspace / MOD_NAME)
    reject_links(workspace / OUTER)
    source = hashes(tree_payload(workspace / MOD_NAME, workspace / OUTER))
    derivation = {}
    if derivation_manifest is not None:
        checked = verify_derivation(derivation_manifest)
        record = json.loads(derivation_manifest.read_text(encoding='utf-8-sig'))
        if (checked['child_sha256'] != digest(raw)
                or record['child']['manifest']['sha256'] != digest(manifest_raw)
                or source != hashes(read_archive(record['parent']['archive']['path']))):
            raise RuntimeError('Derived control does not match the reviewed child and unchanged parent source')
        derivation = {'control_derivation': str(derivation_manifest.resolve()),
                      'control_derivation_sha256': digest(derivation_manifest.read_bytes()),
                      'parent_archive_sha256': checked['parent_sha256'],
                      'artifact_role': 'hook_only_performance_control'}
    elif source != entries:
        raise RuntimeError('Source/archive parity failed; candidate is stale or unrelated')
    return payload, {'archive': str(archive.resolve()), 'archive_sha256': digest(raw),
                     'manifest': str(manifest.resolve()), 'manifest_sha256': digest(manifest_raw),
                     'workspace': str(workspace.resolve()), 'version': version, 'entries': entries, **derivation}


def installed_hashes(mod_dir: Path) -> dict[str, str]:
    reject_links(mod_dir / MOD_NAME)
    reject_links(mod_dir / OUTER)
    return hashes(tree_payload(mod_dir / MOD_NAME, mod_dir / OUTER))


def install_candidate(archive: Path, manifest: Path, expected_sha256: str,
                      version: str, workspace: Path, mod_dir: Path, evidence: Path,
                      derivation_manifest: Path | None = None) -> dict:
    assert_closed()
    reject_links(mod_dir)
    mod_dir, evidence = mod_dir.resolve(), evidence.resolve()
    if evidence.exists() or evidence == mod_dir or mod_dir in evidence.parents:
        raise RuntimeError('Evidence destination must be new and outside the mod directory')
    payload, selection = candidate_payload(archive, manifest, expected_sha256, version, workspace, derivation_manifest)
    if workspace.resolve() == evidence or workspace.resolve() in evidence.parents:
        raise RuntimeError('Installation evidence must not contaminate the source workspace')
    for input_path in (archive.resolve(), manifest.resolve(), workspace.resolve()):
        if mod_dir == input_path or mod_dir in input_path.parents or input_path in mod_dir.parents:
            raise RuntimeError('Installation must not overlap source/archive inputs')
    evidence.mkdir(parents=True)
    backup = evidence / 'previous-install'
    backup.mkdir()
    mod_dir.mkdir(parents=True, exist_ok=True)
    prior = {}
    for name in (MOD_NAME, OUTER):
        target = mod_dir / name
        if target.exists():
            if target.is_dir():
                shutil.copytree(target, backup / name)
            else:
                shutil.copy2(target, backup / name)
            prior[name] = True
    selection.update({'install_root': str(mod_dir), 'recorded_utc': datetime.now(timezone.utc).isoformat(),
                      'status': 'validated', 'previous_install': str(backup)})
    receipt = evidence / 'selection.json'
    receipt.write_text(json.dumps(selection, indent=2) + '\n', encoding='utf-8')
    replaced = []
    with tempfile.TemporaryDirectory(prefix='.aawc-stage-', dir=mod_dir) as temporary:
        staged = Path(temporary)
        for name, data in payload.items():
            dest = staged.joinpath(*PurePosixPath(name).parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        if installed_hashes(staged) != selection['entries']:
            raise RuntimeError('Staging parity failed')
        assert_closed()
        try:
            for name in (MOD_NAME, OUTER):
                target = mod_dir / name
                assert target.parent == mod_dir and name in (MOD_NAME, OUTER)
                replaced.append(name)
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                shutil.move(str(staged / name), str(target))
            if installed_hashes(mod_dir) != selection['entries']:
                raise RuntimeError('Installed candidate differs from selected archive')
        except BaseException:
            for name in replaced:
                target = mod_dir / name
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                if name in prior:
                    if (backup / name).is_dir():
                        shutil.copytree(backup / name, target)
                    else:
                        shutil.copy2(backup / name, target)
            selection['status'] = 'rolled_back'
            receipt.write_text(json.dumps(selection, indent=2) + '\n', encoding='utf-8')
            raise
    selection.update(status='installed', installed_entries=len(payload))
    receipt.write_text(json.dumps(selection, indent=2) + '\n', encoding='utf-8')
    return selection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument(
        '--source-root', '--workspace', dest='source_root', type=Path,
        default=MOD_SOURCE_ROOT,
        help='Directory containing the current mod folder and outer descriptor.',
    )
    parser.add_argument('--mod-dir', type=Path, default=MOD_DIR)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--derivation-manifest', type=Path,
                        help='Approved hook-only child proof; source must still equal its pinned parent')
    args = parser.parse_args()
    result = install_candidate(args.archive, args.manifest, args.sha256, args.version,
                               args.source_root, args.mod_dir, args.evidence, args.derivation_manifest)
    print(json.dumps({k: v for k, v in result.items() if k != 'entries'}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
