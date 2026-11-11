from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


MOD_NAME = "AGOT_Alternate_World_Compatch"
VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"', re.MULTILINE)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def tree_payload(folder: Path, outer: Path) -> dict[str, bytes]:
    payload = {outer.name: outer.read_bytes()}
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            relative = path.relative_to(folder).as_posix()
            payload[f"{MOD_NAME}/{relative}"] = path.read_bytes()
    return payload


def differences(reference: dict[str, bytes], candidate: dict[str, bytes]) -> dict[str, list[str]]:
    reference_names = set(reference)
    candidate_names = set(candidate)
    shared = reference_names & candidate_names
    return {
        "missing": sorted(reference_names - candidate_names),
        "extra": sorted(candidate_names - reference_names),
        "changed": sorted(name for name in shared if reference[name] != candidate[name]),
    }


def descriptor_version(data: bytes) -> str | None:
    match = VERSION_RE.search(data.decode("utf-8-sig"))
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify exact AAWC source/archive/install parity.")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--install-root", type=Path,
                        help="Optional live installation comparison; omission certifies source/archive/manifest only.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    source_folder = workspace / MOD_NAME
    source_outer = workspace / f"{MOD_NAME}.mod"
    source = tree_payload(source_folder, source_outer)
    installed = None
    if args.install_root:
        install_root = args.install_root.resolve()
        installed = tree_payload(install_root / MOD_NAME, install_root / f"{MOD_NAME}.mod")
    with zipfile.ZipFile(args.archive) as archive_file:
        archive = {
            info.filename: archive_file.read(info)
            for info in archive_file.infolist()
            if not info.is_dir()
        }
        bad_crc = archive_file.testzip()

    manifest: dict[str, str] = {}
    malformed_manifest_lines: list[str] = []
    for line in args.manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9A-F]{64})  (.+)", line)
        if match:
            manifest[match.group(2)] = match.group(1)
        else:
            malformed_manifest_lines.append(line)
    expected_manifest = {name: sha256(data) for name, data in source.items()}

    source_archive = differences(source, archive)
    source_install = differences(source, installed) if installed is not None else None
    manifest_missing = sorted(set(expected_manifest) - set(manifest))
    manifest_extra = sorted(set(manifest) - set(expected_manifest))
    manifest_changed = sorted(
        name
        for name in set(expected_manifest) & set(manifest)
        if expected_manifest[name] != manifest[name]
    )
    versions = {
        "source_inner": descriptor_version(source[f"{MOD_NAME}/descriptor.mod"]),
        "source_outer": descriptor_version(source[f"{MOD_NAME}.mod"]),
        "archive_inner": descriptor_version(archive[f"{MOD_NAME}/descriptor.mod"]),
        "archive_outer": descriptor_version(archive[f"{MOD_NAME}.mod"]),
    }
    if installed is not None:
        versions.update({
            "installed_inner": descriptor_version(installed[f"{MOD_NAME}/descriptor.mod"]),
            "installed_outer": descriptor_version(installed[f"{MOD_NAME}.mod"]),
        })
    passed = (
        not any(source_archive.values())
        and (source_install is None or not any(source_install.values()))
        and not malformed_manifest_lines
        and not manifest_missing
        and not manifest_extra
        and not manifest_changed
        and bad_crc is None
        and set(versions.values()) == {args.version}
    )
    report = {
        "passed": passed,
        "installation_checked": installed is not None,
        "version": args.version,
        "counts": {
            "source": len(source),
            "archive": len(archive),
            "installed": len(installed) if installed is not None else None,
            "manifest": len(manifest),
        },
        "versions": versions,
        "source_to_archive": source_archive,
        "source_to_install": source_install,
        "manifest": {
            "malformed_lines": malformed_manifest_lines,
            "missing": manifest_missing,
            "extra": manifest_extra,
            "changed": manifest_changed,
        },
        "archive": {
            "path": str(args.archive.resolve()),
            "sha256": sha256(args.archive.read_bytes()),
            "bad_crc_entry": bad_crc,
        },
        "manifest_file": {
            "path": str(args.manifest.resolve()),
            "sha256": sha256(args.manifest.read_bytes()),
        },
    }
    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
