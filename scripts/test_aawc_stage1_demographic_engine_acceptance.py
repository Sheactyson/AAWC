"""Focused acceptance tests for the Stage 1 demographic authority.

These tests execute the current scripted-effect/value subset in SourceVM and
compare long projections with the independent integer reference model. They are
STATICALLY/PROTOTYPE VERIFIED evidence, not native CK3 runtime certification.
"""

from __future__ import annotations

import unittest

from aawc_cohort_rounding_reference import ANNUAL, INITIAL, reference
from test_aawc_cohort_bounded_arithmetic import P, S, SourceVM
from validate_aawc_reforging_stage1_cohort_engine import (
    AGING_FRACTIONS,
    BANDS,
    MILITARY,
    STAGE2_NEUTRAL_MULTIPLIERS,
    STAGE2_CONDITION_INPUTS,
)


class Stage1DemographicEngineAcceptance(unittest.TestCase):
    def test_exact_fixture_cohorts_and_authoritative_total(self):
        vm = SourceVM()
        vm.initialize(100)
        self.assertEqual([vm.vars[name] for name in BANDS], [value * S for value in INITIAL])
        self.assertEqual(
            [
                vm.vars[P + "children_mirror"],
                vm.vars[P + "young_adults_mirror"],
                vm.vars[P + "older_adults_mirror"],
                vm.vars[P + "elderly_mirror"],
            ],
            [25 * S, 40 * S, 25 * S, 10 * S],
        )
        self.assertEqual(vm.vars[P + "total_mirror"], sum(vm.vars[name] for name in BANDS))
        self.assertEqual(vm.vars["aawc_population_current"], vm.vars[P + "total_mirror"])

    def test_nondefault_initialization_is_exact_deterministic_and_idempotent(self):
        for total in (1, 2, 37, 99, 101, 1_000_003):
            with self.subTest(total=total):
                left, right = SourceVM(), SourceVM()
                left.vars["aawc_population_current"] = total * S
                right.vars["aawc_population_current"] = total * S
                left.call(P + "ensure_production_ledger_effect")
                right.call(P + "ensure_production_ledger_effect")
                expected = [left.vars[name] for name in BANDS]
                self.assertEqual(expected, [right.vars[name] for name in BANDS])
                self.assertEqual(sum(expected), total * S)
                before = dict(left.vars)
                left.call(P + "ensure_production_ledger_effect")
                self.assertEqual(left.vars, before)

    def test_empty_and_ineligible_holdings_do_not_invent_residents(self):
        empty = SourceVM()
        empty.initialize(0)
        for tick in range(240):
            empty.tick(tick)
        self.assertEqual([empty.vars[name] for name in BANDS], [0] * 13)
        self.assertEqual(empty.vars[P + "total_mirror"], 0)

        ineligible = SourceVM()
        ineligible.valid_settlement = False
        ineligible.vars["aawc_population_current"] = 100 * S
        ineligible.call(P + "ensure_production_ledger_effect")
        self.assertFalse(any(name in ineligible.vars for name in BANDS))
        self.assertNotIn(P + "production_initialized", ineligible.vars)

    def test_each_aging_edge_moves_once_and_conserves_population(self):
        for index, carry in enumerate(AGING_FRACTIONS):
            with self.subTest(source=BANDS[index], destination=BANDS[index + 1]):
                vm = SourceVM()
                vm.initialize(0)
                vm.vars[BANDS[index]] = S
                vm.vars[carry] = 99_000
                before = sum(vm.vars[name] for name in BANDS)
                vm.call(P + "apply_aging_effect")
                self.assertEqual(vm.vars[BANDS[index]], 0)
                self.assertEqual(vm.vars[BANDS[index + 1]], S)
                self.assertEqual(sum(vm.vars[name] for name in BANDS), before)
                self.assertEqual(vm.vars[P + "last_aged"], S)
        elderly = SourceVM()
        elderly.initialize(0)
        elderly.vars[BANDS[-1]] = S
        elderly.call(P + "apply_aging_effect")
        self.assertEqual(elderly.vars[BANDS[-1]], S)

    def test_small_birth_fraction_persists_and_requires_young_adults(self):
        no_adults = SourceVM()
        no_adults.initialize(0)
        no_adults.vars[BANDS[-1]] = 100 * S
        for _ in range(240):
            no_adults.call(P + "apply_births_effect")
        self.assertEqual(no_adults.vars[BANDS[0]], 0)
        self.assertEqual(no_adults.vars["aawc_reforging_birth_fraction"], 0)

        one_adult = SourceVM()
        one_adult.initialize(0)
        for dimension in ("sustenance", "habitation", "opportunity", "health", "security", "amenities"):
            one_adult.vars[f"aawc_stage2_effective_{dimension}"] = 50 * S
        one_adult.vars[BANDS[3]] = S
        for _ in range(90):
            one_adult.call(P + "apply_births_effect")
        self.assertEqual(one_adult.vars[BANDS[0]], 0)
        self.assertEqual(one_adult.vars["aawc_reforging_birth_fraction"], 99_000)
        one_adult.call(P + "apply_births_effect")
        self.assertEqual(one_adult.vars[BANDS[0]], S)
        self.assertEqual(one_adult.vars["aawc_reforging_birth_fraction"], 100)

    def test_mortality_is_age_specific_fractional_and_bounded(self):
        vm = SourceVM()
        vm.initialize(0)
        for dimension in ("sustenance", "habitation", "opportunity", "health", "security", "amenities"):
            vm.vars[f"aawc_stage2_effective_{dimension}"] = 50 * S
        for band in BANDS:
            vm.vars[band] = 1_000 * S
        monthly_rates = [
            vm.value(f"aawc_reforging_cohort_candidate_monthly_mortality_age_{band.split('age_', 1)[1]}")
            for band in BANDS
        ]
        self.assertEqual(monthly_rates, [rate * 1_000 // 12 for rate in ANNUAL])
        before = [vm.vars[band] for band in BANDS]
        vm.call(P + "apply_mortality_effect")
        losses = [old - vm.vars[band] for old, band in zip(before, BANDS)]
        self.assertEqual(sum(losses), vm.vars[P + "last_deaths"])
        self.assertTrue(all(0 <= vm.vars[band] <= old for old, band in zip(before, BANDS)))
        self.assertGreater(losses[-1], max(losses[3:8]))
        self.assertGreater(losses[0], losses[3])

    def test_duplicate_tick_is_complete_noop_and_accounting_reconciles(self):
        vm = SourceVM()
        vm.initialize(100)
        vm.tick(1)
        self.assertEqual(
            vm.vars[P + "last_after_total"],
            vm.vars[P + "last_before_total"] + vm.vars[P + "last_births"] - vm.vars[P + "last_deaths"],
        )
        before = dict(vm.vars)
        vm.tick(1)
        self.assertEqual(vm.vars, before)

    def test_stage2_conditions_live_rates_neutral_and_stage6_inert(self):
        vm = SourceVM()
        self.assertTrue(all(vm.value(name) == 50*S for name in STAGE2_CONDITION_INPUTS[:-1]))
        self.assertEqual(vm.value(STAGE2_CONDITION_INPUTS[-1]), 0)
        self.assertTrue(all(vm.value(name) == S for name in STAGE2_NEUTRAL_MULTIPLIERS))
        for suffix in ("15_19", "20_24", "25_29", "30_34", "35_39", "40_44", "45_49", "50_54", "55_59"):
            self.assertEqual(vm.value(f"aawc_reforging_military_building_eligibility_age_{suffix}"), 0)
        self.assertEqual(vm.value("aawc_reforging_military_building_training_monthly"), 0)
        vm.initialize(100)
        for tick in range(120):
            vm.tick(tick)
        self.assertEqual([vm.vars[name] for name in MILITARY], [0] * 9)

    def test_provisional_long_run_reference_is_deterministic_and_nonnegative(self):
        expected_totals = {10: 167, 25: 416, 50: 1_108, 100: 7_858, 150: 56_796}
        for years, expected_total in expected_totals.items():
            with self.subTest(years=years):
                ledger = reference(years * 12)
                self.assertEqual(sum(ledger.bands), expected_total)
                self.assertTrue(all(value >= 0 for value in ledger.bands))
                self.assertTrue(all(0 <= value < S for value in (
                    ledger.birth,
                    *ledger.mortality,
                    *ledger.aging,
                    *ledger.military_aging,
                )))


if __name__ == "__main__":
    unittest.main(verbosity=2)
