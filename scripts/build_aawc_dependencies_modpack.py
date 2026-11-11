from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile

from aawc_paths import DEPENDENCIES_SOURCE_ROOT, RELEASE_ROOT


MOD_NAME = "AAWC_Dependencies_Modpack"
VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"', re.MULTILINE)
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def read_version(path: Path) -> str:
    match = VERSION_RE.search(path.read_text(encoding="utf-8-sig"))
    if not match:
        raise RuntimeError(f"No version was found in {path}")
    return match.group(1)


def add_file(archive: zipfile.ZipFile, source: Path, archive_name: PurePosixPath) -> None:
    info = zipfile.ZipInfo(archive_name.as_posix(), date_time=ZIP_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the deterministic AAWC Dependencies Modpack archive.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEPENDENCIES_SOURCE_ROOT,
        help="Directory containing the current dependency folder and outer descriptor.",
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
        raise RuntimeError(f"Descriptor versions differ: inner={inner_version}, outer={outer_version}")

    output_directory = args.output.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"{MOD_NAME}_{inner_version}.zip"
    for stale in output_directory.glob(f"{MOD_NAME}_*.zip"):
        if stale != output_path:
            stale.unlink()
    inputs = [(outer_descriptor, PurePosixPath(outer_descriptor.name))]
    inputs.extend(
        (path, PurePosixPath(MOD_NAME, *path.relative_to(mod_folder).parts))
        for path in sorted(mod_folder.rglob("*"), key=lambda item: item.relative_to(mod_folder).as_posix().lower())
        if path.is_file()
    )

    with tempfile.NamedTemporaryFile(prefix=f"{MOD_NAME}_{inner_version}_", suffix=".zip", delete=False) as handle:
        temporary_path = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary_path, "w") as archive:
            for source, archive_name in inputs:
                add_file(archive, source, archive_name)
        with zipfile.ZipFile(temporary_path) as archive:
            names = [entry.filename for entry in archive.infolist()]
            roots = {name.split("/", 1)[0] for name in names}
            if any("\\" in name for name in names):
                raise RuntimeError("Archive contains a non-POSIX entry path")
            if roots != {MOD_NAME, f"{MOD_NAME}.mod"}:
                raise RuntimeError(f"Unexpected archive roots: {sorted(roots)}")
            bad_entry = archive.testzip()
            if bad_entry:
                raise RuntimeError(f"Archive CRC failure: {bad_entry}")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(output_path)
    print(f"version={inner_version}")
    print(f"entries={len(inputs)}")


if __name__ == "__main__":
    main()
