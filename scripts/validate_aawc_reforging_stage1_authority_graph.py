#!/usr/bin/env python3
"""Validate the Milestone-0 inventory and completed Stage-1 writer migration."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "evidence" / "stage1-authority"
MUTATIONS = AUDIT / "aawc_reforging_population_mutations.csv"
GRAPH = AUDIT / "AAWC_Reforging_1.11_Milestone_0_Stage_1_Authority_Graph.md"
MOD_ROOT = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
PRODUCTION_EFFECTS = (
    MOD_ROOT
    / "common"
    / "scripted_effects"
    / "aawc_reforging_cohort_production_effects.txt"
)

EXPECTED_DIRECT_WRITERS = {
    ("common/on_action/aawc_population_holding_construction_on_actions.txt", "aawc_population_on_new_holding_completed"): 1,
    ("common/scripted_effects/aawc_population_ai_effects.txt", "aawc_population_ai_establish_selected_owned_settlement_effect"): 1,
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_apply_holding_monthly_growth_effect"): 2,
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_apply_warfare_population_loss_effect"): 2,
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_cap_tribal_to_feudal_conversion_effect"): 1,
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_consume_reserved_from_holding_surplus_effect"): 2,
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_spend_maa_population_pool_from_holding_effect"): 2,
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_spend_reserved_pool_from_holding_effect"): 2,
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_update_holding_dynamic_effect"): 3,
    ("common/scripted_effects/lv_settlement_effects.txt", "aawc_age_of_silence_found_tribal_holding_effect"): 1,
    ("common/scripted_effects/lv_settlement_effects.txt", "lv_settlement_establish_effect"): 2,
    ("common/scripted_effects/zzzz_aawc_population_migration_effects.txt", "aawc_migration_apply_holding_population_delta_effect"): 2,
    ("common/scripted_guis/lv_ruin_restoration_scripted_gui.txt", "aawc_establish_owned_settlement_from_gui"): 1,
}

EXPECTED_ADAPTER_CALLS = {
    ("common/on_action/aawc_population_holding_construction_on_actions.txt", "aawc_population_on_new_holding_completed"): (
        "aawc_reforging_cohort_initialize_production_ledger_effect",
    ),
    ("common/scripted_effects/aawc_population_ai_effects.txt", "aawc_population_ai_establish_selected_owned_settlement_effect"): (
        "aawc_reforging_cohort_initialize_production_ledger_effect",
    ),
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_apply_holding_monthly_growth_effect"): (
        "aawc_reforging_cohort_apply_production_month_effect",
    ),
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_apply_warfare_population_loss_effect"): (
        "aawc_reforging_cohort_death_population_effect",
    ),
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_cap_tribal_to_feudal_conversion_effect"): (
        "aawc_reforging_cohort_set_population_target_effect",
    ),
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_consume_reserved_from_holding_surplus_effect"): (
        "aawc_reforging_cohort_debit_population_effect",
    ),
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_spend_maa_population_pool_from_holding_effect"): (
        "aawc_reforging_cohort_debit_legacy_maa_population_effect",
    ),
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_spend_reserved_pool_from_holding_effect"): (
        "aawc_reforging_cohort_debit_population_effect",
    ),
    ("common/scripted_effects/aawc_population_effects.txt", "aawc_population_initialize_holding_demographics_effect"): (
        "aawc_reforging_cohort_initialize_production_ledger_effect",
        "aawc_reforging_cohort_ensure_production_ledger_effect",
    ),
    ("common/scripted_effects/lv_settlement_effects.txt", "aawc_age_of_silence_found_tribal_holding_effect"): (
        "aawc_reforging_cohort_initialize_production_ledger_effect",
    ),
    ("common/scripted_effects/lv_settlement_effects.txt", "lv_settlement_establish_effect"): (
        "aawc_reforging_cohort_initialize_production_ledger_effect",
    ),
    ("common/scripted_effects/zzzz_aawc_population_migration_effects.txt", "aawc_migration_apply_holding_population_delta_effect"): (
        "aawc_reforging_cohort_apply_signed_transfer_effect",
    ),
    ("common/scripted_guis/lv_ruin_restoration_scripted_gui.txt", "aawc_establish_owned_settlement_from_gui"): (
        "aawc_reforging_cohort_initialize_production_ledger_effect",
    ),
}

SANCTIONED_MIRROR_WRITER = "aawc_reforging_cohort_sync_legacy_population_effect"


def uncommented(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def definition_body(text: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", uncommented(text))
    if not match:
        raise ValueError(f"missing definition {name}")
    code = uncommented(text)
    start = match.end() - 1
    depth = 0
    in_quote = False
    escaped = False
    for index in range(start, len(code)):
        char = code[index]
        if in_quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_quote = False
            continue
        if char == '"':
            in_quote = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return code[start + 1 : index]
    raise ValueError(f"unclosed definition {name}")


def main() -> int:
    rows = list(csv.DictReader(MUTATIONS.open(encoding="utf-8", newline="")))
    failures: list[str] = []
    if len(rows) != 709:
        failures.append(f"mutation row count is {len(rows)}, expected 709")
    authority_pairs = {(row["file"], row["authority"]) for row in rows}
    if len(authority_pairs) != 72:
        failures.append(f"authority-pair count is {len(authority_pairs)}, expected 72")
    file_scope = [row for row in rows if row["authority"] == "<file-scope>"]
    if file_scope:
        failures.append(f"{len(file_scope)} mutation rows remain assigned to file scope")

    direct = Counter(
        (row["file"], row["authority"])
        for row in rows
        if row["target_variable"] == "aawc_population_current"
    )
    if direct != Counter(EXPECTED_DIRECT_WRITERS):
        missing = Counter(EXPECTED_DIRECT_WRITERS) - direct
        unexpected = direct - Counter(EXPECTED_DIRECT_WRITERS)
        if missing:
            failures.append(f"missing/undercounted direct writers: {dict(missing)}")
        if unexpected:
            failures.append(f"unexpected/overcounted direct writers: {dict(unexpected)}")

    graph = GRAPH.read_text(encoding="utf-8")
    for _, authority in EXPECTED_DIRECT_WRITERS:
        if f"`{authority}`" not in graph:
            failures.append(f"authority graph omits {authority}")

    # The CSV/graph is the frozen Milestone-0 inventory. The live source must
    # now route every one of those authorities through a cohort adapter.
    for (relative, authority), adapters in EXPECTED_ADAPTER_CALLS.items():
        path = MOD_ROOT / relative
        try:
            body = definition_body(path.read_text(encoding="utf-8-sig"), authority)
        except (OSError, ValueError) as error:
            failures.append(str(error))
            continue
        if re.search(r"\bname\s*=\s*aawc_population_current\b", body):
            failures.append(f"direct aggregate mutation remains in {relative}:{authority}")
        for adapter in adapters:
            if f"{adapter} =" not in body:
                failures.append(f"{relative}:{authority} omits {adapter}")

    current_writers: list[tuple[str, int, str]] = []
    for path in MOD_ROOT.rglob("*.txt"):
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for match in re.finditer(r"\bname\s*=\s*aawc_population_current\b", uncommented(text)):
            line = uncommented(text)[: match.start()].count("\n") + 1
            current_writers.append((path.relative_to(MOD_ROOT).as_posix(), line, match.group(0)))
    expected_path = PRODUCTION_EFFECTS.relative_to(MOD_ROOT).as_posix()
    if len(current_writers) != 1 or current_writers[0][0] != expected_path:
        failures.append(f"live source aggregate writers are not the one sanctioned mirror: {current_writers}")
    try:
        mirror = definition_body(PRODUCTION_EFFECTS.read_text(encoding="utf-8-sig"), SANCTIONED_MIRROR_WRITER)
    except (OSError, ValueError) as error:
        failures.append(str(error))
        mirror = ""
    if len(re.findall(r"\bname\s*=\s*aawc_population_current\b", mirror)) != 1:
        failures.append("sanctioned legacy-mirror effect does not contain exactly one aggregate write")

    if failures:
        print("AAWC Stage-1 authority graph validation: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("AAWC Stage-1 authority graph validation: PASS")
    print("- 709 complete population/reservation mutation statements under 72 exact authorities")
    print("- zero unresolved file-scope rows")
    print("- historical inventory retains all 22 direct statements and 13 exact authorities")
    print("- all 13 production authorities route through cohort credit/debit/death/reconciliation adapters")
    print("- zero direct authority writes remain; one sanctioned derived compatibility-mirror writer remains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
