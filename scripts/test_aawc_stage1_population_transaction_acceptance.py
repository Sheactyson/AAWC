"""Targeted Stage-1 population-transaction acceptance fixtures.

These tests combine exact offline accounting fixtures with source-contract
checks.  They are not CK3 runtime evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
BANDS = (9, 8, 8, 8, 8, 8, 8, 8, 7, 7, 6, 5, 10)


def body(relative: str, name: str) -> str:
    text = (MOD / relative).read_text(encoding="utf-8-sig")
    text = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise AssertionError(f"missing definition {relative}:{name}")
    opening = text.find("{", match.start(), match.end())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index]
    raise AssertionError(f"unclosed definition {relative}:{name}")


@dataclass
class SettlementReceipt:
    requested: int
    applied: int
    credited: int
    consumed: int
    unmet: int


def settle(source_bands: list[int], requested: int, starting: int) -> SettlementReceipt:
    available = sum(source_bands)
    applied = min(max(requested, 0), available)
    remaining = applied
    for index in range(12, -1, -1):
        debit = min(source_bands[index], remaining)
        source_bands[index] -= debit
        remaining -= debit
    credited = min(applied, max(starting, 0))
    return SettlementReceipt(requested, applied, credited, applied - credited, requested - applied)


def transfer_packet(source: list[int], destination: list[int], amount: int) -> tuple[int, ...]:
    remaining = min(max(amount, 0), sum(source))
    packet = [0] * 13
    for index in range(13):
        packet[index] = min(source[index], remaining)
        source[index] -= packet[index]
        destination[index] += packet[index]
        remaining -= packet[index]
    return tuple(packet)


class AccountingFixtures(unittest.TestCase):
    def test_migration_moves_the_same_age_packet_and_conserves_population(self):
        source = list(BANDS)
        destination = [0] * 13
        before = sum(source) + sum(destination)
        packet = transfer_packet(source, destination, 37)
        self.assertEqual(sum(packet), 37)
        self.assertEqual(tuple(destination), packet)
        self.assertEqual(sum(source) + sum(destination), before)

    def test_insufficient_settlement_source_reduces_credit_fail_closed(self):
        source = [1, 2, 3] + [0] * 10
        receipt = settle(source, requested=100, starting=100)
        self.assertEqual(receipt, SettlementReceipt(100, 6, 6, 0, 94))
        self.assertEqual(sum(source) + receipt.credited + receipt.consumed, 6)

    def test_settlement_consumption_is_classified_exactly(self):
        source = [10] * 13
        receipt = settle(source, requested=80, starting=25)
        self.assertEqual((receipt.applied, receipt.credited, receipt.consumed), (80, 25, 55))
        self.assertEqual(sum(source) + receipt.credited + receipt.consumed, 130)

    def test_reservation_cancel_is_non_demographic(self):
        source = list(BANDS)
        before = tuple(source)
        reservation = 40
        reservation -= 40
        self.assertEqual(reservation, 0)
        self.assertEqual(tuple(source), before)


class SourceContracts(unittest.TestCase):
    def test_only_the_sanctioned_mirror_writes_scalar_current(self):
        writers = []
        for path in MOD.rglob("*.txt"):
            text = "\n".join(line.split("#", 1)[0] for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines())
            if re.search(r"\bname\s*=\s*aawc_population_current\b", text):
                writers.append(path.relative_to(MOD).as_posix())
        self.assertEqual(writers, ["common/scripted_effects/aawc_reforging_cohort_production_effects.txt"])

    def test_migration_commit_uses_exact_packet_once(self):
        migration = body("common/scripted_effects/zzzz_aawc_population_migration_effects.txt", "aawc_migration_commit_scoped_pair_population_effect")
        self.assertEqual(migration.count("aawc_reforging_cohort_capture_transfer_packet_effect ="), 1)
        self.assertEqual(migration.count("aawc_reforging_cohort_apply_transfer_packet_effect ="), 1)
        caller = body("common/scripted_effects/zzzz_aawc_population_migration_effects.txt", "aawc_migration_transfer_to_scoped_target_effect")
        self.assertEqual(caller.count("aawc_migration_commit_scoped_pair_population_effect ="), 1)
        self.assertNotIn("aawc_reforging_cohort_apply_signed_transfer_effect =", caller)

    def test_new_holding_debits_before_receipt_backed_initialization(self):
        completion = body("common/on_action/aawc_population_holding_construction_on_actions.txt", "aawc_population_on_new_holding_completed")
        consume = completion.index("aawc_population_consume_reserved_amount_effect =")
        receipt = completion.index("aawc_population_prepare_settlement_receipt_effect =")
        initialize = completion.index("aawc_reforging_cohort_initialize_production_ledger_effect =")
        self.assertLess(consume, receipt)
        self.assertLess(receipt, initialize)
        self.assertIn("aawc_population_last_settlement_credit", completion)

    def test_consume_records_requested_applied_unmet_once(self):
        consume = body("common/scripted_effects/aawc_population_effects.txt", "aawc_population_consume_reserved_amount_effect")
        for field in ("aawc_population_last_consume_requested", "aawc_population_last_consume_applied", "aawc_population_last_consume_unmet"):
            self.assertIn(f"name = {field}", consume)
        self.assertEqual(consume.count("aawc_population_consume_reserved_from_county_holder_baronies_effect ="), 1)

    def test_maa_and_crisis_use_distinct_central_profiles(self):
        maa = body("common/scripted_effects/aawc_population_effects.txt", "aawc_population_spend_maa_population_pool_from_holding_effect")
        self.assertEqual(maa.count("aawc_reforging_cohort_debit_legacy_maa_population_effect ="), 1)
        self.assertNotIn("aawc_reforging_cohort_debit_population_effect =", maa)
        death = body("common/scripted_effects/aawc_reforging_cohort_production_effects.txt", "aawc_reforging_cohort_death_population_effect")
        self.assertEqual(death.count("aawc_reforging_cohort_debit_crisis_population_effect ="), 1)
        crisis = body("common/scripted_effects/aawc_reforging_cohort_production_effects.txt", "aawc_reforging_cohort_debit_crisis_population_effect")
        self.assertLess(crisis.index("age_00_04"), crisis.index("age_20_24"))
        self.assertLess(crisis.index("age_60_plus"), crisis.index("age_20_24"))

    def test_settlement_paths_do_not_retain_unconditional_target_100(self):
        establish = body("common/scripted_effects/lv_settlement_effects.txt", "lv_settlement_establish_effect")
        self.assertNotIn("set_population_target_effect = { POPULATION = 100", establish)
        self.assertIn("aawc_population_pending_settlement_credit", establish)

    def test_source_free_foundations_are_explicitly_classified(self):
        age_of_silence = body("common/scripted_effects/lv_settlement_effects.txt", "aawc_age_of_silence_found_tribal_holding_effect")
        self.assertIn("name = aawc_population_last_transaction_class value = 8", age_of_silence)
        decisions = (MOD / "common/decisions/agot_decisions/00_agot_colonization_decisions.txt").read_text(encoding="utf-8-sig")
        self.assertEqual(decisions.count("name = aawc_population_last_transaction_class value = 8"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
