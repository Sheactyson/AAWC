#!/usr/bin/env python3
"""Stage the exact Stage 1 AAWC payload in an isolated, workspace-owned profile.

The live CK3 profile and every upstream/dependency tree are read-only inputs.
Only the outer AAWC transport descriptor is rewritten so the isolated profile
loads the byte-identical staged AAWC payload instead of the stale live tree.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from aawc_paths import (
    DEPENDENCIES_SOURCE_ROOT,
    MOD_SOURCE_ROOT,
    PLAYTEST_ROOT,
    RELEASE_ROOT,
    configured_ck3_executable,
    default_mod_dir,
)


ROOT = Path(__file__).resolve().parents[1]
MOD_NAME = "AGOT_Alternate_World_Compatch"
WORKSPACE = MOD_SOURCE_ROOT
LIVE_MOD_ROOT = default_mod_dir()
DEFAULT_CK3 = configured_ck3_executable()
LOAD_ORDER = (
    "mod/ugc_2962333032.mod",
    "mod/AAWC_Dependencies_Modpack.mod",
    f"mod/{MOD_NAME}.mod",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def reject_links(path: Path) -> None:
    """Reject symlinks and Windows reparse points in an inventoried tree."""
    if not path.exists():
        return
    for item in (path, *path.rglob("*")):
        attributes = getattr(item.lstat(), "st_file_attributes", 0)
        if item.is_symlink() or attributes & 0x400:
            raise RuntimeError(f"linked/reparse path is not accepted: {item}")


def file_manifest(folder: Path, prefix: str = "") -> dict[str, str]:
    reject_links(folder)
    return {
        (Path(prefix) / path.relative_to(folder)).as_posix(): digest(path.read_bytes())
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def payload_manifest(folder: Path, outer: Path) -> dict[str, str]:
    result = file_manifest(folder, MOD_NAME)
    result[outer.name] = digest(outer.read_bytes())
    return dict(sorted(result.items()))


def manifest_bytes(entries: dict[str, str]) -> bytes:
    return "".join(f"{value}  {name}\n" for name, value in sorted(entries.items())).encode("utf-8")


def manifest_summary(entries: dict[str, str]) -> dict[str, object]:
    raw = manifest_bytes(entries)
    return {"files": len(entries), "manifest_sha256": digest(raw)}


def differences(reference: dict[str, str], other: dict[str, str]) -> dict[str, list[str]]:
    reference_names, other_names = set(reference), set(other)
    shared = reference_names & other_names
    return {
        "missing": sorted(reference_names - other_names),
        "extra": sorted(other_names - reference_names),
        "changed": sorted(name for name in shared if reference[name] != other[name]),
    }


def descriptor_value(raw: bytes, key: str) -> str:
    text = raw.decode("utf-8-sig")
    match = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*"([^"]+)"\s*$', text)
    if not match:
        raise RuntimeError(f"descriptor omits {key}")
    return match.group(1)


def descriptor_record(path: Path, include_tree: bool = True) -> dict[str, object]:
    raw = path.read_bytes()
    tree_path = Path(descriptor_value(raw, "path"))
    result: dict[str, object] = {
        "descriptor": str(path.resolve()),
        "descriptor_sha256": digest(raw),
        "name": descriptor_value(raw, "name"),
        "version": descriptor_value(raw, "version"),
        "supported_version": descriptor_value(raw, "supported_version"),
        "tree": str(tree_path.resolve()),
        "tree_exists": tree_path.is_dir(),
    }
    if include_tree:
        if not tree_path.is_dir():
            raise RuntimeError(f"descriptor tree is unavailable: {tree_path}")
        entries = file_manifest(tree_path)
        result.update(manifest_summary(entries))
    return result


def runtime_descriptor(source: bytes, staged_tree: Path) -> bytes:
    matches = list(re.finditer(
        rb'(?m)^[ \t]*path[ \t]*=[ \t]*"(?P<value>[^"]+)"[ \t]*\r?$', source
    ))
    if len(matches) != 1:
        raise RuntimeError(f"expected one AAWC descriptor path, found {len(matches)}")
    match = matches[0]
    value = staged_tree.resolve().as_posix().encode("utf-8")
    return source[:match.start("value")] + value + source[match.end("value"):]


def normalized_descriptor_transport(source: bytes) -> bytes:
    matches = list(re.finditer(
        rb'(?m)^[ \t]*path[ \t]*=[ \t]*"(?P<value>[^"]+)"[ \t]*\r?$', source
    ))
    if len(matches) != 1:
        raise RuntimeError(f"expected one descriptor path, found {len(matches)}")
    match = matches[0]
    return source[:match.start("value")] + b"<ISOLATED_PATH>" + source[match.end("value"):]


def process_count(name: str) -> int:
    if os.name != "nt":
        return 0
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"@(Get-Process -Name '{name}' -ErrorAction SilentlyContinue).Count"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(result.stdout.strip())


def stage(
    destination: Path,
    source_workspace: Path,
    live_mod_root: Path,
    ck3_executable: Path,
    designation: str,
) -> dict[str, object]:
    destination = destination.resolve()
    source_workspace = source_workspace.resolve()
    live_mod_root = live_mod_root.resolve()
    playtest_root = PLAYTEST_ROOT.resolve()
    if not is_relative_to(destination, playtest_root) or destination == playtest_root:
        raise RuntimeError("destination must be a new child of the AAWC playtest directory")
    if destination.exists():
        raise RuntimeError("destination already exists; runtime staging is immutable")
    if not source_workspace.is_dir() or not live_mod_root.is_dir():
        raise RuntimeError("source workspace or live mod root is unavailable")
    if any(is_relative_to(destination, protected) or is_relative_to(protected, destination)
           for protected in (
               source_workspace,
               live_mod_root,
               DEPENDENCIES_SOURCE_ROOT.resolve(),
               RELEASE_ROOT.resolve(),
           )):
        raise RuntimeError("isolated staging must not overlap source, live profile, or archives")

    source_tree = source_workspace / MOD_NAME
    source_outer = source_workspace / f"{MOD_NAME}.mod"
    live_tree = live_mod_root / MOD_NAME
    live_outer = live_mod_root / f"{MOD_NAME}.mod"
    for required in (source_tree, source_outer, live_tree, live_outer):
        if not required.exists():
            raise RuntimeError(f"required candidate/install input is missing: {required}")
    reject_links(source_tree)
    reject_links(live_tree)

    source = payload_manifest(source_tree, source_outer)
    live = payload_manifest(live_tree, live_outer)
    source_version = descriptor_value((source_tree / "descriptor.mod").read_bytes(), "version")
    outer_version = descriptor_value(source_outer.read_bytes(), "version")
    if source_version != "1.11.1.0" or outer_version != source_version:
        raise RuntimeError("unexpected Stage 1 source descriptor version")

    runtime_userdir = destination / "runtime-userdir"
    runtime_mod = runtime_userdir / "mod"
    staged_tree = runtime_mod / MOD_NAME
    destination.mkdir(parents=True)
    runtime_mod.mkdir(parents=True)
    shutil.copytree(source_tree, staged_tree, copy_function=shutil.copy2)

    # AGOT and Dependencies remain read-only in their current trees. Their
    # descriptors are copied as controls; only the AAWC payload is staged.
    agot_descriptor = live_mod_root / "ugc_2962333032.mod"
    dependency_descriptor = live_mod_root / "AAWC_Dependencies_Modpack.mod"
    for descriptor in (agot_descriptor, dependency_descriptor):
        if not descriptor.is_file():
            raise RuntimeError(f"dependency descriptor is missing: {descriptor}")
        shutil.copy2(descriptor, runtime_mod / descriptor.name)

    source_outer_bytes = source_outer.read_bytes()
    (destination / "source-outer-descriptor.mod").write_bytes(source_outer_bytes)
    staged_outer = runtime_mod / f"{MOD_NAME}.mod"
    staged_outer.write_bytes(runtime_descriptor(source_outer_bytes, staged_tree))
    (runtime_userdir / "dlc_load.json").write_text(
        json.dumps({"enabled_mods": list(LOAD_ORDER), "disabled_dlcs": []}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    staged_inner = file_manifest(staged_tree, MOD_NAME)
    source_inner = file_manifest(source_tree, MOD_NAME)
    inner_delta = differences(source_inner, staged_inner)
    if any(inner_delta.values()):
        raise RuntimeError(f"staged AAWC payload differs from source: {inner_delta}")

    source_manifest_path = destination / "candidate-source.sha256"
    staged_manifest_path = destination / "isolated-staged-payload.sha256"
    live_manifest_path = destination / "preexisting-live-install.sha256"
    source_manifest_path.write_bytes(manifest_bytes(source))
    # The staged payload manifest intentionally pins the unmodified source outer
    # descriptor alongside the byte-identical inner tree. The runtime transport
    # descriptor is separately hashed and its one-field delta is recorded.
    staged_payload = dict(staged_inner)
    staged_payload[source_outer.name] = digest((destination / "source-outer-descriptor.mod").read_bytes())
    staged_manifest_path.write_bytes(manifest_bytes(staged_payload))
    live_manifest_path.write_bytes(manifest_bytes(live))

    launcher_settings = ck3_executable.parent.parent / "launcher" / "launcher-settings.json"
    launcher = json.loads(launcher_settings.read_text(encoding="utf-8-sig")) if launcher_settings.is_file() else {}
    ck3_running = process_count("ck3")
    static_prerequisites = bool(
        ck3_executable.is_file() and launcher.get("rawVersion") == "1.19.0.6" and ck3_running == 0
    )
    native = {
        "executable": str(ck3_executable.resolve()),
        "executable_present": ck3_executable.is_file(),
        "executable_sha256": digest(ck3_executable.read_bytes()) if ck3_executable.is_file() else None,
        "launcher_settings": str(launcher_settings.resolve()),
        "launcher_raw_version": launcher.get("rawVersion"),
        "launcher_display_version": launcher.get("version"),
        "ck3_processes_running_at_stage_time": ck3_running,
        "static_executable_prerequisites_available": static_prerequisites,
        # Staging can prove executable identity and construct an isolated
        # user-data directory.  It cannot prove that an authorized launch
        # route will bind CK3 to that directory.  That is a separate native
        # execution prerequisite and must be evidenced independently.
        "controlled_launch_prerequisites_available": False,
        "isolated_binding_launch_route_verified": False,
        "native_execution_available": False,
        "execution_attempted": False,
        "execution_result": (
            "NOT RUN — executable identity recorded; an authorized launch route "
            "binding CK3 to the isolated user-data directory is not verified"
        ),
    }

    dependencies = {
        "ck3": native,
        "agot": descriptor_record(agot_descriptor),
        "aawc_dependencies": descriptor_record(dependency_descriptor),
        "aawc": {
            "development_designation": designation,
            "descriptor_version": source_version,
            "supported_version": descriptor_value(source_outer_bytes, "supported_version"),
        },
    }
    if dependencies["agot"]["version"] != "0.5.2.1":
        raise RuntimeError("unexpected AGOT dependency version")
    if dependencies["aawc_dependencies"]["version"] != "1.1.1":
        raise RuntimeError("unexpected AAWC Dependencies version")

    live_delta = differences(source, live)
    runtime_outer_bytes = staged_outer.read_bytes()
    normalized_runtime = normalized_descriptor_transport(runtime_outer_bytes)
    # Every transport-descriptor byte except the path value must remain exact,
    # including BOM and CRLF/LF line-ending choices.
    normalized_source = normalized_descriptor_transport(source_outer_bytes)
    if normalized_runtime != normalized_source:
        raise RuntimeError("runtime descriptor differs from source beyond its isolated path")

    receipt: dict[str, object] = {
        "schema": "aawc-reforging-stage1-runtime-staging-v1",
        "status": "PASS",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "source_workspace": str(source_workspace),
        "isolated_destination": str(destination),
        "protected_locations_modified": [],
        "candidate": {
            "development_designation": designation,
            **manifest_summary(source),
            "source_manifest": str(source_manifest_path),
            "source_manifest_file_sha256": digest(source_manifest_path.read_bytes()),
        },
        "preexisting_live_install": {
            **manifest_summary(live),
            "manifest": str(live_manifest_path),
            "comparison_to_candidate": live_delta,
            "difference_count": sum(len(value) for value in live_delta.values()),
            "classification": "STALE — read-only comparison only",
        },
        "isolated_stage": {
            **manifest_summary(staged_payload),
            "manifest": str(staged_manifest_path),
            "payload_parity": not any(inner_delta.values()) and staged_payload == source,
            "payload_comparison": differences(source, staged_payload),
            "runtime_descriptor": str(staged_outer),
            "runtime_descriptor_sha256": digest(runtime_outer_bytes),
            "descriptor_adaptation": "path field only; candidate payload bytes unchanged",
            "load_order": list(LOAD_ORDER),
        },
        "dependency_stack": dependencies,
        "native_ck3_execution": native,
    }
    receipt_path = destination / "staging-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    return receipt


def verify_receipt(receipt_path: Path) -> dict[str, object]:
    receipt_path = receipt_path.resolve()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "aawc-reforging-stage1-runtime-staging-v1" or receipt.get("status") != "PASS":
        raise RuntimeError("unsupported or incomplete staging receipt")
    destination = Path(receipt["isolated_destination"]).resolve()
    if receipt_path != destination / "staging-receipt.json" or not is_relative_to(destination, PLAYTEST_ROOT.resolve()):
        raise RuntimeError("receipt is outside its isolated AAWC playtest destination")
    source_workspace = Path(receipt["source_workspace"])
    source_tree = source_workspace / MOD_NAME
    source_outer = source_workspace / f"{MOD_NAME}.mod"
    source = payload_manifest(source_tree, source_outer)
    staged_tree = destination / "runtime-userdir" / "mod" / MOD_NAME
    staged_outer_source = destination / "source-outer-descriptor.mod"
    staged = file_manifest(staged_tree, MOD_NAME)
    staged[source_outer.name] = digest(staged_outer_source.read_bytes())
    expected_digest = receipt["candidate"]["manifest_sha256"]
    if manifest_summary(source)["manifest_sha256"] != expected_digest or staged != source:
        raise RuntimeError("source or isolated staged payload drifted after receipt creation")
    runtime_outer = destination / "runtime-userdir" / "mod" / f"{MOD_NAME}.mod"
    if normalized_descriptor_transport(runtime_outer.read_bytes()) != normalized_descriptor_transport(source_outer.read_bytes()):
        raise RuntimeError("runtime descriptor drifted beyond its isolated path")
    load = json.loads((destination / "runtime-userdir" / "dlc_load.json").read_text(encoding="utf-8"))
    if load != {"enabled_mods": list(LOAD_ORDER), "disabled_dlcs": []}:
        raise RuntimeError("isolated load order drifted")
    result = {
        "status": "PASS",
        "receipt": str(receipt_path),
        "candidate_files": len(source),
        "candidate_manifest_sha256": expected_digest,
        "payload_parity": True,
        "protected_locations_modified": receipt["protected_locations_modified"],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--destination", type=Path)
    selection.add_argument("--verify-receipt", type=Path)
    parser.add_argument(
        "--source-root", "--workspace", dest="source_root", type=Path, default=WORKSPACE,
        help="Directory containing the current mod folder and outer descriptor.",
    )
    parser.add_argument("--live-mod-root", type=Path, default=LIVE_MOD_ROOT)
    parser.add_argument("--ck3-executable", type=Path, default=DEFAULT_CK3,
                        help="CK3 executable (or set AAWC_CK3_EXECUTABLE)")
    parser.add_argument("--designation", default="1.11.2.7-stage2-dev.0")
    args = parser.parse_args()
    if args.verify_receipt:
        print(json.dumps(verify_receipt(args.verify_receipt), indent=2))
        return 0
    if args.ck3_executable is None:
        parser.error("--ck3-executable or AAWC_CK3_EXECUTABLE is required when staging")
    receipt = stage(args.destination, args.source_root, args.live_mod_root, args.ck3_executable, args.designation)
    print(json.dumps({
        "status": receipt["status"],
        "candidate": receipt["candidate"],
        "live_difference_count": receipt["preexisting_live_install"]["difference_count"],
        "isolated_stage": receipt["isolated_stage"],
        "native_ck3_execution": receipt["native_ck3_execution"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
