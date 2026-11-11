from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile

from aawc_paths import MOD_SOURCE_ROOT, RELEASE_ROOT


MOD_NAME = "AGOT_Alternate_World_Compatch"
VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"', re.MULTILINE)


def read_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    match = VERSION_RE.search(text)
    if not match:
        raise RuntimeError(f"No version was found in {path}")
    return match.group(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an AAWC release zip with normalized POSIX entry paths."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=MOD_SOURCE_ROOT,
        help="Directory containing the current mod folder and outer descriptor.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RELEASE_ROOT,
        help="Single-current-release output directory.",
    )
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    mod_folder = source_root / MOD_NAME
    outer_descriptor = source_root / f"{MOD_NAME}.mod"
    inner_descriptor = mod_folder / "descriptor.mod"
    for required in (mod_folder, outer_descriptor, inner_descriptor):
        if not required.exists():
            raise RuntimeError(f"Required release input is missing: {required}")

    inner_version = read_version(inner_descriptor)
    outer_version = read_version(outer_descriptor)
    if inner_version != outer_version:
        raise RuntimeError(
            f"Descriptor versions differ: inner={inner_version}, outer={outer_version}"
        )
    version = inner_version
    output_directory = args.output.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"{MOD_NAME}_{version}.zip"
    manifest_path = output_directory / f"{MOD_NAME}_{version}.manifest.sha256"

    # Git is the release history. Keep only the current package in this checkout.
    for pattern in (f"{MOD_NAME}_*.zip", f"{MOD_NAME}_*.manifest.sha256"):
        for stale in output_directory.glob(pattern):
            if stale not in (output_path, manifest_path):
                stale.unlink()

    inputs = [(outer_descriptor, PurePosixPath(outer_descriptor.name))]
    inputs.extend(
        (path, PurePosixPath(MOD_NAME, *path.relative_to(mod_folder).parts))
        for path in sorted(mod_folder.rglob("*"))
        if path.is_file()
    )

    with tempfile.NamedTemporaryFile(
        prefix=f"{MOD_NAME}_{version}_", suffix=".zip", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(
            temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for source, archive_name in inputs:
                archive.write(source, archive_name.as_posix())
        with zipfile.ZipFile(temporary_path) as archive:
            names = [entry.filename for entry in archive.infolist()]
            if any("\\" in name for name in names):
                raise RuntimeError("Archive contains a non-POSIX entry path")
            expected_roots = {MOD_NAME, f"{MOD_NAME}.mod"}
            roots = {name.split("/", 1)[0] for name in names}
            if roots != expected_roots:
                raise RuntimeError(f"Unexpected archive roots: {sorted(roots)}")
            bad_entry = archive.testzip()
            if bad_entry:
                raise RuntimeError(f"Archive CRC failure: {bad_entry}")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    manifest_lines = []
    for source, archive_name in inputs:
        digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        manifest_lines.append(f"{digest}  {archive_name.as_posix()}")
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8", newline="\n")

    print(output_path)
    print(manifest_path)
    print(f"version={version}")
    print(f"entries={len(inputs)}")


if __name__ == "__main__":
    main()
