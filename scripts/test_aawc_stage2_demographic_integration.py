"""Focused source-executing checks for Stage 2 natural demography.

These scenarios execute the current CK3 script-value/effect subset in SourceVM.
They validate deterministic formula behavior, not native CK3 parser/runtime or UI.
"""

from __future__ import annotations

from pathlib import Path
import unittest

from generate_aawc_stage2_conditions import rows

from test_aawc_cohort_bounded_arithmetic import P, S, SourceVM
from validate_aawc_reforging_stage1_cohort_engine import (
    BAND_SUFFIXES,
    BANDS,
    MOD_ROOT,
    definition_body,
)


DIMENSIONS = ("sustenance", "habitation", "opportunity", "health", "security", "amenities")
VALUES_PATH = MOD_ROOT / "common/script_values/aawc_reforging_cohort_stage1_values.txt"
CONDITIONS_PATH = MOD_ROOT / "common/scripted_effects/aawc_stage2_condition_effects.txt"
WARFARE_PATH = MOD_ROOT / "common/on_action/aawc_population_warfare_on_actions.txt"
AUTHORITY_PATH = MOD_ROOT / "common/scripted_effects/aawc_reforging_cohort_stage1_effects.txt"
POPULATION_PATH = MOD_ROOT / "common/scripted_effects/aawc_population_effects.txt"


def set_effective(vm: SourceVM, **scores: int) -> None:
    values = {dimension: 50 for dimension in DIMENSIONS}
    values.update(scores)
    for dimension, score in values.items():
        vm.vars[f"aawc_stage2_effective_{dimension}"] = score * S


def set_structural_and_refresh(vm: SourceVM, capacity: int, **scores: int) -> None:
    values = {dimension: 50 for dimension in DIMENSIONS}
    values.update(scores)
    for dimension, score in values.items():
        vm.vars[f"aawc_stage2_structural_{dimension}"] = score * S
    vm.vars["aawc_population_expected"] = capacity * S
    vm.call("aawc_stage2_refresh_effective_effect")


def expected_month(vm: SourceVM) -> tuple[int, int]:
    births = vm.value("aawc_reforging_cohort_candidate_monthly_births")
    deaths = sum(
        vm.value(f"aawc_reforging_cohort_candidate_monthly_mortality_age_{suffix}")
        for suffix in BAND_SUFFIXES
    )
    return births, deaths


class Stage2DemographicIntegration(unittest.TestCase):
    def test_real_infrastructure_recalculation_drives_demographic_divergence(self):
        agricultural = SourceVM()
        agricultural.holding = "city_holding"
        agricultural.buildings = {"aawc_cereal_fields_08", "aawc_longhouses_02", "aawc_infirmaries_04"}
        self.assertTrue(agricultural.buildings <= {row["building"] for row in rows()})
        agricultural.initialize(100)

        fortress = SourceVM()
        fortress.holding = "city_holding"
        fortress.buildings = {"aawc_barracks_08", "aawc_watchtowers_08"}
        self.assertTrue(fortress.buildings <= {row["building"] for row in rows()})
        fortress.initialize(100)

        self.assertEqual(
            tuple(agricultural.vars[band] for band in BANDS),
            tuple(fortress.vars[band] for band in BANDS),
        )
        self.assertGreater(
            agricultural.vars["aawc_stage2_structural_sustenance"],
            fortress.vars["aawc_stage2_structural_sustenance"],
        )
        self.assertGreater(
            fortress.vars["aawc_stage2_structural_security"],
            agricultural.vars["aawc_stage2_structural_security"],
        )
        self.assertGreater(
            agricultural.vars["aawc_population_expected"],
            fortress.vars["aawc_population_expected"],
        )
        agricultural_births, agricultural_deaths = expected_month(agricultural)
        fortress_births, fortress_deaths = expected_month(fortress)
        self.assertGreater(
            agricultural_births - agricultural_deaths,
            fortress_births - fortress_deaths,
        )

        residents_before = tuple(fortress.vars[band] for band in BANDS)
        old_capacity = fortress.vars["aawc_population_expected"]
        old_births, old_deaths = expected_month(fortress)
        fortress.buildings = set(agricultural.buildings)
        fortress.call("aawc_stage2_initialize_conditions_effect")
        new_births, new_deaths = expected_month(fortress)
        self.assertEqual(tuple(fortress.vars[band] for band in BANDS), residents_before)
        self.assertGreater(fortress.vars["aawc_population_expected"], old_capacity)
        self.assertGreater(new_births - new_deaths, old_births - old_deaths)

    def test_fertility_weights_and_dimension_boundaries(self):
        vm = SourceVM()
        set_effective(vm)
        neutral = vm.value("aawc_reforging_stage2_birth_rate_multiplier")
        self.assertEqual(neutral, S)

        reductions = {}
        for dimension in ("habitation", "sustenance", "opportunity"):
            set_effective(vm, **{dimension: 20})
            reductions[dimension] = neutral - vm.value("aawc_reforging_stage2_birth_rate_multiplier")
        self.assertGreater(reductions["habitation"], reductions["sustenance"])
        self.assertGreater(reductions["sustenance"], reductions["opportunity"])
        self.assertGreater(reductions["opportunity"], 0)

        set_effective(vm, security=40)
        self.assertEqual(vm.value("aawc_reforging_stage2_birth_rate_multiplier"), neutral)
        set_effective(vm, security=20)
        self.assertLess(vm.value("aawc_reforging_stage2_birth_rate_multiplier"), neutral)
        for dimension in ("health", "amenities"):
            set_effective(vm, **{dimension: 0})
            self.assertEqual(vm.value("aawc_reforging_stage2_birth_rate_multiplier"), neutral)

    def test_mortality_channels_are_distinct_and_age_sensitive(self):
        vm = SourceVM()
        set_effective(vm)
        for dimension in ("sustenance", "health", "habitation"):
            set_effective(vm, **{dimension: 20})
            self.assertGreater(
                vm.value("aawc_reforging_stage2_mortality_multiplier_age_20_24"), S,
                dimension,
            )
        for dimension in ("opportunity", "amenities"):
            set_effective(vm, **{dimension: 0})
            self.assertEqual(vm.value("aawc_reforging_stage2_mortality_multiplier_age_20_24"), S)

        set_effective(vm, sustenance=20, habitation=20, health=20)
        young = vm.value("aawc_reforging_stage2_mortality_multiplier_age_20_24")
        self.assertGreater(vm.value("aawc_reforging_stage2_mortality_multiplier_age_00_04"), young)
        self.assertGreater(vm.value("aawc_reforging_stage2_mortality_multiplier_age_05_09"), young)
        self.assertGreater(vm.value("aawc_reforging_stage2_mortality_multiplier_age_60_plus"), young)

    def test_balanced_growth_and_poor_below_capacity_decline(self):
        balanced = SourceVM()
        balanced.initialize(100)
        set_structural_and_refresh(balanced, 1000)
        for tick in range(120):
            balanced.tick(tick)
        balanced_total = sum(balanced.vars[band] for band in BANDS)
        self.assertGreater(balanced_total, 100 * S)

        poor = SourceVM()
        poor.initialize(100)
        set_structural_and_refresh(
            poor,
            1000,
            sustenance=20,
            habitation=30,
            opportunity=40,
            health=20,
            security=50,
            amenities=50,
        )
        self.assertEqual(poor.vars["aawc_stage2_occupancy_ratio"], S // 10)
        for tick in range(120):
            poor.tick(tick)
        poor_total = sum(poor.vars[band] for band in BANDS)
        self.assertLess(poor_total, 100 * S)
        self.assertLess(poor_total, balanced_total)

    def test_unhealthy_and_overcrowded_conditions_have_worse_natural_balance(self):
        balanced = SourceVM()
        balanced.initialize(100)
        set_structural_and_refresh(balanced, 200)
        balanced_births, balanced_deaths = expected_month(balanced)

        unhealthy = SourceVM()
        unhealthy.initialize(100)
        set_structural_and_refresh(unhealthy, 200, health=15)
        unhealthy_births, unhealthy_deaths = expected_month(unhealthy)
        self.assertEqual(unhealthy_births, balanced_births)
        self.assertGreater(unhealthy_deaths, balanced_deaths)

        favorable = SourceVM()
        favorable.initialize(100)
        set_structural_and_refresh(favorable, 200, sustenance=90, habitation=90, opportunity=90, health=90)
        favorable_births, favorable_deaths = expected_month(favorable)

        crowded = SourceVM()
        crowded.initialize(100)
        set_structural_and_refresh(crowded, 91, sustenance=90, habitation=90, opportunity=90, health=90)
        crowded_births, crowded_deaths = expected_month(crowded)
        self.assertLess(crowded_births - crowded_deaths, favorable_births - favorable_deaths)
        self.assertLess(crowded.vars["aawc_stage2_effective_habitation"], 90 * S)
        self.assertLess(crowded.vars["aawc_stage2_effective_health"], 90 * S)

    def test_exceptional_structure_is_naturally_unsustainable_near_125_percent(self):
        vm = SourceVM()
        vm.initialize(125)
        set_structural_and_refresh(
            vm,
            100,
            sustenance=100,
            habitation=100,
            opportunity=100,
            health=100,
            security=100,
            amenities=100,
        )
        self.assertEqual(vm.vars["aawc_stage2_occupancy_ratio"], 125 * S // 100)
        self.assertEqual(vm.vars["aawc_stage2_effective_habitation"], 550000)
        self.assertEqual(vm.vars["aawc_stage2_effective_health"], 7725000)
        births, deaths = expected_month(vm)
        self.assertLess(births, deaths)

    def test_crisis_losses_remain_external_and_are_not_recharged(self):
        conditions = CONDITIONS_PATH.read_text(encoding="utf-8-sig")
        warfare = WARFARE_PATH.read_text(encoding="utf-8-sig")
        authority = AUTHORITY_PATH.read_text(encoding="utf-8-sig")
        population = POPULATION_PATH.read_text(encoding="utf-8-sig")
        monthly_authority = definition_body(authority, "aawc_reforging_cohort_monthly_authority_effect")
        warfare_helper = definition_body(population, "aawc_population_apply_warfare_population_loss_effect")
        self.assertNotIn("aawc_reforging_cohort_death_population_effect", conditions)
        self.assertNotIn("aawc_reforging_cohort_death_population_effect", monthly_authority)
        self.assertIn("aawc_population_apply_warfare_population_loss_effect", warfare)
        self.assertIn("aawc_reforging_cohort_death_population_effect", warfare_helper)
        self.assertIn("aawc_population_raid_growth_suppressed", conditions)
        self.assertIn("aawc_population_siege_growth_suppressed", conditions)
        self.assertIn("aawc_reforging_cohort_last_deaths", monthly_authority)
        self.assertNotIn("aawc_reforging_cohort_last_external_deaths", monthly_authority)

    def test_no_target_growth_hard_cap_or_resident_write_in_rate_values(self):
        values = VALUES_PATH.read_text(encoding="utf-8-sig")
        self.assertNotIn("set_variable", values)
        self.assertNotIn("change_variable", values)
        self.assertNotIn("remove_variable", values)
        self.assertNotIn("aawc_reforging_cohort_set_population_target_effect", values)


if __name__ == "__main__":
    unittest.main(verbosity=2)
