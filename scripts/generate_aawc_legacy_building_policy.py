"""Generate AAWC's compatibility-safe legacy-building suppression policy.

The ordinary catalogue is suppressed by removing legacy roots from holding
allow-lists.  Definitions remain loaded, so old saves and scripted references
continue to resolve.  Special and duchy-slot definitions have no equivalent
allow-list; their complete effective definitions are therefore copied into one
late override with only construction visibility/eligibility and AI choice
disabled.

Discovery is pinned to the installed CK3/AGOT versions used by this release.
The generated policy and runtime override are committed, so normal packaging
does not depend on a consumer having those source trees installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from generate_aawc_stage3_catalogue import ROOT, load_source, require, json_bytes
from generate_aawc_stage3_buildings import (
    CONSTRUCTION,
    HOLDING_MARKER_END,
    HOLDING_MARKER_START,
    matching_brace,
)
from validate_aawc_reforging_stage1_cohort_engine import (
    definition_body,
    top_level_definitions,
)

MOD = ROOT / "mod/AGOT_Alternate_World_Compatch"
CATALOGUE = ROOT / "catalogue/stage3/catalogue.json"
POLICY = ROOT / "catalogue/stage3/legacy_building_policy.json"
ORDINARY_INVENTORY = ROOT / "catalogue/stage3/legacy_ordinary_inventory.json"
DOC = ROOT / "catalogue/stage3/LEGACY_BUILDING_POLICY.md"
SPECIAL_OVERRIDE = MOD / "common/buildings/zzzzz_aawc_legacy_special_suppression.txt"
HOLDING_FILES = (
    MOD / "common/holdings/00_holdings.txt",
    MOD / "common/holdings/zz_aawc_regional_blocker_holdings.txt",
)
OUTPUT_NAME = SPECIAL_OVERRIDE.name

BASE_DEFAULT = Path(r"C:/Program Files (x86)/Steam/steamapps/common/Crusader Kings III/game")
AGOT_DEFAULT = Path(r"C:/Program Files (x86)/Steam/steamapps/workshop/content/1158310/2962333032")
DEPENDENCIES = ROOT / "dependencies/AAWC_Dependencies_Modpack"

MAIN_HOLDINGS = {
    "castle_holding",
    "church_holding",
    "city_holding",
    "herder_holding",
    "monastery_holding",
    "nomad_holding",
    "pirate_den_holding",
    "ruin_holding",
    "settlement_holding",
    "temple_citadel_holding",
    "tribal_holding",
    "unknown_holding",
    "wilderness_holding",
}
FULL_ROOT_RETENTION = {"ruin_holding", "wilderness_holding"}

# These are lifecycle obstacles, their cleared states, and Valyria ruin/mining
# state.  They remain in settlements because Stage 4 and LoV transitions refer
# to the exact IDs; they are not ordinary economic catalogue alternatives.
SETTLEMENT_LIFECYCLE_ROOTS = {
    "wolf_den", "wolf_den_cleared", "bear_den", "bear_den_cleared",
    "flooded_lands", "flooded_lands_cleared", "bandits", "bandits_cleared",
    "dense_growth", "dense_growth_cleared", "pirate_remnants", "pirate_remnants_cleared",
    "valyria_mines_dormant_01", "valyria_mines_01", "unexplored_caves_01",
    "swamp_01_01", "swamp_02_01", "lv_floods_01", "noxious_gases_01_01",
    "noxious_gases_02_01", "stonemen_encampment_01", "bandit_camps_01",
    "small_ruined_holding_01", "medium_ruined_holding_01", "large_ruined_holding_01",
    "ravenous_basilisk_1", "ravenous_basilisk_tame", "ghoulish_bat_1",
    "ghoulish_bat_tame", "basilisk_1", "cos_bat_1", "cos_wyvern_1",
    "cos_wyvern_alpha_1", "cos_carn_plant_1",
}

# Settlement-only LoV catalogue entries do not have direct historical lineage
# rows in Stage 3.  Route them to the closest approved AAWC infrastructure.
ANALOGOUS_ROOT_ROUTES = {
    "stockades_01": "aawc_palisades_01",
    "tribal_stockades_01": "aawc_palisades_01",
    "local_militia_01": "aawc_mustering_fields_01",
    "tribal_local_militia_01": "aawc_mustering_fields_01",
    "trading_outposts_01": "aawc_market_villages_01",
    "tribal_trading_outposts_01": "aawc_market_villages_01",
    "construction_guilds_01": "aawc_workshops_01",
    "tribal_construction_guilds_01": "aawc_workshops_01",
    "hyperborean_trade_post_01": "aawc_common_tradeport_01",
    "colony_port_01": "aawc_common_tradeport_01",
    "colony_quarries_01": "aawc_quarries_01",
    "colony_forestry_01": "aawc_logging_camps_01",
    "lokirian_barracks_01": "aawc_barracks_01",
}

ROOT_EXCEPTIONS = {
    "generic_dragon_pit_01": (
        "dragon_system_owned",
        "Generic dragon pits are owned by AGOT's dragon lifecycle; AAWC has no safe "
        "repeatable structural substitute, so the legacy ordinary-menu route is hidden.",
    ),
    "valyria_mines_dormant_01": (
        "ruin_lifecycle_owned",
        "The dormant mine is retained only in ruin/settlement lifecycle holdings and is not "
        "a general-purpose economic construction route.",
    ),
    "valyria_mines_01": (
        "ruin_lifecycle_owned",
        "The active Valyria mine remains an exact-ID ruin/settlement lifecycle endpoint and "
        "is removed from ordinary settled-holding catalogues.",
    ),
}

GATE_PATTERNS = {
    "culture_or_innovation": r"\bculture\b|innovation|cultural_parameter|cultural_tradition",
    "faith_or_doctrine": r"\bfaith\b|doctrine|holy_site",
    "character_skill_or_lifestyle": r"\b(diplomacy|martial|stewardship|intrigue|learning|prowess)\b\s*(?:=|>=|<=|>|<)|has_lifestyle_perk|has_trait\s*=\s*lifestyle_",
    "dynasty_legacy": r"has_dynasty_perk|\bdynasty\s*=",
    "government": r"government",
    "geography_or_resource": r"terrain|geographical_region|province_modifier|is_coastal|is_riverside",
    "building_prerequisite": r"has_building|building_requirement",
    "development": r"development_level",
    "holding_type": r"has_holding_type",
    "title_or_realm": r"has_title|highest_held_title|is_independent|county\.holder|capital_province",
    "dlc": r"has_dlc|dlc_feature",
}
MANAGED_FIELDS = ("show_disabled", "can_construct_potential", "can_construct", "ai_value")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def all_definitions(text: str) -> dict[str, str]:
    """Extract top-level definitions in one pass.

    The shared validator helper is ideal for small targeted reads but repeatedly
    rescans a file for each ID.  The population overlay is several megabytes, so
    discovery uses this equivalent linear extractor.
    """
    result = {}
    position = 0
    pattern = re.compile(r"(?m)^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{")
    while True:
        match = pattern.search(text, position)
        if not match:
            return result
        opening = text.find("{", match.start())
        closing = matching_brace(text, opening)
        result[match.group(1)] = text[opening + 1 : closing]
        position = closing + 1


def extract_value_span(text: str, key: str) -> tuple[int, int] | None:
    match = re.search(r"(?m)^[ \t]*" + re.escape(key) + r"\s*=\s*", text)
    if not match:
        return None
    value = match.end()
    if value < len(text) and text[value] == "{":
        end = matching_brace(text, value) + 1
        while end < len(text) and text[end] in " \t":
            end += 1
        if end < len(text) and text[end] == "\r":
            end += 1
        if end < len(text) and text[end] == "\n":
            end += 1
        return match.start(), end
    end = text.find("\n", value)
    return match.start(), len(text) if end < 0 else end + 1


def replace_field(text: str, key: str, replacement: str) -> str:
    span = extract_value_span(text, key)
    line = f"\t{key} = {replacement}\n"
    if span:
        return text[: span[0]] + line + text[span[1] :]
    return text.rstrip() + "\n" + line


def remove_fields(text: str, fields: tuple[str, ...] = MANAGED_FIELDS) -> str:
    result = text
    for key in fields:
        span = extract_value_span(result, key)
        if span:
            result = result[: span[0]] + result[span[1] :]
    return re.sub(r"\s+", " ", result).strip()


def gate_text(body: str) -> str:
    chunks = []
    for key in ("can_construct_potential", "can_construct", "can_construct_showing_failures_only", "is_enabled"):
        span = extract_value_span(body, key)
        if span:
            chunks.append(body[span[0] : span[1]])
    return "\n".join(chunks)


def gate_categories(text: str) -> list[str]:
    return sorted(name for name, pattern in GATE_PATTERNS.items() if re.search(pattern, text, re.I))


def holding_blocks(text: str) -> dict[str, tuple[list[str], int, int, str]]:
    result = {}
    for holding in sorted(top_level_definitions(text)):
        match = re.search(r"(?m)^" + re.escape(holding) + r"\s*=\s*\{", text)
        if not match:
            continue
        opening = text.find("{", match.start())
        closing = matching_brace(text, opening)
        body = text[opening + 1 : closing]
        buildings = re.search(r"(?m)^\s*buildings\s*=\s*\{", body)
        if not buildings:
            continue
        block_open = opening + 1 + body.find("{", buildings.start())
        block_close = matching_brace(text, block_open)
        raw = text[block_open + 1 : block_close]
        roots = re.findall(r"(?m)^\s*([A-Za-z0-9_]+)\s*(?:#.*)?$", raw)
        indent_match = re.search(r"(?m)^([ \t]*)[A-Za-z0-9_]+", raw)
        indent = indent_match.group(1) if indent_match else "\t\t"
        result[holding] = (roots, block_open + 1, block_close, indent)
    return result


def lineage_maps(catalogue: dict) -> tuple[dict[str, str], dict[str, str]]:
    tier = {}
    roots = {}
    for chain in catalogue["chains"]:
        for level in chain["levels"]:
            if level["legacy_id"]:
                tier[level["legacy_id"]] = level["id"]
        first = chain["levels"][0]
        if first["legacy_id"]:
            roots[first["legacy_id"]] = first["id"]
    return tier, roots


def load_ordinary_inventory() -> dict[str, list[str]]:
    inventory = load_source(ORDINARY_INVENTORY)
    require(
        set(inventory) == {"schema_version", "policy", "roots_by_holding"}
        and inventory["schema_version"] == 1
        and inventory["policy"] == "pre_suppression_ordinary_roots_v1",
        "ordinary inventory schema/policy mismatch",
    )
    return inventory["roots_by_holding"]


def bootstrap_ordinary_inventory() -> None:
    """Capture the verified pre-suppression holding roots from the release base."""
    require(not ORDINARY_INVENTORY.exists(), "ordinary inventory already exists")
    roots_by_holding = {}
    for path in HOLDING_FILES:
        relative = path.relative_to(ROOT).as_posix()
        result = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        )
        text = result.stdout.decode("utf-8-sig")
        for holding, (roots, _, _, _) in holding_blocks(text).items():
            if holding in FULL_ROOT_RETENTION:
                continue
            roots_by_holding[holding] = [
                root
                for root in roots
                if not root.startswith("aawc_")
                and not (holding == "settlement_holding" and root in SETTLEMENT_LIFECYCLE_ROOTS)
            ]
    ORDINARY_INVENTORY.write_bytes(
        json_bytes(
            {
                "schema_version": 1,
                "policy": "pre_suppression_ordinary_roots_v1",
                "roots_by_holding": roots_by_holding,
            }
        )
    )


def rewrite_holdings(catalogue: dict) -> tuple[dict[Path, str], list[dict], list[dict], dict[str, list[str]]]:
    _, root_map = lineage_maps(catalogue)
    stage3_roots = {
        chain["levels"][0]["id"] for chain in catalogue["chains"] if chain["kind"] == "regular"
    }
    artifacts = {}
    mapped = {}
    exceptions = {}
    retained = {}
    for holding, roots in load_ordinary_inventory().items():
        for root in roots:
            replacement = root_map.get(root) or ANALOGOUS_ROOT_ROUTES.get(root)
            if replacement:
                row = mapped.setdefault(
                    root,
                    {
                        "legacy_root": root,
                        "replacement_root": replacement,
                        "route": "catalogue_lineage" if root in root_map else "analogous_settlement_route",
                        "holding_types": [],
                    },
                )
                row["holding_types"].append(holding)
            else:
                require(root in ROOT_EXCEPTIONS, f"{holding}: missing disposition for {root}")
                category, rationale = ROOT_EXCEPTIONS[root]
                row = exceptions.setdefault(
                    root,
                    {
                        "legacy_root": root,
                        "category": category,
                        "rationale": rationale,
                        "holding_types": [],
                    },
                )
                row["holding_types"].append(holding)
    for path in HOLDING_FILES:
        text = path.read_text(encoding="utf-8-sig")
        edits = []
        for holding, (roots, start, end, indent) in holding_blocks(text).items():
            kept = []
            retained[holding] = []
            for root in roots:
                if root.startswith("aawc_") or holding in FULL_ROOT_RETENTION or (
                    holding == "settlement_holding" and root in SETTLEMENT_LIFECYCLE_ROOTS
                ):
                    kept.append(root)
                    retained[holding].append(root)
                    continue
                require(root in mapped or root in exceptions, f"{holding}: root absent from pinned inventory: {root}")
            marker_roots = [x for x in kept if x.startswith("aawc_")]
            require(marker_roots, f"{holding}: no AAWC replacement roots retained") if holding not in FULL_ROOT_RETENTION and holding not in {"monastery_holding"} else None
            lines = []
            inside_stage3 = False
            for root in kept:
                if root in stage3_roots and not inside_stage3:
                    lines.append(f"\t\t{HOLDING_MARKER_START}\n")
                    inside_stage3 = True
                if root not in stage3_roots and inside_stage3:
                    lines.append(f"\t\t{HOLDING_MARKER_END}\n")
                    inside_stage3 = False
                lines.append(f"\t\t{root}\n")
            if inside_stage3:
                lines.append(f"\t\t{HOLDING_MARKER_END}\n")
            rendered = "\n" + "".join(lines) + "\t"
            edits.append((start, end, rendered))
        for start, end, rendered in sorted(edits, key=lambda item: item[0], reverse=True):
            text = text[:start] + rendered + text[end:]
        artifacts[path] = text
    return artifacts, sorted(mapped.values(), key=lambda x: x["legacy_root"]), sorted(exceptions.values(), key=lambda x: x["legacy_root"]), retained


def effective_stack(base: Path, agot: Path) -> tuple[dict[str, str], dict[str, dict], dict[str, str], dict[str, str]]:
    roots = (("CK3", base), ("AGOT", agot), ("Dependencies", DEPENDENCIES), ("AAWC", MOD))
    files = {}
    labels = {}
    for label, root in roots:
        directory = root / "common/buildings"
        require(directory.is_dir(), f"missing building source: {directory}")
        for path in sorted(directory.glob("*.txt")):
            if path.name != OUTPUT_NAME:
                files[path.name] = path
                labels[path.name] = label
    definitions = {}
    sources = {}
    variables = {}
    definition_variables = {}
    file_hashes = {}
    for name, path in sorted(files.items()):
        text = path.read_text(encoding="utf-8-sig")
        label = labels[name]
        file_hashes[f"{label}/{name}"] = sha256(path.read_bytes())
        local_vars = {
            key: value.strip()
            for key, value in re.findall(r"(?m)^@([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^#\r\n]+)", text)
        }
        variables.update(local_vars)
        for bid, body in all_definitions(text).items():
            definitions[bid] = body
            definition_variables[bid] = {**variables, **local_vars}
            sources[bid] = {"label": label, "file": name, "sha256": file_hashes[f"{label}/{name}"]}

    def resolve(body: str, context: dict[str, str]) -> str:
        for _ in range(12):
            refs = set(re.findall(r"@([A-Za-z_][A-Za-z0-9_]*)", body))
            if not refs:
                return body
            missing = sorted(refs - context.keys())
            require(not missing, f"unresolved script variables: {missing}")
            changed = body
            for ref in sorted(refs, key=len, reverse=True):
                changed = re.sub(r"@" + re.escape(ref) + r"\b", context[ref], changed)
            require(changed != body, "script variable expansion made no progress")
            body = changed
        require(False, "script variable expansion exceeded recursion bound")
        return body

    definitions = {bid: resolve(body, definition_variables[bid]) for bid, body in definitions.items()}
    return definitions, sources, file_hashes, labels


def chain_closure(roots: set[str], definitions: dict[str, str]) -> set[str]:
    retained = set()
    pending = list(roots)
    while pending:
        bid = pending.pop()
        if bid in retained or bid not in definitions:
            continue
        retained.add(bid)
        match = re.search(r"(?m)^\s*next_building\s*=\s*([A-Za-z0-9_]+)", definitions[bid])
        if match:
            pending.append(match.group(1))
    return retained


def primary_and_lifecycle_roots(holding_artifacts: dict[Path, str]) -> set[str]:
    roots = set()
    for text in holding_artifacts.values():
        definitions = all_definitions(text)
        for holding in MAIN_HOLDINGS & definitions.keys():
            body = definitions[holding]
            primary = re.search(r"(?m)^\s*primary_building\s*=\s*([A-Za-z0-9_]+)", body)
            if primary:
                roots.add(primary.group(1))
        for holding in FULL_ROOT_RETENTION:
            if holding in definitions:
                block = holding_blocks(text)[holding][0]
                roots.update(block)
    return roots


def special_policy(
    definitions: dict[str, str],
    sources: dict[str, dict],
    holding_artifacts: dict[Path, str],
    catalogue: dict,
    construction: dict,
) -> tuple[str, list[dict], list[dict], set[str]]:
    tier_map, _ = lineage_maps(catalogue)
    retained_roots = primary_and_lifecycle_roots(holding_artifacts)
    retained_roots |= {bid for bid in definitions if bid.startswith("aawc_")}
    retained = chain_closure(retained_roots, definitions)

    special = {
        bid
        for bid, body in definitions.items()
        if re.search(r"(?m)^\s*type\s*=\s*(special|duchy_capital)\s*$", body)
    }
    suppressed = sorted(special - retained)
    mapped = []
    exceptions = []
    script = [
        "# Generated by scripts/generate_aawc_legacy_building_policy.py.",
        "# Full effective definitions are retained for save/script compatibility.",
        "# Only construction visibility, eligibility, and AI selection are suppressed.",
        "",
    ]
    for bid in suppressed:
        original = definitions[bid]
        categories = gate_categories(gate_text(original))
        patched = replace_field(original, "show_disabled", "no")
        patched = replace_field(patched, "can_construct_potential", "{ always = no }")
        patched = replace_field(patched, "can_construct", "{ always = no }")
        patched = replace_field(patched, "ai_value", "{ base = 0 }")
        payload_hash = sha256(remove_fields(patched).encode("utf-8"))
        script.extend((f"# Effective source: {sources[bid]['label']}/{sources[bid]['file']}", f"{bid} = {{", patched.rstrip(), "}", ""))
        common = {
            "legacy_id": bid,
            "gate_categories": categories,
            "source": sources[bid],
            "preserved_payload_sha256": payload_hash,
        }
        if bid in tier_map:
            mapped.append({**common, "replacement_id": tier_map[bid], "route": "catalogue_lineage"})
        else:
            exceptions.append(
                {
                    **common,
                    "category": "world_landmark_or_dependency_special",
                    "rationale": "No generic replacement: this is a county/site-specific landmark or dependency-owned special chain. Existing instances and scripted references remain intact, while new legacy construction is hidden.",
                }
            )
    return "\n".join(script), mapped, exceptions, retained & special


def add_route_metadata(rows: list[dict], construction: dict) -> None:
    by_level = {
        bid: level
        for chain in construction["chains"].values()
        for bid, level in chain["levels"].items()
    }
    for row in rows:
        replacement = row.get("replacement_root") or row.get("replacement_id")
        require(replacement in by_level, f"missing replacement definition in construction contract: {replacement}")
        gates = "\n".join(by_level[replacement]["gates"].values())
        row["replacement_gate_categories"] = gate_categories(gates)
        row["replacement_gate_sha256"] = sha256(re.sub(r"\s+", " ", gates).strip().encode("utf-8"))


def catalogue_tier_routes(catalogue: dict, construction: dict) -> list[dict]:
    routes = []
    protected_main_lineages = {"aawc_tribe", "aawc_temple_citadel"}
    for chain in catalogue["chains"]:
        contract = construction["chains"][chain["id"]]
        for level in chain["levels"]:
            if not level["legacy_id"]:
                continue
            rule = contract["levels"][level["id"]]
            gates = "\n".join(rule["gates"].values())
            routes.append(
                {
                    "legacy_id": level["legacy_id"],
                    "replacement_id": level["id"],
                    "replacement_chain": chain["id"],
                    "disposition": (
                        "retained_main_line_with_aawc_annex"
                        if chain["id"] in protected_main_lineages
                        else "legacy_replaced_by_aawc"
                    ),
                    "gate_categories": gate_categories(gates),
                    "gate_contract_sha256": sha256(re.sub(r"\s+", " ", gates).strip().encode("utf-8")),
                    "provenance": rule["provenance"],
                }
            )
    return sorted(routes, key=lambda row: row["legacy_id"])


def render_doc(policy: dict) -> str:
    ordinary = policy["ordinary_routes"]
    special = policy["special_routes"]
    skill_count = policy["gate_audit"]["direct_character_skill_gate_count"]
    skill_summary = (
        "No direct character-skill/lifestyle construction gate was identified in the effective legacy catalogue; none is invented."
        if skill_count == 0
        else f"Direct character-skill/lifestyle gates identified: {skill_count}; each is dispositioned by exact ID in the JSON authority."
    )
    lines = [
        "# Legacy Building Suppression and Unlock Routes",
        "",
        "This is the dedicated authority for AAWC's post-review legacy-building policy. "
        "Compatibility is preserved: legacy definitions remain loaded, existing instances keep "
        "their modifiers, and exact-ID scripted references keep resolving. Ordinary legacy roots "
        "are removed from holding construction allow-lists; unretained special/duchy definitions "
        "are fully mirrored in a late override with only visibility, construction eligibility, and "
        "AI selection disabled.",
        "",
        "AAWC definitions, primary holding chains, ruin/wilderness lifecycle chains, settlement "
        "blockers, and restored-special endpoints reached through AAWC wrapper chains are retained. "
        "The policy does not delete dependency definitions and does not migrate existing saves.",
        "",
        "## Unlock-route summary",
        "",
        f"- Ordinary legacy roots mapped to AAWC replacements: {len(ordinary['mapped'])}",
        f"- Ordinary holding-specific no-replacement exceptions: {len(ordinary['no_replacement'])}",
        f"- Special/duchy legacy tiers mapped by catalogue lineage: {len(special['mapped'])}",
        f"- Site-specific special/duchy no-replacement exceptions: {len(special['no_replacement'])}",
        f"- Retained special/duchy tiers: {special['retained_count']}",
        f"- Complete historical tier unlock contracts: {len(policy['unlock_routes']['catalogue_tiers'])} "
        f"({policy['unlock_routes']['replacement_count']} replaced; {policy['unlock_routes']['retained_main_line_count']} retained main-line tiers with AAWC annexes)",
        f"- {skill_summary}",
        "",
        "Culture/innovation, faith/doctrine, government, geography/resource, prerequisite-building, "
        "development, holding-type, title/realm, and DLC predicates are classified per route in the "
        "machine-readable JSON authority. Catalogue-lineage replacements preserve their recovered "
        "legacy predicates tier by tier; analogous settlement routes use the approved replacement's "
        "own reachable AAWC gate contract.",
        "",
        "## Ordinary catalogue routes",
        "",
        "| Legacy root | AAWC replacement | Route | Holdings | Replacement gate classes |",
        "|---|---|---|---|---|",
    ]
    for row in ordinary["mapped"]:
        lines.append(
            f"| `{row['legacy_root']}` | `{row['replacement_root']}` | `{row['route']}` | "
            f"{', '.join(row['holding_types'])} | {', '.join(row['replacement_gate_categories']) or 'none'} |"
        )
    lines += ["", "## Ordinary no-replacement exceptions", "", "| Legacy root | Scope | Reason |", "|---|---|---|"]
    for row in ordinary["no_replacement"]:
        lines.append(f"| `{row['legacy_root']}` | {', '.join(row['holding_types'])} | {row['rationale']} |")
    lines += [
        "",
        "## Special and duchy disposition",
        "",
        "Every suppressed special/duchy tier is listed in `legacy_building_policy.json` with its "
        "source hash, gate classes, preserved-payload hash, and either an exact AAWC tier mapping or "
        "a per-ID no-replacement record. The no-replacement class is intentionally narrow: unique "
        "world landmarks and dependency-owned special sites do not become repeatable generic AAWC "
        "infrastructure. Existing instances remain active for save and event compatibility.",
        "",
        "## Retained exceptions",
        "",
        "- All `aawc_*` definitions, including the 131 Stage 3 chains and restoration wrappers.",
        "- Primary holding chains for castle, city, church, tribe, temple citadel, monastery, pirate den, settlement, wilderness, nomad, herder, unknown, and ruin holdings.",
        "- All roots registered in ruin and wilderness holdings, plus exact settlement blocker/cleared-state and Valyria mine lifecycle roots.",
        "- Non-AAWC special endpoints reached recursively from AAWC restoration wrappers.",
        "",
        "## Verification boundary",
        "",
        "Focused tests enumerate holding-list suppression, mapping/no-replacement coverage, special "
        "override payload preservation, retained main/ruin availability, and target reachability. "
        "This is source/package validation; rendered CK3 menu inspection belongs to the integrated review candidate.",
        "",
    ]
    return "\n".join(lines)


def build(base: Path, agot: Path) -> dict[Path, bytes]:
    catalogue = load_source(CATALOGUE)
    construction = load_source(CONSTRUCTION)
    holding_artifacts, ordinary_mapped, ordinary_exceptions, retained_roots = rewrite_holdings(catalogue)
    definitions, sources, file_hashes, _ = effective_stack(base, agot)
    special_text, special_mapped, special_exceptions, retained_special = special_policy(
        definitions, sources, holding_artifacts, catalogue, construction
    )
    add_route_metadata(ordinary_mapped, construction)
    add_route_metadata(special_mapped, construction)
    tier_routes = catalogue_tier_routes(catalogue, construction)

    direct_skill_ids = sorted(
        {
            row["legacy_id"]
            for row in tier_routes + special_exceptions
            if "character_skill_or_lifestyle" in row["gate_categories"]
        }
    )
    policy = {
        "schema_version": 1,
        "policy": "compatibility_safe_legacy_suppression_v1",
        "source_stack": {
            "ck3_version": "1.19.0.6",
            "agot_version": "0.5.2.1",
            "dependencies_version": "1.1.2",
            "file_sha256": file_hashes,
        },
        "ordinary_routes": {
            "mapped": ordinary_mapped,
            "no_replacement": ordinary_exceptions,
            "retained_roots_by_holding": retained_roots,
        },
        "special_routes": {
            "mapped": sorted(special_mapped, key=lambda x: x["legacy_id"]),
            "no_replacement": sorted(special_exceptions, key=lambda x: x["legacy_id"]),
            "retained_count": len(retained_special),
            "retained_ids": sorted(retained_special),
        },
        "unlock_routes": {
            "catalogue_tiers": tier_routes,
            "replacement_count": sum(row["disposition"] == "legacy_replaced_by_aawc" for row in tier_routes),
            "retained_main_line_count": sum(row["disposition"] == "retained_main_line_with_aawc_annex" for row in tier_routes),
        },
        "gate_audit": {
            "categories": sorted(GATE_PATTERNS),
            "direct_character_skill_gate_count": len(direct_skill_ids),
            "direct_character_skill_legacy_ids": direct_skill_ids,
            "direct_character_skill_disposition": (
                "No direct skill/lifestyle construction gate was identified in the effective catalogue; do not invent one."
                if not direct_skill_ids
                else "Every identified skill/lifestyle-gated legacy tier is mapped or has an exact-ID no-replacement record; no additional gate is invented."
            ),
        },
    }
    artifacts = {path: text.encode("utf-8-sig") for path, text in holding_artifacts.items()}
    artifacts[SPECIAL_OVERRIDE] = special_text.encode("utf-8-sig")
    artifacts[POLICY] = json_bytes(policy)
    artifacts[DOC] = render_doc(policy).encode("utf-8")
    return artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bootstrap-inventory", action="store_true")
    parser.add_argument("--base-root", type=Path, default=Path(os.environ.get("AAWC_CK3_GAME_ROOT", BASE_DEFAULT)))
    parser.add_argument("--agot-root", type=Path, default=Path(os.environ.get("AAWC_AGOT_ROOT", AGOT_DEFAULT)))
    args = parser.parse_args()
    if args.bootstrap_inventory:
        bootstrap_ordinary_inventory()
    artifacts = build(args.base_root, args.agot_root)
    if args.check:
        for path, expected in artifacts.items():
            require(path.is_file(), f"missing generated artifact: {path.relative_to(ROOT)}")
            require(path.read_bytes() == expected, f"generated artifact drift: {path.relative_to(ROOT)}")
        print("Legacy building policy: deterministic parity verified")
        return
    for path, data in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print("Legacy building policy generated")


if __name__ == "__main__":
    main()
