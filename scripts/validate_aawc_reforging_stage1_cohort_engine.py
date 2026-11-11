#!/usr/bin/env python3
"""Validate the Milestone 1 cohort engine and guarded recurring authority."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext
import json
from pathlib import Path
import re


getcontext().prec = 28

ROOT = Path(__file__).resolve().parents[1]
MOD_ROOT = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
EFFECTS = MOD_ROOT / "common" / "scripted_effects" / "aawc_reforging_cohort_stage1_effects.txt"
VALUES = MOD_ROOT / "common" / "script_values" / "aawc_reforging_cohort_stage1_values.txt"
EVENTS = MOD_ROOT / "events" / "aawc_reforging_cohort_pilot_events.txt"
DECISIONS = MOD_ROOT / "common" / "decisions" / "aawc_reforging_cohort_pilot_decisions.txt"
PRODUCTION = MOD_ROOT / "common" / "scripted_effects" / "aawc_reforging_cohort_production_effects.txt"
LOCALIZATION = MOD_ROOT / "localization" / "english" / "aawc_reforging_cohort_pilot_l_english.yml"
GUI_LOCALIZATION = MOD_ROOT / "localization" / "english" / "aawc_population_l_english.yml"

BAND_SUFFIXES = (
    "00_04", "05_09", "10_14", "15_19", "20_24", "25_29", "30_34",
    "35_39", "40_44", "45_49", "50_54", "55_59", "60_plus",
)
BANDS = tuple(f"aawc_reforging_cohort_age_{suffix}" for suffix in BAND_SUFFIXES)
ADULT_INDEXES = tuple(range(3, 12))
MILITARY = tuple(f"aawc_reforging_military_age_{BAND_SUFFIXES[index]}" for index in ADULT_INDEXES)
MILITARY_ELIGIBILITY = tuple(
    f"aawc_reforging_military_building_eligibility_age_{BAND_SUFFIXES[index]}"
    for index in ADULT_INDEXES
)
STAGE2_CONDITION_INPUTS = tuple(
    f"aawc_reforging_stage2_{name}_input"
    for name in (
        "sustenance", "habitation", "opportunity", "health", "security",
        "amenities", "capacity_pressure",
    )
)
STAGE2_NEUTRAL_MULTIPLIERS = (
    "aawc_reforging_stage2_birth_rate_multiplier",
    "aawc_reforging_stage2_mortality_rate_multiplier",
)
STAGE2_AGE_MORTALITY_MULTIPLIERS = tuple(
    f"aawc_reforging_stage2_mortality_multiplier_age_{suffix}"
    for suffix in BAND_SUFFIXES
)
STAGE2_DEMOGRAPHIC_VALUES = {
    "aawc_reforging_stage2_habitation_deficit",
    "aawc_reforging_stage2_habitation_surplus",
    "aawc_reforging_stage2_sustenance_deficit",
    "aawc_reforging_stage2_sustenance_surplus",
    "aawc_reforging_stage2_opportunity_deficit",
    "aawc_reforging_stage2_opportunity_surplus",
    "aawc_reforging_stage2_health_deficit",
    "aawc_reforging_stage2_health_surplus",
    "aawc_reforging_stage2_security_disruption",
    "aawc_reforging_stage2_security_danger",
    "aawc_reforging_stage2_birth_habitation_factor",
    "aawc_reforging_stage2_birth_sustenance_factor",
    "aawc_reforging_stage2_birth_opportunity_factor",
    "aawc_reforging_stage2_birth_security_factor",
    "aawc_reforging_stage2_mortality_multiplier_infant",
    "aawc_reforging_stage2_mortality_multiplier_child",
    "aawc_reforging_stage2_mortality_multiplier_young_adult",
    "aawc_reforging_stage2_mortality_multiplier_mature_adult",
    "aawc_reforging_stage2_mortality_multiplier_older_adult",
    "aawc_reforging_stage2_mortality_multiplier_elderly",
} | set(STAGE2_AGE_MORTALITY_MULTIPLIERS)
MORTALITY_FRACTIONS = tuple(
    f"aawc_reforging_mortality_fraction_age_{suffix}" for suffix in BAND_SUFFIXES
)
AGING_FRACTIONS = tuple(
    f"aawc_reforging_aging_fraction_age_{suffix}" for suffix in BAND_SUFFIXES[:-1]
)
MILITARY_AGING_FRACTIONS = tuple(
    f"aawc_reforging_military_aging_fraction_age_{BAND_SUFFIXES[index]}"
    for index in ADULT_INDEXES
)
ALL_FRACTIONS = (
    ("aawc_reforging_birth_fraction",)
    + MORTALITY_FRACTIONS
    + AGING_FRACTIONS
    + MILITARY_AGING_FRACTIONS
    + ("aawc_reforging_military_training_fraction",)
)
MIRRORS = (
    "aawc_reforging_cohort_children_mirror",
    "aawc_reforging_cohort_young_adults_mirror",
    "aawc_reforging_cohort_older_adults_mirror",
    "aawc_reforging_cohort_elderly_mirror",
    "aawc_reforging_cohort_total_mirror",
    "aawc_reforging_military_total_mirror",
    "aawc_reforging_civilian_adults_mirror",
)
INITIAL = (9, 8, 8, 8, 8, 8, 8, 8, 7, 7, 6, 5, 10)
BIRTH_RATE = Decimal("0.011")
ANNUAL_MORTALITY = tuple(
    Decimal(rate)
    for rate in (
        "0.012", "0.003", "0.003", "0.005", "0.005", "0.005", "0.006",
        "0.006", "0.010", "0.012", "0.016", "0.022", "0.055",
    )
)

REQUIRED_EFFECTS = {
    "aawc_reforging_cohort_refresh_mirrors_effect",
    "aawc_reforging_cohort_reconcile_effect",
    "aawc_reforging_cohort_credit_effect",
    "aawc_reforging_cohort_debit_effect",
    "aawc_reforging_cohort_death_effect",
    "aawc_reforging_cohort_classify_military_effect",
    "aawc_reforging_cohort_release_military_effect",
    "aawc_reforging_cohort_stage1_prepare_test_effect",
    "aawc_reforging_cohort_stage1_snapshot_persistence_effect",
    "aawc_reforging_cohort_stage1_persistence_diagnostics_effect",
    "aawc_reforging_cohort_initialize_survivor_effect",
    "aawc_reforging_cohort_initialize_empty_effect",
    "aawc_reforging_cohort_apply_births_effect",
    "aawc_reforging_cohort_apply_band_mortality_effect",
    "aawc_reforging_cohort_apply_mortality_effect",
    "aawc_reforging_cohort_apply_aging_band_effect",
    "aawc_reforging_cohort_apply_military_aging_band_effect",
    "aawc_reforging_cohort_apply_military_retirement_effect",
    "aawc_reforging_cohort_train_military_band_effect",
    "aawc_reforging_cohort_apply_military_training_effect",
    "aawc_reforging_cohort_apply_aging_effect",
    "aawc_reforging_cohort_monthly_authority_effect",
    "aawc_reforging_cohort_stage1_test_advance_effect",
    "aawc_reforging_cohort_stage1_prepare_military_runtime_fixture_effect",
    "aawc_reforging_cohort_stage1_benchmark_cleanup_effect",
    "aawc_reforging_cohort_stage1_benchmark_baseline_effect",
    "aawc_reforging_cohort_stage1_benchmark_engine_effect",
    "aawc_reforging_cohort_production_runtime_cleanup_effect",
    "aawc_reforging_cohort_stage1_production_runtime_test_effect",
    "aawc_reforging_cohort_stage1_zero_mover_runtime_test_effect",
}

REQUIRED_VALUES = {
    "aawc_reforging_cohort_children",
    "aawc_reforging_cohort_young_adults",
    "aawc_reforging_cohort_older_adults",
    "aawc_reforging_cohort_elderly",
    "aawc_reforging_cohort_reproductive_civilians",
    "aawc_reforging_military_building_training_monthly",
    "aawc_reforging_cohort_candidate_monthly_births",
    "aawc_reforging_cohort_stage1_invariant_status",
    "aawc_reforging_cohort_last_tick_accounting_status",
    "aawc_reforging_cohort_stage1_persistence_status",
    "aawc_reforging_cohort_stage1_military_runtime_fixture_status",
    "aawc_reforging_cohort_stage1_benchmark_baseline_status",
    "aawc_reforging_cohort_stage1_benchmark_engine_status",
} | set(MILITARY_ELIGIBILITY) | set(STAGE2_CONDITION_INPUTS) | set(STAGE2_NEUTRAL_MULTIPLIERS) | STAGE2_DEMOGRAPHIC_VALUES | {
    f"aawc_reforging_cohort_candidate_monthly_mortality_age_{suffix}"
    for suffix in BAND_SUFFIXES
}


def uncommented(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def top_level_definitions(text: str) -> set[str]:
    definitions: set[str] = set()
    depth = 0
    for line in uncommented(text).splitlines():
        if depth == 0:
            match = re.match(r"^\s*([A-Za-z0-9_]+)\s*=\s*\{", line)
            if match:
                definitions.add(match.group(1))
        depth += line.count("{") - line.count("}")
    return definitions


def definition_body(text: str, name: str) -> str:
    # Prefer an actual top-level definition over an earlier parameterized call.
    # The fallback remains for callers deliberately extracting a nested block.
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"missing definition {name}")
    start = match.end() - 1
    depth = 0
    in_quote = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
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
                return text[start + 1 : index]
    raise ValueError(f"unclosed definition {name}")


def balanced(text: str) -> bool:
    depth = 0
    in_quote = False
    escaped = False
    for char in uncommented(text):
        if in_quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_quote = False
        elif char == '"':
            in_quote = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not in_quote


@dataclass
class Ledger:
    bands: list[int]
    military: list[int]
    birth_fraction: Decimal
    mortality_fractions: list[Decimal]
    aging_fractions: list[Decimal]
    military_aging_fractions: list[Decimal]
    last_tick: int = -1
    tick_count: int = 0

    @classmethod
    def survivor(cls) -> "Ledger":
        return cls(
            list(INITIAL), [0] * 9, Decimal(0), [Decimal(0)] * 13,
            [Decimal(0)] * 12, [Decimal(0)] * 9,
        )

    def snapshot_people(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        return tuple(self.bands), tuple(self.military)

    def mirrors(self) -> tuple[int, int, int, int, int, int, int]:
        children = sum(self.bands[:3])
        young = sum(self.bands[3:8])
        older = sum(self.bands[8:12])
        elderly = self.bands[12]
        military = sum(self.military)
        adults = young + older
        return children, young, older, elderly, sum(self.bands), military, adults - military

    def invariant(self) -> bool:
        fractions = (
            [self.birth_fraction] + self.mortality_fractions + self.aging_fractions
            + self.military_aging_fractions
        )
        return (
            len(self.bands) == 13
            and len(self.military) == 9
            and all(value >= 0 for value in self.bands)
            and all(0 <= value <= self.bands[index] for value, index in zip(self.military, ADULT_INDEXES, strict=True))
            and all(Decimal(0) <= value < Decimal(1) for value in fractions)
            and sum(self.mirrors()[:4]) == sum(self.bands)
        )

    def reconcile(self) -> None:
        self.bands = [max(0, value) for value in self.bands]
        self.military = [
            min(max(0, value), self.bands[index])
            for value, index in zip(self.military, ADULT_INDEXES, strict=True)
        ]

    def apply_aging(self) -> int:
        """Age parent bands first and carry military membership with actual movers."""
        retired = 0
        for index in range(11, -1, -1):
            source = self.bands[index]
            self.aging_fractions[index] += Decimal(source) / Decimal(60)
            amount = min(source, int(self.aging_fractions[index]))
            self.aging_fractions[index] -= amount
            self.bands[index] -= amount
            self.bands[index + 1] += amount
            if self.bands[index] == 0 and self.aging_fractions[index] >= 1:
                self.aging_fractions[index] = Decimal(0)

            if index in ADULT_INDEXES:
                military_index = ADULT_INDEXES.index(index)
                military_source = self.military[military_index]
                if source > 0 and amount > 0 and military_source > 0:
                    self.military_aging_fractions[military_index] += (
                        Decimal(amount) * Decimal(military_source) / Decimal(source)
                    )
                military_amount = min(
                    amount,
                    military_source,
                    int(self.military_aging_fractions[military_index]),
                )
                self.military_aging_fractions[military_index] -= military_amount
                self.military[military_index] -= military_amount
                if military_index < 8:
                    self.military[military_index + 1] += military_amount
                else:
                    retired += military_amount
        self.reconcile()
        return retired

    def tick(self, tick_id: int) -> tuple[int, int] | None:
        if tick_id == self.last_tick:
            return None
        before = sum(self.bands)
        reproductive = sum(self.bands[3:8]) - sum(self.military[:5])
        self.birth_fraction += Decimal(reproductive) * BIRTH_RATE
        births = int(self.birth_fraction)
        self.birth_fraction -= births
        self.bands[0] += births

        deaths = 0
        for index, rate in enumerate(ANNUAL_MORTALITY):
            self.mortality_fractions[index] += Decimal(self.bands[index]) * rate / Decimal(12)
            amount = min(self.bands[index], int(self.mortality_fractions[index]))
            self.mortality_fractions[index] -= amount
            self.bands[index] -= amount
            deaths += amount
            if self.bands[index] == 0 and self.mortality_fractions[index] >= 1:
                self.mortality_fractions[index] = Decimal(0)
        self.reconcile()

        self.apply_aging()
        self.last_tick = tick_id
        self.tick_count += 1
        assert sum(self.bands) == before + births - deaths
        assert self.invariant()
        return births, deaths


def main() -> int:
    failures: list[str] = []
    paths = (EFFECTS, VALUES, EVENTS, DECISIONS, LOCALIZATION, GUI_LOCALIZATION)
    for path in paths:
        if not path.is_file():
            failures.append(f"missing source file: {path.relative_to(ROOT).as_posix()}")
        elif not path.read_bytes().startswith(b"\xef\xbb\xbf"):
            failures.append(f"source file lacks UTF-8 BOM: {path.relative_to(ROOT).as_posix()}")
    if failures:
        print("AAWC Reforging Milestone 1 cohort engine validation: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    effect_text = EFFECTS.read_text(encoding="utf-8-sig")
    value_text = VALUES.read_text(encoding="utf-8-sig")
    event_text = EVENTS.read_text(encoding="utf-8-sig")
    decision_text = DECISIONS.read_text(encoding="utf-8-sig")
    localization_text = LOCALIZATION.read_text(encoding="utf-8-sig")
    gui_localization_text = GUI_LOCALIZATION.read_text(encoding="utf-8-sig")
    for path, text in zip(paths[:4], (effect_text, value_text, event_text, decision_text), strict=True):
        if not balanced(text):
            failures.append(f"unbalanced script braces/quotes: {path.relative_to(MOD_ROOT).as_posix()}")
    for line_number, line in enumerate(localization_text.splitlines(), start=1):
        if line.strip() and not line.lstrip().startswith(("l_english:", "#")):
            if len(re.findall(r'(?<!\\)"', line)) != 2:
                failures.append(f"localization line {line_number} does not contain one balanced quoted value")

    effect_defs = top_level_definitions(effect_text)
    value_defs = top_level_definitions(value_text)
    if effect_defs != REQUIRED_EFFECTS:
        failures.append(f"unexpected Milestone 1 effect definitions: {sorted(effect_defs ^ REQUIRED_EFFECTS)}")
    ui_values = {
        "aawc_reforging_ui_" + suffix for suffix in (
            "children", "young_adults", "older_adults", "elderly",
            "young_adults_military", "young_adults_civilian",
            "older_adults_military", "older_adults_civilian",
            "last_births", "last_deaths", "last_natural_change", "last_aged",
            "last_transfer_credit", "last_transfer_debit", "last_external_deaths",
        )
    }
    if value_defs != REQUIRED_VALUES | ui_values:
        failures.append(f"unexpected Milestone 1 value definitions: {sorted(value_defs ^ (REQUIRED_VALUES | ui_values))}")
    invariant_body = definition_body(value_text, "aawc_reforging_cohort_stage1_invariant_status")
    if "aawc_reforging_diag_fractional_status = 0" not in uncommented(invariant_body):
        failures.append("Stage 1 invariant does not reject fractional resident/military headcounts")
    for name in ui_values:
        body = definition_body(value_text, name)
        if re.search(r"\b(?:set|change|remove)_variable\b", body):
            failures.append(f"UI getter mutates ledger: {name}")
    gui_rows = []
    tooltip_key = 'tooltip = "AAWC_COHORT_DYNAMIC_TT"'
    if gui_localization_text.count("AAWC_COHORT_DYNAMIC_TT:0") != 1:
        failures.append("dynamic cohort tooltip localization is missing or duplicated")
    for token in (
        "aawc_reforging_ui_children", "aawc_reforging_ui_young_adults",
        "aawc_reforging_ui_older_adults", "aawc_reforging_ui_elderly",
        "aawc_reforging_ui_last_births", "aawc_reforging_ui_last_deaths",
        "aawc_reforging_ui_last_natural_change", "aawc_reforging_ui_last_aged",
        "aawc_reforging_ui_last_transfer_credit", "aawc_reforging_ui_last_transfer_debit",
        "aawc_reforging_ui_last_external_deaths",
    ):
        if gui_localization_text.count(f"ScriptValue('{token}')") != 1:
            failures.append(f"dynamic cohort tooltip localization lacks one exact {token} getter")
    for folder in ("gui", "gui_folder_valyria"):
        gui = (MOD_ROOT / folder / "window_county_view.gui").read_text(encoding="utf-8-sig")
        if gui.count(tooltip_key) != 1:
            failures.append(f"{folder}: Total Population lacks dynamic cohort tooltip")
        if "\\n" in gui:
            failures.append(f"{folder}: GUI tooltip contains unsupported backslash newline escapes")
        for cohort in ("CHILDREN", "YOUNG_ADULTS", "OLDER_ADULTS", "ELDERLY", "MEMBERSHIP"):
            if re.search(r'raw_text\s*=\s*"\[Localize\(\'AAWC_COHORT_' + cohort, gui):
                failures.append(f"{folder}: cohort row remains persistently visible: {cohort}")
        if "Localize('AAWC_POPULATION_LABEL_LEVIES')" in gui or "Localize('AAWC_POPULATION_LABEL_GROWTH_RATING')" in gui:
            failures.append(f"{folder}: retired demographic formula remains visible")
        gui_rows.append(re.findall(r'tooltip = "AAWC_COHORT_DYNAMIC_TT"', gui))
    if gui_rows[0] != gui_rows[1]:
        failures.append("standard and Valyria cohort displays diverge")

    forbidden_scan = uncommented(effect_text)
    for test_only_effect in (
        "aawc_reforging_cohort_production_runtime_cleanup_effect",
        "aawc_reforging_cohort_stage1_production_runtime_test_effect",
        "aawc_reforging_cohort_stage1_zero_mover_runtime_test_effect",
    ):
        try:
            forbidden_scan = forbidden_scan.replace(
                definition_body(effect_text, test_only_effect), "", 1
            )
        except ValueError as error:
            failures.append(str(error))
    forbidden = (
        "aawc_population_current", "aawc_population_reserved", "aawc_migration_",
        "aawc_population_maa", "add_building", "remove_building", "men_at_arms",
    )
    for token in forbidden:
        if token in forbidden_scan or token in uncommented(value_text):
            failures.append(f"Milestone 1 source touches forbidden later/live identifier: {token}")

    try:
        refresh = definition_body(effect_text, "aawc_reforging_cohort_refresh_mirrors_effect")
        reconcile = definition_body(effect_text, "aawc_reforging_cohort_reconcile_effect")
        mortality = definition_body(effect_text, "aawc_reforging_cohort_apply_mortality_effect")
        aging = definition_body(effect_text, "aawc_reforging_cohort_apply_aging_effect")
        aging_band = definition_body(effect_text, "aawc_reforging_cohort_apply_aging_band_effect")
        military_aging_band = definition_body(effect_text, "aawc_reforging_cohort_apply_military_aging_band_effect")
        military_retirement = definition_body(effect_text, "aawc_reforging_cohort_apply_military_retirement_effect")
        military_training = definition_body(effect_text, "aawc_reforging_cohort_apply_military_training_effect")
        authority = definition_body(effect_text, "aawc_reforging_cohort_monthly_authority_effect")
        empty = definition_body(effect_text, "aawc_reforging_cohort_initialize_empty_effect")
    except ValueError as error:
        failures.append(str(error))
        refresh = reconcile = mortality = aging = aging_band = military_aging_band = military_retirement = military_training = authority = empty = ""

    if re.search(r"(?:cohort_age|military_age|fraction).*name\s*=", refresh):
        failures.append("mirror refresh appears to mutate authoritative people/fraction state")
    for band in BANDS:
        if band not in reconcile or band not in empty:
            failures.append(f"reconcile/empty initialization omits {band}")
    for military in MILITARY:
        if military not in reconcile or military not in empty:
            failures.append(f"reconcile/empty initialization omits {military}")
    # Natural wrappers now delegate to the generated pooled Hamilton source.
    # The legacy per-band oracle below remains a historical regression only.
    from generate_aawc_cohort_rounding import generate, P, PERSISTENT
    for path, expected in generate().items():
        if path.read_bytes() != expected.encode('utf-8-sig'):
            failures.append("generated all-flow source differs: " + path.name)
    for body, route in ((mortality, 'mortality'), (aging, 'aging'),
                        (aging_band, 'compat_aging'),
                        (military_aging_band, 'compat_military'),
                        (military_retirement, 'compat_military')):
        if P + route + '_effect = ' not in body:
            failures.append('missing all-flow route: ' + route)
    if P + 'pending_valid_value = 0' not in invariant_body:
        failures.append('invariant omits additive pending state')
    for clause in (
        "NOT = { has_variable = aawc_reforging_cohort_tick_in_progress }",
        "NOT = { var:aawc_reforging_cohort_last_tick = $TICK_ID$ }",
        "aawc_reforging_cohort_apply_births_effect = yes",
        "aawc_reforging_cohort_apply_mortality_effect = yes",
        "aawc_reforging_cohort_apply_aging_effect = yes",
        "aawc_reforging_cohort_apply_military_training_effect = yes",
        "remove_variable = aawc_reforging_cohort_tick_in_progress",
    ):
        if clause not in " ".join(authority.split()):
            failures.append(f"single tick authority omits guard/stage: {clause}")

    for suffix, rate in zip(BAND_SUFFIXES, ANNUAL_MORTALITY, strict=True):
        body = definition_body(value_text, f"aawc_reforging_cohort_candidate_monthly_mortality_age_{suffix}")
        if f"multiply = {rate:.3f}" not in body or "divide = 12" not in body:
            failures.append(f"approved Milestone 1 mortality coefficient mismatch for {suffix}")
        if f"multiply = aawc_reforging_stage2_mortality_multiplier_age_{suffix}" not in body:
            failures.append(f"Stage 2 mortality extension input missing for {suffix}")
    birth_body = definition_body(value_text, "aawc_reforging_cohort_candidate_monthly_births")
    if "multiply = 0.011" not in birth_body:
        failures.append("approved Milestone 1 birth coefficient mismatch")
    if "multiply = aawc_reforging_stage2_birth_rate_multiplier" not in birth_body:
        failures.append("Stage 2 birth extension input missing")
    for name in STAGE2_CONDITION_INPUTS:
        dimension = name.removeprefix("aawc_reforging_stage2_").removesuffix("_input")
        expected = "aawc_stage2_occupancy" if dimension == "capacity_pressure" else f"aawc_stage2_effective_{dimension}_value"
        if " ".join(definition_body(value_text, name).split()) != f"value = {expected}":
            failures.append(f"Stage 2 input is not bound to effective conditions: {name}")
    birth_multiplier = definition_body(value_text, "aawc_reforging_stage2_birth_rate_multiplier")
    for factor in ("habitation", "sustenance", "opportunity", "security"):
        if f"aawc_reforging_stage2_birth_{factor}_factor" not in birth_multiplier:
            failures.append(f"Stage 2 birth multiplier omits {factor}")
    if "amenities" in birth_multiplier or "health" in birth_multiplier:
        failures.append("Stage 2 birth multiplier directly includes Health or Amenities")
    if " ".join(definition_body(value_text, "aawc_reforging_stage2_mortality_rate_multiplier").split()) != "value = 1":
        failures.append("Stage 2 compatibility mortality multiplier is not neutral")
    training_rate = definition_body(value_text, "aawc_reforging_military_building_training_monthly")
    training_band = definition_body(effect_text, "aawc_reforging_cohort_train_military_band_effect")
    if "value = 0" not in " ".join(training_rate.split()):
        failures.append("unsupported building training throughput is not explicitly disabled")
    for value_name in MILITARY_ELIGIBILITY:
        eligibility_body = definition_body(value_text, value_name)
        if "value = 0" not in " ".join(eligibility_body.split()):
            failures.append(f"unsupported age-specific eligibility is not disabled: {value_name}")
        if f"ELIGIBILITY = {value_name}" not in military_training:
            failures.append(f"military training omits age-specific building contract: {value_name}")
    rejected_policy = uncommented(value_text + "\n" + effect_text)
    for token in (
        "multiply = 0.0025",
        "multiply = 0.025",
        "multiply = 0.10",
        "aawc_reforging_military_training_capacity",
        "aawc_reforging_military_capacity_building_tiers",
        "aawc_reforging_military_training_building_tiers",
    ):
        if token in rejected_policy:
            failures.append(f"rejected arbitrary military allocation policy survived: {token}")
    eligibility_start = value_text.index(MILITARY_ELIGIBILITY[0])
    eligibility_end = value_text.index("# Approved Milestone 1 neutral birth", eligibility_start)
    if "has_building =" in uncommented(value_text[eligibility_start:eligibility_end]):
        failures.append("review-only catalogue was silently mapped to live building IDs")
    for token in (
        "aawc_reforging_military_training_fraction",
        "aawc_reforging_civilian_available_adults",
        "aawc_reforging_military_building_training_monthly",
        "aawc_reforging_cohort_classify_military_effect",
    ):
        if token not in military_training and token not in training_band:
            failures.append(f"military training lifecycle omits {token}")

    # The recurring authority may be called only by the explicit test adapter
    # and the audited production adapter. The test adapter remains reachable
    # only through the opt-in event harness.
    allowed = {EFFECTS.resolve(), EVENTS.resolve(), PRODUCTION.resolve()}
    for path in MOD_ROOT.rglob("*.txt"):
        if path.resolve() in allowed:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for token in (
            "aawc_reforging_cohort_monthly_authority_effect",
            "aawc_reforging_cohort_stage1_test_advance_effect",
        ):
            if token in uncommented(text):
                failures.append(f"cohort tick escaped audited caller boundary: {path.relative_to(MOD_ROOT).as_posix()}")
    if event_text.count("aawc_reforging_cohort_stage1_test_advance_effect = yes") != 1:
        failures.append("test advance effect must have exactly one event caller")
    if "aawc_reforging_stage1a.0003" not in event_text or "aawc_reforging_stage1a.0003" not in decision_text:
        failures.append("explicit one-month test event/decision is incomplete")
    if "aawc_reforging_stage1a.0007" not in event_text or "aawc_reforging_stage1a.0007" not in decision_text:
        failures.append("production-adapter runtime regression event/decision is incomplete")
    if "aawc_reforging_stage1a.0008" not in event_text or "aawc_reforging_stage1a.0008" not in decision_text:
        failures.append("zero-mover runtime regression event/decision is incomplete")
    if len(ALL_FRACTIONS) != 36 or len(set(ALL_FRACTIONS)) != 36:
        failures.append("fractional persistence inventory is not exactly 36 unique carries")
    try:
        persistence_snapshot = definition_body(
            effect_text, "aawc_reforging_cohort_stage1_snapshot_persistence_effect"
        )
        persistence_diagnostic = definition_body(
            effect_text, "aawc_reforging_cohort_stage1_persistence_diagnostics_effect"
        )
        persistence_status = definition_body(
            value_text, "aawc_reforging_cohort_stage1_persistence_status"
        )
        tick_event = definition_body(event_text, "aawc_reforging_stage1a.0003")
        inspect_event = definition_body(event_text, "aawc_reforging_stage1a.0002")
    except ValueError as error:
        failures.append(str(error))
        persistence_snapshot = persistence_diagnostic = persistence_status = tick_event = inspect_event = ""
    for fraction in ALL_FRACTIONS:
        expected = "aawc_reforging_persistence_expected_" + fraction.removeprefix("aawc_reforging_")
        snapshot_clause = f"name = {expected} value = var:{fraction}"
        status_clause = f"var:{fraction} = var:{expected}"
        if snapshot_clause not in " ".join(persistence_snapshot.split()):
            failures.append(f"persistence snapshot omits carry: {fraction}")
        if status_clause not in " ".join(persistence_status.split()):
            failures.append(f"persistence comparison omits carry: {fraction}")
    if P + 'snapshot_effect = yes' not in persistence_snapshot:
        failures.append('persistence snapshot omits additive rounding state')
    if P + 'persistence_status_value = 0' not in persistence_status:
        failures.append('persistence comparison omits additive rounding state')
    expected_state = {
        **{name: "aawc_reforging_persistence_expected_" + name.removeprefix("aawc_reforging_cohort_") for name in BANDS},
        **{name: "aawc_reforging_persistence_expected_" + name.removeprefix("aawc_reforging_") for name in MILITARY},
        **{name: "aawc_reforging_persistence_expected_" + name.removeprefix("aawc_reforging_cohort_") for name in MIRRORS[:5]},
        "aawc_reforging_military_total_mirror": "aawc_reforging_persistence_expected_military_total_mirror",
        "aawc_reforging_civilian_adults_mirror": "aawc_reforging_persistence_expected_civilian_adults_mirror",
    }
    normalized_snapshot = " ".join(persistence_snapshot.split())
    normalized_status = " ".join(persistence_status.split())
    for current, expected in expected_state.items():
        if f"name = {expected} value = var:{current}" not in normalized_snapshot:
            failures.append(f"persistence snapshot omits ledger field: {current}")
        if f"var:{current} = var:{expected}" not in normalized_status:
            failures.append(f"persistence comparison omits ledger field: {current}")
    if re.search(r"\b(?:set|change|remove)_variable\b", persistence_diagnostic):
        failures.append("post-reload persistence diagnostic is not read-only")
    if "aawc_reforging_cohort_stage1_test_advance_effect = yes" not in tick_event:
        failures.append("event .0003 does not exercise the guarded Stage-1 tick")
    elif tick_event.index("aawc_reforging_cohort_stage1_test_advance_effect = yes") > tick_event.index(
        "aawc_reforging_cohort_stage1_snapshot_persistence_effect = yes"
    ):
        failures.append("event .0003 snapshots persistence before advancing the Stage-1 tick")
    if "aawc_reforging_cohort_stage1_persistence_diagnostics_effect = yes" not in inspect_event:
        failures.append("event .0002 does not invoke the read-only Stage-1 persistence diagnostic")
    for token in (
        "aawc_reforging_stage1a.tick_pass", "aawc_reforging_stage1a.tick_fail",
        "aawc_reforging_stage1a.persistence_pass", "aawc_reforging_stage1a.persistence_fail",
        "aawc_reforging_stage1a_advance_tick_decision",
        "aawc_reforging_stage1a_prepare_military_fixture_decision",
        "aawc_reforging_stage1a_benchmark_baseline_decision",
        "aawc_reforging_stage1a_benchmark_engine_decision",
        "aawc_reforging_stage1a_production_runtime_decision",
        "aawc_reforging_stage1a_zero_mover_runtime_decision",
        "aawc_reforging_stage1a.full_state_vector",
    ):
        if token not in localization_text:
            failures.append(f"test harness localization omits {token}")
    for token in (
        "aawc_reforging_cohort_stage1_prepare_military_runtime_fixture_effect",
        "aawc_reforging_cohort_stage1_benchmark_cleanup_effect",
        "aawc_reforging_cohort_stage1_benchmark_baseline_effect",
        "aawc_reforging_cohort_stage1_benchmark_engine_effect",
        "aawc_reforging_cohort_stage1_zero_mover_runtime_test_effect",
    ):
        if token not in effect_text:
            failures.append(f"runtime coverage effect missing: {token}")
    zero_mover_runtime = definition_body(
        effect_text, "aawc_reforging_cohort_stage1_zero_mover_runtime_test_effect"
    )
    if "save_scope_as = aawc_reforging_zero_mover_runtime_province" not in zero_mover_runtime:
        failures.append("zero-mover runtime harness does not select its disposable province by scope")
    if "var:aawc_reforging_zero_mover_runtime_selected <" in zero_mover_runtime:
        failures.append("zero-mover runtime harness reads a setup-only selection variable in preview")
    if "var:aawc_reforging_zero_mover_runtime_selected = 1" in zero_mover_runtime:
        failures.append("zero-mover runtime harness performs a preview-unsafe final selection read")
    for token in (
        "save_scope_as = aawc_reforging_benchmark_owner",
        "scope:aawc_reforging_benchmark_owner = {",
        "var:aawc_reforging_benchmark_count < 1024",
        "count = 12",
        "aawc_reforging_cohort_stage1_benchmark_cleanup_effect = yes",
        "NOT = { has_variable = aawc_reforging_cohort_test_initialized }",
    ):
        if token not in effect_text:
            failures.append(f"bounded benchmark contract missing: {token}")
    if "root.var:aawc_reforging_benchmark_count" in effect_text:
        failures.append("bounded benchmark still relies on an ambiguous iterator root variable")
    for effect_name in (
        "aawc_reforging_cohort_stage1_benchmark_baseline_effect",
        "aawc_reforging_cohort_stage1_benchmark_engine_effect",
    ):
        benchmark_body = definition_body(effect_text, effect_name)
        province_pos = benchmark_body.find("every_province = {")
        cap_pos = benchmark_body.find("var:aawc_reforging_benchmark_count < 1024", province_pos)
        body_if_pos = benchmark_body.find("if = {", province_pos)
        if province_pos < 0 or body_if_pos < 0 or cap_pos < body_if_pos:
            failures.append(
                f"{effect_name} does not enforce its 1,024 cap sequentially in the iterator body"
            )
    military_aging_effect = definition_body(
        effect_text, "aawc_reforging_cohort_apply_military_aging_band_effect"
    )
    military_retirement_effect = definition_body(
        effect_text, "aawc_reforging_cohort_apply_military_retirement_effect"
    )
    from generate_aawc_cohort_rounding import OUTPUT, read
    rounded_text = OUTPUT.read_text(encoding='utf-8-sig')
    selected = definition_body(rounded_text, P + 'compat_military_effect')
    if read('aawc_reforging_cohort_work_aged') not in selected:
        failures.append('military compatibility selection lacks zero-safe parent read')
    if 'max = ' + read('aawc_reforging_cohort_work_aged') not in selected:
        failures.append('military compatibility selection exceeds exact parent movers')
    if 'while =' in selected:
        failures.append('military compatibility selection uses per-person iteration')
    for route, counter in (('move', 'aged'), ('retire', 'retired')):
        action = definition_body(rounded_text, P + 'compat_military_' + route + '_effect')
        if 'name = aawc_reforging_cohort_last_military_' + counter not in action or 'add = $AMOUNT$' not in action:
            failures.append('military compatibility action does not record applied count: ' + route)
    military_fixture = definition_body(
        effect_text, "aawc_reforging_cohort_stage1_prepare_military_runtime_fixture_effect"
    )
    for token in (
        "aawc_reforging_cohort_runtime_military_fixture",
        "aawc_reforging_aging_fraction_age_15_19 value = 0.01",
        "aawc_reforging_military_aging_fraction_age_15_19 value = 0.99",
        "aawc_reforging_cohort_age_55_59 value = 4",
        "aawc_reforging_military_age_55_59 value = 4",
    ):
        if token not in military_fixture:
            failures.append(f"military runtime fixture omits adversarial field: {token}")

    # Deterministic 50-year neutral reference and conservation proof.
    neutral = Ledger.survivor()
    for tick_id in range(1, 601):
        neutral.tick(tick_id)
    neutral_total = sum(neutral.bands)
    if not 540 <= neutral_total <= 660:
        failures.append(f"approved Milestone 1 50-year neutral result is {neutral_total}, outside 600 +/-10%")

    # Duplicate serial must be a no-op, including all fractional state.
    duplicate = Ledger.survivor()
    duplicate.tick(1)
    state_before_duplicate = repr(duplicate)
    if duplicate.tick(1) is not None or repr(duplicate) != state_before_duplicate:
        failures.append("duplicate tick serial mutates deterministic state")

    # Non-runtime save/reload transport proof for the complete carry inventory.
    # Every carry is deliberately unique so an omission, reordering, or reset is
    # observable. Actual CK3 save serialization remains a separate runtime gate.
    carry_values = [Decimal(index) / Decimal(38) for index in range(1, 37)]
    persistence_probe = Ledger(
        list(INITIAL), [0] * 9, carry_values[0], carry_values[1:14],
        carry_values[14:26], carry_values[26:35], last_tick=17, tick_count=17,
    )
    persistence_payload = dict(zip(ALL_FRACTIONS, (str(value) for value in carry_values), strict=True))
    persistence_payload["aawc_reforging_cohort_last_tick"] = persistence_probe.last_tick
    persistence_payload["aawc_reforging_cohort_tick_count"] = persistence_probe.tick_count
    persistence_reload = json.loads(json.dumps(persistence_payload, sort_keys=True))
    if any(persistence_reload[name] != str(value) for name, value in zip(ALL_FRACTIONS, carry_values, strict=True)):
        failures.append("36-carry deterministic save/reload transport changes a fractional value")
    if persistence_reload["aawc_reforging_cohort_last_tick"] != 17 or persistence_reload[
        "aawc_reforging_cohort_tick_count"
    ] != 17:
        failures.append("deterministic save/reload transport changes tick identity")

    # Military overlays must age, retire at 60+, and remain parent-bounded.
    military = Ledger.survivor()
    military.military = [2, 3, 4, 4, 3, 2, 2, 1, 1]
    for tick_id in range(1, 241):
        military.tick(tick_id)
    if not military.invariant():
        failures.append("military overlay model violates parent/fraction bounds")
    if military.military_aging_fractions == [Decimal(0)] * 9:
        failures.append("military overlay aging carries never changed")

    # Regression: a mature military carry with no parent-band mover used to
    # transfer into an empty destination and then disappear in reconciliation.
    divergent = Ledger(
        [0] * 13, [0] * 9, Decimal(0), [Decimal(0)] * 13,
        [Decimal(0)] * 12, [Decimal(0)] * 9,
    )
    divergent.bands[3] = 1
    divergent.military[0] = 1
    divergent.military_aging_fractions[0] = Decimal("0.99")
    divergent_before_population = sum(divergent.bands)
    divergent_before_military = sum(divergent.military)
    retired = divergent.apply_aging()
    if sum(divergent.bands) != divergent_before_population:
        failures.append("divergent-carry aging changes total population")
    if sum(divergent.military) + retired != divergent_before_military:
        failures.append("divergent-carry aging loses military membership")
    if not divergent.invariant():
        failures.append("divergent-carry aging/reconciliation violates invariants")

    # Adversarial mixed carries exercise every adult transition and retirement.
    adversarial = Ledger(
        [0, 0, 0, 3, 2, 4, 1, 5, 2, 6, 1, 4, 0],
        [3, 1, 4, 1, 3, 2, 5, 1, 4],
        Decimal(0), [Decimal(0)] * 13,
        [Decimal("0.99") if index % 2 else Decimal("0.01") for index in range(12)],
        [Decimal("0.99") if index % 2 == 0 else Decimal("0.01") for index in range(9)],
    )
    adversarial_before_population = sum(adversarial.bands)
    adversarial_before_military = sum(adversarial.military)
    adversarial_retired = adversarial.apply_aging()
    if sum(adversarial.bands) != adversarial_before_population:
        failures.append("adversarial aging changes total population")
    if sum(adversarial.military) + adversarial_retired != adversarial_before_military:
        failures.append("adversarial aging loses military membership")
    if not adversarial.invariant():
        failures.append("adversarial aging/reconciliation violates invariants")

    # Exhaust every adult/retirement edge over small parent populations and
    # deliberately opposed normalized carries. This proves the bounds rather
    # than relying only on the two named regression fixtures.
    exhaustive_cases = 0
    for parent_index in ADULT_INDEXES:
        military_index = ADULT_INDEXES.index(parent_index)
        for parent_count in range(1, 7):
            for military_count in range(parent_count + 1):
                for parent_carry in (Decimal("0.01"), Decimal("0.49"), Decimal("0.99")):
                    for military_carry in (Decimal("0.01"), Decimal("0.49"), Decimal("0.99")):
                        probe = Ledger(
                            [0] * 13, [0] * 9, Decimal(0), [Decimal(0)] * 13,
                            [Decimal(0)] * 12, [Decimal(0)] * 9,
                        )
                        probe.bands[parent_index] = parent_count
                        probe.military[military_index] = military_count
                        probe.aging_fractions[parent_index] = parent_carry
                        probe.military_aging_fractions[military_index] = military_carry
                        before_population = sum(probe.bands)
                        before_military = sum(probe.military)
                        probe_retired = probe.apply_aging()
                        exhaustive_cases += 1
                        if sum(probe.bands) != before_population:
                            failures.append("exhaustive divergent-carry aging changes total population")
                            break
                        if sum(probe.military) + probe_retired != before_military:
                            failures.append("exhaustive divergent-carry aging loses military membership")
                            break
                        if not probe.invariant():
                            failures.append("exhaustive divergent-carry aging/reconciliation violates invariants")
                            break

    # Read-only derived refresh cannot alter authoritative people.
    refresh_probe = Ledger.survivor()
    people_before = refresh_probe.snapshot_people()
    _ = refresh_probe.mirrors()
    if refresh_probe.snapshot_people() != people_before:
        failures.append("derived mirror refresh mutates authoritative people")

    # Civilian cohort transfer primitives conserve shared population exactly.
    source = Ledger.survivor()
    destination = Ledger(
        [0] * 13, [0] * 9, Decimal(0), [Decimal(0)] * 13,
        [Decimal(0)] * 12, [Decimal(0)] * 9,
    )
    package = [1, 1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1]
    combined_before = sum(source.bands) + sum(destination.bands)
    for index, amount in enumerate(package):
        moved = min(amount, source.bands[index])
        source.bands[index] -= moved
        destination.bands[index] += moved
    if sum(source.bands) + sum(destination.bands) != combined_before:
        failures.append("cohort debit/credit transfer model fails shared conservation")
    if not source.invariant() or not destination.invariant():
        failures.append("cohort debit/credit transfer model violates ledger invariants")

    if failures:
        print("AAWC Reforging Milestone 1 cohort engine validation: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("AAWC Reforging Milestone 1 cohort engine validation: PASS")
    print("- complete additive source: fresh survivor/empty initialization, 13 bands, 4 mirrors, 9 military overlays")
    print("- bounded credit, debit, death, military classification/release, reconciliation, and audit primitives")
    print("- fractional births, 13 mortality bands, 12 five-year transfers, bounded support training, military aging and age-60 retirement")
    print("- approved Milestone 1 tuning reaches the sole guarded authority through one audited production adapter")
    print(f"- historical per-band oracle: {neutral_total} residents; not current-policy calibration")
    from aawc_cohort_rounding_reference import reference as all_flows_reference
    print(f"- selected neutral all-flows oracle: {sum(all_flows_reference(600).bands)} residents; Stage 2 conditions now modulate live rates")
    print(f"- divergent/adversarial carry membership and population conservation pass across {exhaustive_cases} exhaustive edge cases")
    print("- .0003/.0002 persistence contract preserves the full ledger/mirrors and all 36 demographic/training carries")
    print("- opt-in nonzero-military fixture, production-adapter regression, and bounded 1,024-province x 12-month CK3 benchmark routes are source-complete")
    print("- monthly accounting, fractional normalization, overlay bounds, refresh immutability, transfer conservation, and duplicate-tick no-op pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
