from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile


TEXT_EXTENSIONS = {".asset", ".gfx", ".gui", ".map", ".mod", ".txt", ".yml"}
STRUCTURAL_EXTENSIONS = {".asset", ".gfx", ".gui", ".txt"}
EXPECTED_DEPENDENCIES = ["A Game of Thrones", "AAWC Dependencies Modpack"]
EXPECTED_GAME_VERSION = "1.19.0.6"


def decoded(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def code_line(line: str, in_quote: bool) -> tuple[str, bool]:
    result: list[str] = []
    escaped = False
    for char in line:
        if in_quote:
            result.append(" ")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_quote = False
        else:
            if char == "#":
                break
            if char == '"':
                in_quote = True
                result.append(" ")
            else:
                result.append(char)
    return "".join(result), in_quote


def structural_error(path: Path) -> str | None:
    depth = 0
    in_quote = False
    for line_number, line in enumerate(decoded(path).splitlines(), 1):
        clean, in_quote = code_line(line, in_quote)
        for char in clean:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth < 0:
                    return f"negative brace depth at line {line_number}"
    if in_quote:
        return "unterminated quoted string"
    if depth:
        return f"final brace depth is {depth}"
    return None


def top_level_definitions(directory: Path) -> dict[str, list[str]]:
    definitions: dict[str, list[str]] = defaultdict(list)
    if not directory.is_dir():
        return definitions
    for path in directory.rglob("*.txt"):
        depth = 0
        in_quote = False
        for line_number, line in enumerate(decoded(path).splitlines(), 1):
            clean, in_quote = code_line(line, in_quote)
            if depth == 0:
                match = re.match(r"^\s*([A-Za-z0-9_.:@-]+)\s*=\s*\{", clean)
                if match:
                    definitions[match.group(1)].append(
                        f"{path.as_posix()}:{line_number}"
                    )
            depth += clean.count("{") - clean.count("}")
    return definitions


def descriptor_values(text: str, key: str) -> list[str]:
    return re.findall(
        rf'^\s*{re.escape(key)}\s*=\s*"([^"]+)"', text, flags=re.MULTILINE
    )


def descriptor_dependencies(text: str) -> list[str]:
    match = re.search(r"dependencies\s*=\s*\{([^}]*)\}", text, flags=re.DOTALL)
    return re.findall(r'"([^"]+)"', match.group(1)) if match else []


def validate_archive(archive_path: Path, expected_version: str) -> dict[str, object]:
    expected_folder = "AGOT_Alternate_World_Compatch"
    expected_descriptor = f"{expected_folder}.mod"
    with zipfile.ZipFile(archive_path) as archive:
        names = [info.filename for info in archive.infolist()]
        bad_separators = [name for name in names if "\\" in name]
        roots = sorted({name.split("/", 1)[0] for name in names if name})
        bad_crc = archive.testzip()
        descriptor = archive.read(f"{expected_folder}/descriptor.mod").decode("utf-8-sig")
        outer = archive.read(expected_descriptor).decode("utf-8-sig")
    return {
        "path": str(archive_path),
        "entries": len(names),
        "roots": roots,
        "bad_separators": bad_separators,
        "bad_crc_entry": bad_crc,
        "inner_version": descriptor_values(descriptor, "version"),
        "outer_version": descriptor_values(outer, "version"),
        "version_matches": descriptor_values(descriptor, "version")
        == [expected_version]
        and descriptor_values(outer, "version") == [expected_version],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--agot", type=Path, required=True)
    parser.add_argument(
        "--dependency-modpack",
        type=Path,
        help="AAWC Dependencies Modpack source root used for effective reference closure.",
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()

    root = args.workspace.resolve()
    agot = args.agot.resolve()
    dependency_modpack = (
        args.dependency_modpack.resolve()
        if args.dependency_modpack
        else root.parent / "AAWC_Dependencies_Modpack"
    )
    outer_path = root.parent / f"{root.name}.mod"
    files = [path for path in root.rglob("*") if path.is_file()]
    report: dict[str, object] = {"file_count": len(files), "failures": []}
    failures: list[str] = report["failures"]  # type: ignore[assignment]

    invalid_utf8: list[str] = []
    double_bom: list[str] = []
    localization_header: list[str] = []
    localization_tabs: list[str] = []
    bom_counts: Counter[str] = Counter()
    for path in files:
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        data = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        bom_counts["with_bom" if data.startswith(b"\xef\xbb\xbf") else "without_bom"] += 1
        if data.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"):
            double_bom.append(relative)
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            invalid_utf8.append(relative)
            continue
        if path.suffix.lower() == ".yml":
            if not text.startswith("l_english:"):
                localization_header.append(relative)
            if "\t" in text:
                localization_tabs.append(relative)
    report["encoding"] = {
        "bom_counts": dict(bom_counts),
        "invalid_utf8": invalid_utf8,
        "double_bom": double_bom,
        "bad_localization_headers": localization_header,
        "localization_tabs": localization_tabs,
    }
    if invalid_utf8 or double_bom or localization_header or localization_tabs:
        failures.append("encoding/localization validation failed")

    structural_failures: dict[str, str] = {}
    structural_count = 0
    for path in files:
        if path.suffix.lower() not in STRUCTURAL_EXTENSIONS:
            continue
        structural_count += 1
        error = structural_error(path)
        if error:
            structural_failures[path.relative_to(root).as_posix()] = error
    report["structure"] = {
        "checked": structural_count,
        "failures": structural_failures,
    }
    if structural_failures:
        failures.append("structural validation failed")

    localization_keys: dict[str, list[str]] = defaultdict(list)
    for path in root.rglob("*.yml"):
        for line_number, line in enumerate(decoded(path).splitlines()[1:], 2):
            match = re.match(r"^\s*([^\s:#]+):\d*\s", line)
            if match:
                localization_keys[match.group(1)].append(
                    f"{path.relative_to(root).as_posix()}:{line_number}"
                )
    localization_duplicates = {
        key: locations
        for key, locations in localization_keys.items()
        if len(locations) > 1
    }
    report["localization_ids"] = {
        "count": len(localization_keys),
        "duplicates": localization_duplicates,
    }
    if localization_duplicates:
        failures.append("duplicate localization IDs found")

    common_duplicates: dict[str, list[str]] = {}
    common = root / "common"
    for namespace in sorted(path for path in common.iterdir() if path.is_dir()):
        definitions = top_level_definitions(namespace)
        for key, locations in definitions.items():
            if len(locations) > 1:
                common_duplicates[f"{namespace.name}:{key}"] = locations
    # CK3 intentionally composes on_actions and define groups across files. AAWC's
    # generated building-effect overlay and late compatibility files also replace
    # same-named objects by design. Report every collision, but fail only collisions
    # outside those documented ownership mechanisms.
    intentional_fragments = (
        "/zzzz_aawc_population_building_effects.txt:",
        "/zzzz_aawc_kei_cafg_agot_compat_",
        "/kei_cafg_tcm_compatibility_",
        "/lv_agot_trigger_overrides.txt:",
        "/placeholder_entries_essos.txt:",
        "/zz_cob_custom_coa.txt:",
        "/zz_cob_characters_valyrian.txt:",
    )
    expected_duplicate_namespaces = {"defines", "genes", "on_action"}
    unexpected_common_duplicates = {
        key: locations
        for key, locations in common_duplicates.items()
        if key.split(":", 1)[0] not in expected_duplicate_namespaces
        and not any(
            fragment in location
            for location in locations
            for fragment in intentional_fragments
        )
    }
    report["common_ids"] = {
        "all_duplicates": common_duplicates,
        "unexpected_duplicates": unexpected_common_duplicates,
    }
    if unexpected_common_duplicates:
        failures.append("unexpected duplicate top-level common IDs found")

    inner_path = root / "descriptor.mod"
    inner = decoded(inner_path)
    outer = decoded(outer_path)
    descriptor_report = {
        "inner_version": descriptor_values(inner, "version"),
        "outer_version": descriptor_values(outer, "version"),
        "inner_supported_version": descriptor_values(inner, "supported_version"),
        "outer_supported_version": descriptor_values(outer, "supported_version"),
        "inner_dependencies": descriptor_dependencies(inner),
        "outer_dependencies": descriptor_dependencies(outer),
        "inner_replace_path": descriptor_values(inner, "replace_path"),
        "outer_replace_path": descriptor_values(outer, "replace_path"),
        "inner_has_bom": inner_path.read_bytes().startswith(b"\xef\xbb\xbf"),
        "outer_has_bom": outer_path.read_bytes().startswith(b"\xef\xbb\xbf"),
    }
    report["descriptors"] = descriptor_report
    if not (
        descriptor_report["inner_version"] == [args.version]
        and descriptor_report["outer_version"] == [args.version]
        and descriptor_report["inner_supported_version"] == [EXPECTED_GAME_VERSION]
        and descriptor_report["outer_supported_version"] == [EXPECTED_GAME_VERSION]
        and descriptor_report["inner_dependencies"] == EXPECTED_DEPENDENCIES
        and descriptor_report["outer_dependencies"] == EXPECTED_DEPENDENCIES
        and descriptor_report["inner_replace_path"]
        == descriptor_report["outer_replace_path"]
        == ["common/culture/eras", "common/defines"]
        and not descriptor_report["inner_has_bom"]
        and not descriptor_report["outer_has_bom"]
    ):
        failures.append("descriptor contract validation failed")

    replace_paths: list[dict[str, object]] = []
    for relative in descriptor_report["inner_replace_path"]:
        aawc_path = root / relative
        agot_path = agot / relative
        replace_paths.append(
            {
                "path": relative,
                "aawc_exists": aawc_path.is_dir(),
                "aawc_files": sum(path.is_file() for path in aawc_path.rglob("*")),
                "agot_exists": agot_path.is_dir(),
                "agot_files": sum(path.is_file() for path in agot_path.rglob("*")),
            }
        )
    report["replace_paths"] = replace_paths
    if any(not item["aawc_exists"] for item in replace_paths):
        failures.append("replace_path target missing")

    building_definitions = set(top_level_definitions(root / "common" / "buildings"))
    building_definitions.update(top_level_definitions(dependency_modpack / "common" / "buildings"))
    building_definitions.update(top_level_definitions(agot / "common" / "buildings"))
    maa_definitions = set(top_level_definitions(root / "common" / "men_at_arms_types"))
    maa_definitions.update(top_level_definitions(dependency_modpack / "common" / "men_at_arms_types"))
    maa_definitions.update(top_level_definitions(agot / "common" / "men_at_arms_types"))
    script_text = "\n".join(
        decoded(path)
        for path in files
        if path.suffix.lower() in {".txt", ".gui"}
    )
    building_references = set(
        re.findall(
            r"(?m)^\s*(?:building|add_building|remove_building|has_building|"
            r"has_building_or_higher|can_construct_building)\s*=\s*([A-Za-z0-9_.-]+)",
            script_text,
        )
    )
    maa_references = set(
        re.findall(
            r"(?m)^\s*(?:men_at_arms_type|has_men_at_arms|add_men_at_arms)"
            r"\s*=\s*([A-Za-z0-9_.-]+)",
            script_text,
        )
    )
    reference_report = {
        "dependency_modpack": str(dependency_modpack),
        "building_definitions": len(building_definitions),
        "building_references": len(building_references),
        "missing_buildings": sorted(building_references - building_definitions),
        "maa_definitions": len(maa_definitions),
        "maa_references": len(maa_references),
        "missing_maa": sorted(maa_references - maa_definitions),
    }
    report["references"] = reference_report
    if reference_report["missing_buildings"] or reference_report["missing_maa"]:
        failures.append("building or MAA reference closure failed")

    generated: dict[str, object] = {}
    for relative in (
        "common/buildings/zz_aawc_generated_special_building_chains.txt",
        "common/scripted_effects/zzzz_aawc_population_maa_cost_effects.txt",
    ):
        path = root / relative
        if not path.is_file():
            generated[relative] = {"missing": True}
            failures.append(f"missing generated file: {relative}")
            continue
        data = path.read_bytes()
        generated[relative] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "bom": data.startswith(b"\xef\xbb\xbf"),
            "double_bom": data.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"),
            "top_level_definitions": len(top_level_definitions(path.parent))
            if path.name.startswith("zz_aawc_generated_special")
            else None,
        }
    report["generated"] = generated

    contracts = {
        "kECVCompatProvinceNotEmpty": 1,
        "kECVCompatDisplayHolder": 1,
        "kECVCompatProvinceHasHolder": 1,
        "kei_Compat_IsModLoaded_AGOT": 1,
        "kei_Compat_IsModLoaded_kCAFG": 1,
        "ECVBaronyTabsSplit3": 1,
        "ECVBaronyTabsCompact": 1,
        "kECVCompatDisplayGarrison": 1,
        "E_kCAFG_update_county_culture": 1,
        "E_kCAFG_update_county_faith": 1,
        "adding_building_slot_interaction": 1,
        "extra_building_slot": 1,
    }
    contract_counts = {
        contract: len(
            re.findall(
                rf"(?<![A-Za-z0-9_]){re.escape(contract)}(?![A-Za-z0-9_])",
                script_text,
            )
        )
        for contract in contracts
    }
    report["integrated_contract_mentions"] = contract_counts
    for contract, minimum in contracts.items():
        if contract_counts[contract] < minimum:
            failures.append(f"missing integrated contract: {contract}")

    forbidden = ("Rite.", "GetRite", "mbrxxx_", "Bruce_", "cow3.", "mgr_")
    forbidden_counts = {token: script_text.count(token) for token in forbidden}
    report["forbidden_contract_mentions"] = forbidden_counts
    if any(forbidden_counts.values()):
        failures.append("forbidden external contract residue found")

    if args.archive:
        report["archive"] = validate_archive(args.archive.resolve(), args.version)
        archive_report = report["archive"]
        if (
            archive_report["roots"]
            != ["AGOT_Alternate_World_Compatch", "AGOT_Alternate_World_Compatch.mod"]
            or archive_report["bad_separators"]
            or archive_report["bad_crc_entry"]
            or not archive_report["version_matches"]
        ):
            failures.append("archive validation failed")

    report["passed"] = not failures
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
