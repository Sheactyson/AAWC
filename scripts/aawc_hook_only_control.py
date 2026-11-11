"""Build and independently verify the approved one-statement CK3 control.

This produces a test artifact only. It never edits source or installation and
cannot certify runtime behavior, state matching, or performance by itself.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


PARENT_SHA256 = '34E32A6E0C3378A960B32B11DCD577BEC495BD6F08AF8E08A6617BEEDAAB73B8'
PARENT_MANIFEST_SHA256 = 'DAB4F14C9D763B270107F3D5C0F10AEF93BE3944B7EED208628091C910315603'
PAYLOAD_PATH = 'AGOT_Alternate_World_Compatch/common/scripted_effects/aawc_reforging_cohort_production_effects.txt'
WRAPPER = b'aawc_reforging_cohort_apply_production_month_effect'
STATEMENT = b'aawc_reforging_cohort_monthly_authority_effect = { TICK_ID = var:aawc_reforging_cohort_requested_tick }'


def sha256(data):
    return hashlib.sha256(data).hexdigest().upper()


def file_hash(path):
    return sha256(Path(path).read_bytes())


def read_archive(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise ValueError('duplicate archive entries')
        if any('\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
               or ':' in name or info.is_dir() for name, info in zip(names, infos)):
            raise ValueError('unsafe or non-payload archive entry')
        if archive.testzip():
            raise ValueError('archive CRC failure')
        return {name: archive.read(name) for name in names}


def check_manifest(payload, manifest):
    parsed = {}
    for line in Path(manifest).read_text(encoding='utf-8-sig').splitlines():
        match = re.fullmatch(r'([A-Fa-f0-9]{64})  (.+)', line)
        if not match or match[2] in parsed:
            raise ValueError('malformed or duplicate manifest entry')
        parsed[match[2]] = match[1].upper()
    actual = {name: sha256(data) for name, data in payload.items()}
    if parsed != actual:
        raise ValueError('archive/manifest payload mismatch')


def transform(data):
    """Omit exactly the reviewed invocation, preserving surrounding whitespace."""
    # Ignore commented/string braces when locating the containing definition.
    mask = bytearray(data)
    quoted = comment = escaped = False
    for i, char in enumerate(data):
        if comment:
            if char in (10, 13):
                comment = False
            else:
                mask[i] = 32
        elif quoted:
            mask[i] = 32
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 35:
            comment = True
            mask[i] = 32
        elif char == 34:
            quoted = True
            mask[i] = 32
    clean = bytes(mask)
    matches = list(re.finditer(rb'(?m)^' + WRAPPER + rb'\s*=\s*\{', clean))
    if len(matches) != 1:
        raise ValueError('expected exactly one production wrapper')
    begin = matches[0].end()
    depth = 1
    end = begin
    while end < len(clean) and depth:
        depth += (clean[end] == 123) - (clean[end] == 125)
        end += 1
    if depth:
        raise ValueError('unclosed production wrapper')
    body = clean[begin:end-1]
    if body.count(STATEMENT) != 1:
        raise ValueError('expected exactly one reviewed authority invocation inside wrapper')
    offset = begin + body.index(STATEMENT)
    return data[:offset] + data[offset+len(STATEMENT):], offset


def inspect_relationship(parent, child):
    if set(parent) != set(child):
        raise ValueError('control entries differ from parent')
    changed = [name for name in parent if parent[name] != child[name]]
    if changed != [PAYLOAD_PATH]:
        raise ValueError('control changes more or less than the approved payload')
    expected, offset = transform(parent[PAYLOAD_PATH])
    if child[PAYLOAD_PATH] != expected:
        raise ValueError('control is not the exact approved one-statement omission')
    return dict(entries=len(parent), unchanged_entries=len(parent)-1,
                changed_entry=PAYLOAD_PATH, byte_offset=offset,
                omitted_bytes=len(STATEMENT), parent_payload_sha256=sha256(parent[PAYLOAD_PATH]),
                child_payload_sha256=sha256(child[PAYLOAD_PATH]))


def artifact(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=file_hash(path), bytes=path.stat().st_size)


def derived_archive_bytes(parent_archive):
    """Reproduce the entire child container from pinned parent metadata and bytes."""
    parent = read_archive(parent_archive)
    replacement, _ = transform(parent[PAYLOAD_PATH])
    buffer = io.BytesIO()
    with zipfile.ZipFile(parent_archive) as source, zipfile.ZipFile(buffer, 'w', compresslevel=9) as target:
        target.comment = source.comment
        for item in source.infolist():
            content = replacement if item.filename == PAYLOAD_PATH else parent[item.filename]
            target.writestr(copy.copy(item), content, compress_type=item.compress_type, compresslevel=9)
    return buffer.getvalue()


def verify_record(path):
    record = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if record.get('schema') != 1 or record.get('transformation') != 'omit_reviewed_monthly_authority_invocation':
        raise ValueError('unrecognized derivation contract')
    for side in ('parent', 'child'):
        for kind in ('archive', 'manifest'):
            item = record[side][kind]
            if file_hash(item['path']) != item['sha256'] or Path(item['path']).stat().st_size != item['bytes']:
                raise ValueError(f'{side}/{kind}: artifact identity mismatch')
    if (record['parent']['archive']['sha256'] != PARENT_SHA256
            or record['parent']['manifest']['sha256'] != PARENT_MANIFEST_SHA256):
        raise ValueError('parent is not the approved candidate')
    if record['parent']['archive']['sha256'] == record['child']['archive']['sha256']:
        raise ValueError('parent and child must have distinct hashes')
    parent = read_archive(record['parent']['archive']['path'])
    child = read_archive(record['child']['archive']['path'])
    for side, payload in (('parent', parent), ('child', child)):
        check_manifest(payload, record[side]['manifest']['path'])
    actual = inspect_relationship(parent, child)
    if actual != record['verification']:
        raise ValueError('derivation summary disagrees with independently compared bytes')
    if sha256(derived_archive_bytes(record['parent']['archive']['path'])) != record['child']['archive']['sha256']:
        raise ValueError('child container does not reproduce from pinned parent metadata and transform')
    return dict(verified=True, **actual, parent_sha256=record['parent']['archive']['sha256'],
                child_sha256=record['child']['archive']['sha256'])


def build(parent_archive, parent_manifest, destination):
    if file_hash(parent_archive) != PARENT_SHA256 or file_hash(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise ValueError('parent identity is not approved')
    parent = read_archive(parent_archive)
    check_manifest(parent, parent_manifest)
    child_bytes = derived_archive_bytes(parent_archive)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    child_archive = destination / 'AAWC_1.11.1.0_hook_only_control.zip'
    child_manifest = destination / 'AAWC_1.11.1.0_hook_only_control.manifest.sha256'
    record_path = destination / 'derivation-manifest.json'
    with child_archive.open('xb') as target:
        target.write(child_bytes)
    child = read_archive(child_archive)
    child_manifest.write_text(''.join(f'{sha256(data)}  {name}\n' for name, data in child.items()), encoding='utf-8', newline='\n')
    record = dict(schema=1, created_utc=datetime.now(timezone.utc).isoformat(),
        transformation='omit_reviewed_monthly_authority_invocation',
        authority='User-approved hook-only paired-performance package, 2026-10-27',
        measurement_scope='Recurring birth/mortality/aging authority and its internal diagnostics; not total cohort-system cost.',
        parent=dict(archive=artifact(parent_archive), manifest=artifact(parent_manifest)),
        child=dict(archive=artifact(child_archive), manifest=artifact(child_manifest)),
        builder=artifact(__file__), verification=inspect_relationship(parent, child),
        runtime_certified=False, installation_changed=False)
    record_path.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return record_path, verify_record(record_path)


def attach_control_derivation(performance, artifacts):
    """Discard asserted verification and derive it from pinned parent/child bytes."""
    control = performance.setdefault('control', {})
    control['derivation_verified'] = False
    control['derivation_problems'] = []
    path = control.get('derivation_manifest')
    try:
        if not path or path not in artifacts or file_hash(path) != artifacts[path]:
            raise ValueError('derivation manifest is absent or not hash-pinned')
        record = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        for side in ('parent', 'child'):
            for kind in ('archive', 'manifest'):
                ref = record[side][kind]
                if artifacts.get(ref['path']) != ref['sha256']:
                    raise ValueError('referenced parent/child artifact is not pinned in raw evidence')
        actual = verify_record(path)
        if control.get('sha256') != actual['child_sha256'] or performance.get('parent_sha256') != actual['parent_sha256']:
            raise ValueError('sample candidate/control identities differ from derivation')
        control['derivation_verified'] = True
        control['derived_relationship'] = actual
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        control['derivation_problems'].append(str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('build')
    make.add_argument('--parent-archive', type=Path, required=True)
    make.add_argument('--parent-manifest', type=Path, required=True)
    make.add_argument('--output', type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        path, output = build(args.parent_archive, args.parent_manifest, args.output)
        output['record'] = str(path)
    else:
        output = verify_record(args.record)
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
