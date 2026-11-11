#!/usr/bin/env python3
"""Validate the guarded Milestone-1 production-candidate activation."""

from __future__ import annotations

from pathlib import Path

from validate_aawc_reforging_stage1_cohort_engine import Ledger
from validate_aawc_reforging_stage1_authority_graph import definition_body, uncommented


ROOT = Path(__file__).resolve().parents[1]
MOD_ROOT = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
STAGE1 = MOD_ROOT / "common" / "scripted_effects" / "aawc_reforging_cohort_stage1_effects.txt"
PRODUCTION = MOD_ROOT / "common" / "scripted_effects" / "aawc_reforging_cohort_production_effects.txt"
POPULATION = MOD_ROOT / "common" / "scripted_effects" / "aawc_population_effects.txt"
EVENTS = MOD_ROOT / "events" / "aawc_population_events.txt"
ON_ACTIONS = MOD_ROOT / "common" / "on_action" / "aawc_population_on_actions.txt"


def normalized(text: str) -> str:
    return " ".join(uncommented(text).split())


def main() -> int:
    failures: list[str] = []
    source = {
        path: path.read_text(encoding="utf-8-sig")
        for path in (STAGE1, PRODUCTION, POPULATION, EVENTS, ON_ACTIONS)
    }

    production_month = normalized(
        definition_body(source[PRODUCTION], "aawc_reforging_cohort_apply_production_month_effect")
    )
    holding_month = normalized(
        definition_body(source[POPULATION], "aawc_population_apply_holding_monthly_growth_effect")
    )
    character_month = normalized(
        definition_body(source[POPULATION], "aawc_population_apply_monthly_growth_character_effect")
    )
    cadence_recovery = normalized(
        definition_body(source[POPULATION], "aawc_population_apply_county_holding_cadence_recovery_effect")
    )
    recurring_event = normalized(definition_body(source[EVENTS], "aawc_population_event.0100"))
    delayed_start = normalized(definition_body(source[EVENTS], "aawc_population_event.0101"))
    title_gain = normalized(
        definition_body(source[ON_ACTIONS], "aawc_population_on_county_holder_gain_cadence")
    )

    for clause in (
        "aawc_reforging_cohort_ensure_production_ledger_effect = yes",
        "change_variable = { name = aawc_reforging_cohort_requested_tick add = 1 }",
        "aawc_reforging_cohort_monthly_authority_effect = { TICK_ID = var:aawc_reforging_cohort_requested_tick }",
        "aawc_reforging_cohort_sync_legacy_population_effect = yes",
        "NOT = { has_variable = aawc_reforging_cohort_monthly_tick_recent }",
        "set_variable = { name = aawc_reforging_cohort_monthly_tick_recent value = 1 days = 27 }",
    ):
        if clause not in production_month:
            failures.append(f"production month omits {clause}")

    if holding_month.count("aawc_reforging_cohort_apply_production_month_effect = yes") != 1:
        failures.append("holding month does not invoke exactly one cohort production month")
    for retired in (
        "name = aawc_population_growth_delta",
        "aawc_population_holding_live_final_growth_rate_display",
        "applied minimum positive monthly population growth",
    ):
        if retired in holding_month:
            failures.append(f"legacy aggregate growth remains active: {retired}")

    if character_month.count("aawc_population_apply_county_holder_barony_monthly_growth_effect = yes") != 1:
        failures.append("character authority does not traverse its established holding route exactly once")
    if cadence_recovery.count("aawc_reforging_cohort_apply_production_month_effect = yes") != 1:
        failures.append("county-gain recovery does not invoke the guarded cohort month exactly once")
    for forbidden in ("aawc_population_apply_monthly_maa_reinforcement_character_effect", "aawc_migration_update_world_effect"):
        if forbidden in cadence_recovery:
            failures.append(f"county-gain recovery repeats unrelated work: {forbidden}")
    for clause in (
        "NOT = { has_character_flag = aawc_population_monthly_tick_recent }",
        "add_character_flag = { flag = aawc_population_monthly_tick_recent days = 27 }",
        "aawc_population_apply_monthly_growth_character_effect = yes",
        "trigger_event = { id = aawc_population_event.0100 days = 31 }",
    ):
        if clause not in recurring_event:
            failures.append(f"recurring event lost scheduler guard: {clause}")
    if "aawc_population_recover_missing_monthly_schedulers_effect = yes" not in delayed_start:
        failures.append("delayed startup does not recover rulers created after the first scheduler pass")
    for clause in (
        "current_date_is_start_date_trigger = no",
        "scope:title = { tier = tier_county }",
        "aawc_population_apply_county_holding_cadence_recovery_effect = yes",
        "trigger_event = { id = aawc_population_event.0100 days = 31 }",
    ):
        if clause not in title_gain:
            failures.append(f"county-gain cadence recovery omits {clause}")

    production_calls = 0
    test_calls = 0
    for path in MOD_ROOT.rglob("*.txt"):
        code = uncommented(path.read_text(encoding="utf-8-sig", errors="ignore"))
        production_calls += code.count(
            "aawc_reforging_cohort_apply_production_month_effect = yes"
        )
        test_calls += code.count("aawc_reforging_cohort_stage1_test_advance_effect = yes")
    if production_calls != 2:
        failures.append(f"production month has {production_calls} callers, expected recurring and county-gain routes")
    if test_calls != 2:
        failures.append(
            f"test advance has {test_calls} callers, expected the event and military-fixture callers"
        )

    ledger = Ledger.survivor()
    initial = sum(ledger.bands)
    for tick_id in range(1, 61):
        ledger.tick(tick_id)
    after_60 = sum(ledger.bands)
    snapshot = ledger.snapshot_people()
    if ledger.tick(60) is not None or ledger.snapshot_people() != snapshot:
        failures.append("duplicate production tick is not a no-op")
    if ledger.tick_count != 60 or not ledger.invariant():
        failures.append("60-month candidate simulation violates cadence or invariants")

    if failures:
        print("AAWC Reforging Milestone 1 candidate activation validation: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("AAWC Reforging Milestone 1 candidate activation validation: PASS")
    print("- the recurring and county-gain routes share one province-guarded cohort production adapter")
    print("- legacy aggregate capacity-rate growth is absent from the live holding-month authority")
    print("- two production entry routes share one guarded adapter; the opt-in test callers remain isolated")
    print(f"- deterministic 60-month candidate run: {initial} -> {after_60} residents, 60 ticks, duplicate no-op")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
