"""Focused Stage 4 new-holding funding and pending-settlement contracts.

The lifecycle fixtures are deterministic accounting evidence. Source checks
verify the CK3 adapters and suppression surfaces; they are not rendered-game
certification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
BANDS = 13


def definition(relative: str, name: str) -> str:
    text = (MOD / relative).read_text(encoding="utf-8-sig")
    text = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise AssertionError(f"missing definition {relative}:{name}")
    opening = text.find("{", match.start(), match.end())
    depth = 0
    for index in range(opening, len(text)):
        depth += text[index] == "{"
        depth -= text[index] == "}"
        if depth == 0:
            return text[opening + 1 : index]
    raise AssertionError(f"unclosed definition {relative}:{name}")


@dataclass
class Holding:
    bands: list[int]
    reserved: list[int] = field(default_factory=lambda: [0] * BANDS)


@dataclass
class Settlement:
    bands: list[int] = field(default_factory=lambda: [0] * BANDS)
    pending: bool = False
    reserve_active: bool = False
    packet: list[int] = field(default_factory=lambda: [0] * BANDS)

    @property
    def privileges(self) -> dict[str, bool]:
        enabled = not self.pending
        return {
            key: enabled
            for key in ("initialize", "growth", "tax", "levy", "workforce", "settlement")
        }


def reserve(source: Holding, destination: Settlement, cost: int) -> bool:
    remaining = cost
    packet = [0] * BANDS
    for index in range(BANDS):
        available = max(source.bands[index] - source.reserved[index], 0)
        packet[index] = min(available, remaining)
        remaining -= packet[index]
    if cost <= 0 or remaining:
        return False
    source.reserved[:] = packet
    destination.packet[:] = packet
    destination.reserve_active = True
    return True


def cancel(source: Holding, destination: Settlement) -> None:
    if not destination.reserve_active:
        return
    source.reserved[:] = [0] * BANDS
    destination.packet[:] = [0] * BANDS
    destination.reserve_active = False


def complete(source: Holding, destination: Settlement) -> bool:
    destination.pending = True
    destination.bands[:] = [0] * BANDS
    if not destination.reserve_active:
        return False
    if any(source.bands[i] < destination.packet[i] for i in range(BANDS)):
        cancel(source, destination)
        return False
    for index, amount in enumerate(destination.packet):
        source.bands[index] -= amount
        destination.bands[index] += amount
    cancel(source, destination)
    destination.pending = False
    return True


class LifecycleFixtures(unittest.TestCase):
    def test_sufficient_completion_debits_before_exact_credit(self):
        source = Holding([200] * BANDS)
        destination = Settlement(bands=[100] + [0] * 12)
        before = sum(source.bands)
        self.assertTrue(reserve(source, destination, 1500))
        self.assertEqual(sum(source.bands), before)
        self.assertTrue(complete(source, destination))
        self.assertEqual(before - sum(source.bands), 1500)
        self.assertEqual(sum(destination.bands), 1500)
        self.assertFalse(destination.pending)

    def test_insufficient_completion_is_persistent_zero_pending(self):
        source = Holding([10] * BANDS)
        destination = Settlement(bands=[100] + [0] * 12)
        self.assertFalse(reserve(source, destination, 1500))
        self.assertFalse(complete(source, destination))
        self.assertTrue(destination.pending)
        self.assertEqual(sum(destination.bands), 0)
        self.assertEqual(set(destination.privileges.values()), {False})

    def test_cancel_is_idempotent_and_retry_can_commit(self):
        source = Holding([200] * BANDS)
        destination = Settlement()
        before = tuple(source.bands)
        self.assertTrue(reserve(source, destination, 1500))
        cancel(source, destination)
        cancel(source, destination)
        self.assertEqual(tuple(source.bands), before)
        self.assertEqual(sum(source.reserved), 0)
        self.assertTrue(reserve(source, destination, 1500))
        self.assertTrue(complete(source, destination))

    def test_real_source_recovery_restores_normal_lifecycle(self):
        source = Holding([0] * BANDS)
        destination = Settlement()
        self.assertFalse(reserve(source, destination, 1500))
        self.assertFalse(complete(source, destination))
        source.bands[:] = [200] * BANDS
        self.assertTrue(reserve(source, destination, 1500))
        self.assertTrue(complete(source, destination))
        self.assertEqual(sum(destination.bands), 1500)
        self.assertEqual(set(destination.privileges.values()), {True})


class SourceContracts(unittest.TestCase):
    ON_ACTION = "common/on_action/aawc_population_holding_construction_on_actions.txt"
    CORE = "common/scripted_effects/aawc_stage4_cohort_reservation_effects.txt"
    PENDING = "common/scripted_effects/aawc_stage4_new_holding_effects.txt"

    def test_start_cancel_and_completion_use_exact_packet_lifecycle(self):
        start = definition(self.ON_ACTION, "aawc_population_on_new_holding_started")
        cancel_body = definition(self.ON_ACTION, "aawc_population_on_new_holding_cancelled")
        completion = definition(self.ON_ACTION, "aawc_population_on_new_holding_completed")
        self.assertEqual(start.count("aawc_stage4_expedition_reserve_effect ="), 1)
        self.assertEqual(cancel_body.count("aawc_stage4_expedition_release_effect ="), 1)
        self.assertLess(
            completion.index("aawc_stage4_enter_pending_settlement_effect ="),
            completion.index("aawc_stage4_expedition_commit_effect ="),
        )
        self.assertLess(
            completion.index("aawc_stage4_expedition_commit_effect ="),
            completion.index("aawc_stage4_finalize_funded_settlement_effect ="),
        )
        self.assertNotIn("aawc_population_consume_reserved_amount_effect =", completion)
        self.assertNotIn("aawc_reforging_cohort_initialize_production_ledger_effect =", completion)

    def test_commit_removes_pending_only_after_source_debit(self):
        commit_body = definition(self.CORE, "aawc_stage4_expedition_commit_effect")
        self.assertLess(
            commit_body.index("aawc_stage4_expedition_commit_source_effect ="),
            commit_body.index("remove_variable = aawc_stage4_pending_settlement"),
        )
        self.assertLess(
            commit_body.index("remove_variable = aawc_stage4_pending_settlement"),
            commit_body.index("aawc_reforging_cohort_apply_transfer_packet_effect ="),
        )

    def test_pending_entry_clears_ledgers_and_zeroes_workforce_inputs(self):
        enter = definition(self.PENDING, "aawc_stage4_enter_pending_settlement_effect")
        self.assertIn("aawc_reforging_cohort_clear_ineligible_settlement_effect =", enter)
        self.assertIn("aawc_reforging_cohort_sync_legacy_population_effect =", enter)
        for name in (
            "aawc_population_expected",
            "aawc_population_debug_building_capacity",
            "aawc_population_debug_growth_rating",
            "aawc_population_maa_max_contribution",
            "aawc_migration_holding_building_rating_eligible",
        ):
            self.assertRegex(enter, rf"name\s*=\s*{name}\s+value\s*=\s*0")

    def test_all_pending_suppression_surfaces_are_wired(self):
        trigger = definition(
            "common/scripted_triggers/aawc_population_triggers.txt",
            "aawc_population_valid_settlement_for_cohort_trigger",
        )
        privileges = definition(
            "common/scripted_triggers/aawc_population_triggers.txt",
            "aawc_stage4_settlement_privileges_available_trigger",
        )
        values = (MOD / "common/script_values/aawc_population_values.txt").read_text(encoding="utf-8-sig")
        modifier = (MOD / "common/modifiers/aawc_stage4_pending_settlement_modifiers.txt").read_text(encoding="utf-8-sig")
        cache = (MOD / "common/scripted_effects/zz_aawc_population_cache_effects.txt").read_text(encoding="utf-8-sig")
        population = (MOD / "common/scripted_effects/aawc_population_effects.txt").read_text(encoding="utf-8-sig")
        self.assertIn("aawc_stage4_settlement_privileges_available_trigger = yes", trigger)
        self.assertIn("NOT = { has_variable = aawc_stage4_pending_settlement }", privileges)
        self.assertIn("aawc_stage4_pending_workforce_available", values)
        self.assertIn("aawc_population_holding_income_component", values)
        self.assertIn("aawc_population_holding_levy_component", values)
        self.assertIn("has_variable = aawc_stage4_pending_settlement", cache)
        self.assertIn("has_variable = aawc_stage4_pending_settlement", population)
        for native in ("tax_mult = -1", "levy_size = -1", "levy_reinforcement_rate = -1"):
            self.assertIn(native, modifier)

    def test_recovery_requires_exact_reserve_commit_and_zero_delta(self):
        recovery = definition(self.PENDING, "aawc_stage4_recover_pending_settlement_effect")
        monthly = definition(
            "common/scripted_effects/aawc_population_effects.txt",
            "aawc_population_apply_monthly_growth_character_effect",
        )
        self.assertLess(
            recovery.index("aawc_stage4_expedition_reserve_effect ="),
            recovery.index("aawc_stage4_expedition_commit_effect ="),
        )
        self.assertLess(
            recovery.index("aawc_stage4_expedition_commit_effect ="),
            recovery.index("aawc_stage4_finalize_funded_settlement_effect ="),
        )
        self.assertIn("aawc_stage4_receipt_delta = 0", recovery)
        self.assertIn("aawc_stage4_recover_pending_settlements_character_effect =", monthly)

    def test_changed_scripts_have_balanced_braces(self):
        paths = (
            self.ON_ACTION,
            self.CORE,
            self.PENDING,
            "common/scripted_triggers/aawc_population_triggers.txt",
            "common/script_values/aawc_population_values.txt",
            "common/scripted_effects/aawc_population_effects.txt",
            "common/scripted_effects/zz_aawc_population_cache_effects.txt",
            "common/modifiers/aawc_stage4_pending_settlement_modifiers.txt",
        )
        for relative in paths:
            text = (MOD / relative).read_text(encoding="utf-8-sig")
            stripped = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
            self.assertEqual(stripped.count("{"), stripped.count("}"), relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
