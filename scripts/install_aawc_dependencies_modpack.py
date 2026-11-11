from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from aawc_paths import RELEASE_ROOT, default_mod_dir


MOD_NAME = "AAWC_Dependencies_Modpack"
ZIP_RE = re.compile(rf"^{MOD_NAME}_(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?\.zip$", re.IGNORECASE)
DEFAULT_RELEASES = RELEASE_ROOT
DEFAULT_MOD_DIR = default_mod_dir()


def latest_archive(root: Path) -> Path:
    candidates: list[tuple[tuple[int, ...], Path]] = []
    for path in root.glob("AAWC_Dependencies_Modpack_*.zip"):
        match = ZIP_RE.match(path.name)
        if match:
            candidates.append((tuple(int(value) for value in match.groups() if value is not None), path))
    if not candidates:
        raise RuntimeError(f"No versioned dependencies archive was found under {root}")
    return max(candidates, key=lambda item: item[0])[1]


def validate_layout(archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        names = [entry.filename for entry in archive.infolist()]
        roots = {name.split("/", 1)[0] for name in names if name}
        if roots != {MOD_NAME, f"{MOD_NAME}.mod"}:
            raise RuntimeError(f"Unexpected archive roots: {sorted(roots)}")
        for required in (f"{MOD_NAME}/descriptor.mod", f"{MOD_NAME}/AAWC_DEPENDENCIES_MODPACK_PROVENANCE.md"):
            if required not in names:
                raise RuntimeError(f"Archive is missing {required}")
        bad_entry = archive.testzip()
        if bad_entry:
            raise RuntimeError(f"Archive CRC failure: {bad_entry}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install only the independently versioned AAWC Dependencies Modpack.")
    parser.add_argument("archive", nargs="?", type=Path)
    parser.add_argument("--releases", type=Path, default=DEFAULT_RELEASES)
    parser.add_argument("--mod-dir", type=Path, default=DEFAULT_MOD_DIR)
    args = parser.parse_args()

    archive_path = args.archive.resolve() if args.archive else latest_archive(args.releases.resolve())
    validate_layout(archive_path)
    mod_dir = args.mod_dir.resolve()
    target_folder = mod_dir / MOD_NAME
    target_descriptor = mod_dir / f"{MOD_NAME}.mod"

    with tempfile.TemporaryDirectory(prefix="aawc_dependencies_install_") as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(staging)
        staged_folder = staging / MOD_NAME
        staged_descriptor = staging / f"{MOD_NAME}.mod"
        if not staged_folder.is_dir() or not staged_descriptor.is_file():
            raise RuntimeError("Staged dependencies package is incomplete")
        mod_dir.mkdir(parents=True, exist_ok=True)
        if target_folder.exists():
            shutil.rmtree(target_folder)
        if target_descriptor.exists():
            target_descriptor.unlink()
        shutil.copytree(staged_folder, target_folder)
        shutil.copy2(staged_descriptor, target_descriptor)

    print(f"archive={archive_path}")
    print(f"installed_folder={target_folder}")
    print(f"installed_descriptor={target_descriptor}")


if __name__ == "__main__":
    main()
