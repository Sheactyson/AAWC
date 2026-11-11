from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


MOD_NAME = "AAWC_Dependencies_Modpack"
EXPECTED_NAME = "AAWC Dependencies Modpack"
EXPECTED_VERSION = "1.1.2"
EXPECTED_GAME_VERSION = "1.19.0.6"
EXPECTED_GAMEPLAY_FILES = 1538
EXPECTED_AUXILIARY_FILES = 180
EXPECTED_AUXILIARY_PATHS_SHA256 = "7EBDA8D490270EB75E66563D1D55C2BA7C7E8F351C41911723A8292EB65FD212"
EXPECTED_LOV_EXACT_FILES = 1355
EXPECTED_LOV_EXACT_PATHS_SHA256 = "EC21AC756C213DD6C81DAE12359290F400D2D71F5C4306F5D1E992740C35C0C2"
EXPECTED_LOV_RELOCATED_FILES = 3
EXPECTED_LOV_RELOCATED_PATHS_SHA256 = "F1DB71D6C3F93A983A39658E280D7CF6CF815F1B92A492D5234C849C707A47B2"
LOV_RELOCATIONS = {
    "gfx/models/artifacts/throne/lokiria_throne_diffuse.dds":
        "gfx/models/court/materials/lokiria/lokiria_throne_diffuse.dds",
    "gfx/models/artifacts/throne/lokiria_throne_normal.dds":
        "gfx/models/court/materials/lokiria/lokiria_throne_normal.dds",
    "gfx/models/artifacts/throne/lokiria_throne_properties.dds":
        "gfx/models/court/materials/lokiria/lokiria_throne_properties.dds",
}
TEXT_EXTENSIONS = {".asset", ".gfx", ".gui", ".map", ".mod", ".txt", ".yml", ".md"}
STRUCTURAL_EXTENSIONS = {".asset", ".gfx", ".gui", ".txt"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def values(text: str, key: str) -> list[str]:
    return re.findall(rf'^\s*{re.escape(key)}\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)


def dependencies(text: str) -> list[str]:
    match = re.search(r"dependencies\s*=\s*\{([^}]*)\}", text, flags=re.DOTALL)
    return re.findall(r'"([^"]+)"', match.group(1)) if match else []


def structural_error(path: Path) -> str | None:
    depth = 0
    in_quote = False
    escaped = False
    for line_number, line in enumerate(read_text(path).splitlines(), 1):
        for char in line:
            if in_quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_quote = False
            elif char == "#":
                break
            elif char == '"':
                in_quote = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth < 0:
                    return f"negative brace depth at line {line_number}"
    if in_quote:
        return "unterminated quoted string"
    return f"final brace depth is {depth}" if depth else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def tree_hash(files: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix().lower()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()


def path_set_hash(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(value.lower() for value in paths):
        digest.update(path.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the independent AAWC Dependencies Modpack source and archive.")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--lov", type=Path, required=True, help="Pinned Legacy of Valyria 1.5.2.13 source root.")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--installed", type=Path)
    args = parser.parse_args()

    root = args.workspace.resolve()
    lov = args.lov.resolve()
    outer_path = root.parent / f"{MOD_NAME}.mod"
    files = [path for path in root.rglob("*") if path.is_file()]
    gameplay_files = [path for path in files if path.name not in {"descriptor.mod", "AAWC_DEPENDENCIES_MODPACK_PROVENANCE.md"}]
    failures: list[str] = []
    report: dict[str, object] = {
        "file_count": len(files),
        "gameplay_file_count": len(gameplay_files),
        "tree_sha256": tree_hash(files, root),
        "failures": failures,
    }
    if len(gameplay_files) != EXPECTED_GAMEPLAY_FILES:
        failures.append(f"expected {EXPECTED_GAMEPLAY_FILES} gameplay/support files, found {len(gameplay_files)}")

    descriptor_report: dict[str, object] = {}
    for label, path in (("inner", root / "descriptor.mod"), ("outer", outer_path)):
        if not path.is_file():
            failures.append(f"{label} descriptor is missing")
            continue
        text = read_text(path)
        descriptor_report[label] = {
            "name": values(text, "name"),
            "version": values(text, "version"),
            "supported_version": values(text, "supported_version"),
            "dependencies": dependencies(text),
        }
        if values(text, "name") != [EXPECTED_NAME] or values(text, "version") != [EXPECTED_VERSION]:
            failures.append(f"{label} descriptor identity/version is invalid")
        if values(text, "supported_version") != [EXPECTED_GAME_VERSION] or dependencies(text) != ["A Game of Thrones"]:
            failures.append(f"{label} descriptor target/dependency contract is invalid")
    report["descriptors"] = descriptor_report

    invalid_utf8: list[str] = []
    bad_structure: dict[str, str] = {}
    for path in files:
        if path.suffix.lower() in TEXT_EXTENSIONS:
            try:
                path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                invalid_utf8.append(path.relative_to(root).as_posix())
        if path.suffix.lower() in STRUCTURAL_EXTENSIONS:
            error = structural_error(path)
            if error:
                bad_structure[path.relative_to(root).as_posix()] = error
    report["encoding"] = {"invalid_utf8": invalid_utf8}
    report["structure"] = {"checked": sum(path.suffix.lower() in STRUCTURAL_EXTENSIONS for path in files), "failures": bad_structure}
    if invalid_utf8 or bad_structure:
        failures.append("encoding or structural validation failed")

    relative_paths = {path.relative_to(root).as_posix() for path in files}
    required = {
        "common/on_action/00_aawc_alternate_world_on_actions.txt",
        "common/on_action/00_kei_cafg_on_actions.txt",
        "common/on_action/zz_kei_cafg_on_actions.txt",
        "common/on_action/kei_cafg_county_on_actions.txt",
        "common/scripted_effects/aawc_alternate_world_effects.txt",
        "common/scripted_effects/kei_cafg_county_culture_effects.txt",
        "common/scripted_effects/kei_cafg_county_faith_effects.txt",
        "common/landed_titles/kei_cafg_granularity_map_mode_landed_titles.txt",
        "common/landed_titles/kei_cafg_tension_map_mode_landed_titles.txt",
        "data_binding/kei_ecv_compatibility_macros.txt",
        "gui/kei_ecv_templates.gui",
        "localization/english/aawc_alternate_world_l_english.yml",
    }
    missing_required = sorted(required - relative_paths)
    if missing_required:
        failures.append(f"missing {len(missing_required)} required middle-layer paths")
    lov_exact_paths: list[str] = []
    lov_relocated_paths: list[str] = []
    auxiliary_paths: list[str] = []
    invalid_lov_paths: list[str] = []
    for path in gameplay_files:
        relative = path.relative_to(root).as_posix()
        source = lov / relative
        if source.is_file():
            if sha256(path) == sha256(source):
                lov_exact_paths.append(relative)
            else:
                invalid_lov_paths.append(relative)
            continue
        relocated_source = LOV_RELOCATIONS.get(relative)
        if relocated_source:
            source = lov / relocated_source
            if source.is_file() and sha256(path) == sha256(source):
                lov_relocated_paths.append(relative)
            else:
                invalid_lov_paths.append(relative)
            continue
        auxiliary_paths.append(relative)
    ownership_counts = {
        "auxiliary": len(auxiliary_paths),
        "lov_byte_exact": len(lov_exact_paths),
        "lov_relocated_byte_exact": len(lov_relocated_paths),
    }
    ownership_hashes = {
        "auxiliary": path_set_hash(auxiliary_paths),
        "lov_byte_exact": path_set_hash(lov_exact_paths),
        "lov_relocated_byte_exact": path_set_hash(lov_relocated_paths),
    }
    if len(auxiliary_paths) != EXPECTED_AUXILIARY_FILES or ownership_hashes["auxiliary"] != EXPECTED_AUXILIARY_PATHS_SHA256:
        failures.append("controlled auxiliary dependency path inventory drifted")
    if len(lov_exact_paths) != EXPECTED_LOV_EXACT_FILES or ownership_hashes["lov_byte_exact"] != EXPECTED_LOV_EXACT_PATHS_SHA256:
        failures.append("byte-exact LoV middle-layer path inventory drifted")
    if len(lov_relocated_paths) != EXPECTED_LOV_RELOCATED_FILES or ownership_hashes["lov_relocated_byte_exact"] != EXPECTED_LOV_RELOCATED_PATHS_SHA256:
        failures.append("relocated byte-exact LoV asset inventory drifted")
    if invalid_lov_paths:
        failures.append("AAWC-modified or otherwise non-exact LoV paths entered the dependencies package")
    report["ownership"] = {
        "missing_required": missing_required,
        "counts": ownership_counts,
        "path_set_sha256": ownership_hashes,
        "invalid_lov_paths": sorted(invalid_lov_paths),
    }

    all_text = "\n".join(read_text(path) for path in files if path.suffix.lower() in {".txt", ".gui", ".yml"})
    contracts = {
        "aawc_alternate_world_game_start": 1,
        "on_kCAFG_start_early": 1,
        "on_kCAFG_start_late": 1,
        "E_kCAFG_update_county_culture": 1,
        "E_kCAFG_update_county_faith": 1,
        "kECVCompatProvinceNotEmpty": 1,
    }
    contract_counts = {name: len(re.findall(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", all_text)) for name in contracts}
    if any(contract_counts[name] < minimum for name, minimum in contracts.items()):
        failures.append("required middle-layer hook/API contract is missing")
    forbidden_tokens = {token: all_text.count(token) for token in ("Rite.", "GetRite", "kCAFG_rites", "mgr_")}
    if any(forbidden_tokens.values()):
        failures.append("forbidden CK3 1.20 or pre-remap contract remains")
    report["contracts"] = contract_counts
    report["forbidden_contracts"] = forbidden_tokens

    if args.archive:
        archive_path = args.archive.resolve()
        with zipfile.ZipFile(archive_path) as archive:
            names = [entry.filename for entry in archive.infolist()]
            roots = sorted({name.split("/", 1)[0] for name in names if name})
            bad_entry = archive.testzip()
            source_entries = {f"{MOD_NAME}/{path.relative_to(root).as_posix()}": path.read_bytes() for path in files}
            source_entries[f"{MOD_NAME}.mod"] = outer_path.read_bytes()
            archive_entries = {name: archive.read(name) for name in names}
        missing = sorted(set(source_entries) - set(archive_entries))
        extra = sorted(set(archive_entries) - set(source_entries))
        changed = sorted(name for name in set(source_entries) & set(archive_entries) if source_entries[name] != archive_entries[name])
        report["archive"] = {
            "path": str(archive_path), "sha256": sha256(archive_path), "entries": len(names),
            "roots": roots, "bad_crc_entry": bad_entry, "missing": missing, "extra": extra, "changed": changed,
        }
        if roots != [MOD_NAME, f"{MOD_NAME}.mod"] or bad_entry or missing or extra or changed or any("\\" in name for name in names):
            failures.append("archive integrity or source parity failed")

    if args.installed:
        installed = args.installed.resolve()
        installed_files = {path.relative_to(installed).as_posix(): path.read_bytes() for path in installed.rglob("*") if path.is_file()}
        source_files = {path.relative_to(root).as_posix(): path.read_bytes() for path in files}
        missing = sorted(set(source_files) - set(installed_files))
        extra = sorted(set(installed_files) - set(source_files))
        changed = sorted(name for name in set(source_files) & set(installed_files) if source_files[name] != installed_files[name])
        report["installed"] = {"path": str(installed), "missing": missing, "extra": extra, "changed": changed}
        if missing or extra or changed:
            failures.append("live installation parity failed")

    report["passed"] = not failures
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
