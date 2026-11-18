"""Focused Stage 4 cohort-reservation accounting and source contracts.

The reference fixtures are deterministic offline evidence. Source assertions
prove that the CK3 adapter calls the same lifecycle in the required order;
they are not a substitute for rendered gameplay inspection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import importlib.util
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
EFFECTS_REL = "common/scripted_effects/aawc_stage4_cohort_reservation_effects.txt"
VALUES_REL = "common/script_values/aawc_stage4_cohort_reservation_values.txt"
ON_ACTION_REL = "common/on_action/LV/ruin_restoration_on_actions/lv_settlement_on_actions.txt"
PRODUCTION_REL = "common/scripted_effects/aawc_reforging_cohort_production_effects.txt"
ADULT = set(range(3, 12))
RESERVED_BANDS = (
    "age_00_04",
    "age_05_09",
    "age_10_14",
    "age_15_19",
    "age_20_24",
    "age_25_29",
    "age_30_34",
    "age_35_39",
    "age_40_44",
    "age_45_49",
    "age_50_54",
    "age_55_59",
    "age_60_plus",
)


def definition(relative: str, name: str) -> str:
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
class Holding:
    bands: list[int]
    military: list[int] = field(default_factory=lambda: [0] * 13)
    reservation: list[int] = field(default_factory=lambda: [0] * 13)
    token_id: int | None = None


@dataclass
class Sponsor:
    reserved: int = 0


@dataclass
class Destination:
    bands: list[int] = field(default_factory=lambda: [0] * 13)
    native_handoff_complete: bool = True
    occupied_or_dummy: bool = False


@dataclass
class Token:
    token_id: int
    state: int = 0
    requested: int = 0
    packets: list[tuple[Holding, tuple[int, ...]]] = field(default_factory=list)
    debited: int = 0
    credited: int = 0
    attrition: int = 0
    delta: int = 0


def plan(token: Token, amount: int) -> None:
    token.requested = max(amount, 0)
    token.state = 0


def release(token: Token, sponsor: Sponsor) -> None:
    if token.state not in (1, 4):
        return
    was_reserved = token.state == 1
    for holding, _ in token.packets:
        if holding.token_id == token.token_id:
            holding.reservation[:] = [0] * 13
            holding.token_id = None
    if was_reserved:
        sponsor.reserved -= token.requested
    token.state = 3


def reserve(token: Token, sponsor: Sponsor, holdings: list[Holding], amount: int) -> bool:
    if token.state == 1:
        return True
    token.state = 4
    token.requested = max(amount, 0)
    token.packets.clear()
    remaining = token.requested
    for holding in holdings:
        if remaining <= 0:
            break
        if holding.token_id is not None:
            continue
        packet = [0] * 13
        for band in range(13):
            available = holding.bands[band] - holding.reservation[band]
            if band in ADULT:
                available -= holding.military[band]
            packet[band] = min(max(available, 0), remaining)
            remaining -= packet[band]
        if any(packet):
            holding.reservation[:] = packet
            holding.token_id = token.token_id
            token.packets.append((holding, tuple(packet)))
    if token.requested > 0 and remaining == 0:
        token.state = 1
        sponsor.reserved += token.requested
        return True
    release(token, sponsor)
    return False


def commit(token: Token, sponsor: Sponsor, destination: Destination, attrition: int) -> bool:
    valid = (
        token.state == 1
        and destination.native_handoff_complete
        and not destination.occupied_or_dummy
        and 0 <= attrition <= token.requested
        and sum(sum(packet) for _, packet in token.packets) == token.requested
    )
    if valid:
        for holding, packet in token.packets:
            if holding.token_id != token.token_id or any(
                holding.bands[i] < packet[i] for i in range(13)
            ):
                valid = False
                break
    if not valid:
        release(token, sponsor)
        return False

    pool = [0] * 13
    for holding, packet in token.packets:
        for band, amount in enumerate(packet):
            holding.bands[band] -= amount
            pool[band] += amount
        holding.reservation[:] = [0] * 13
        holding.token_id = None

    retained = token.requested - attrition
    for band in range(13):
        credit = min(pool[band], retained)
        destination.bands[band] += credit
        pool[band] -= credit
        retained -= credit

    token.debited = token.requested
    token.credited = sum(destination.bands)
    token.attrition = sum(pool)
    token.delta = token.debited - token.credited - token.attrition
    sponsor.reserved -= token.requested
    token.state = 2
    return True


class TransactionFixtures(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Holding([150] * 13)
        self.sponsor = Sponsor()
        self.token = Token(41)

    def test_pre_travel_cancellation_changes_no_population_or_reservation(self):
        before = tuple(self.source.bands)
        plan(self.token, 500)
        release(self.token, self.sponsor)
        self.assertEqual(tuple(self.source.bands), before)
        self.assertEqual(self.source.reservation, [0] * 13)
        self.assertEqual(self.sponsor.reserved, 0)

    def test_post_start_cancellation_releases_once(self):
        before = tuple(self.source.bands)
        self.assertTrue(reserve(self.token, self.sponsor, [self.source], 500))
        self.assertEqual(sum(self.source.reservation), 500)
        self.assertEqual(sum(self.source.bands), sum(before))
        release(self.token, self.sponsor)
        release(self.token, self.sponsor)
        self.assertEqual(tuple(self.source.bands), before)
        self.assertEqual(self.sponsor.reserved, 0)
        self.assertEqual(self.token.state, 3)

    def test_invalid_or_occupied_arrival_has_no_debit_credit_or_leak(self):
        before = tuple(self.source.bands)
        self.assertTrue(reserve(self.token, self.sponsor, [self.source], 500))
        destination = Destination(occupied_or_dummy=True)
        self.assertFalse(commit(self.token, self.sponsor, destination, attrition=400))
        self.assertEqual(tuple(self.source.bands), before)
        self.assertEqual(sum(destination.bands), 0)
        self.assertEqual(self.sponsor.reserved, 0)
        self.assertIsNone(self.source.token_id)

    def test_successful_wilderness_arrival_reconciles_exact_packet(self):
        self.assertTrue(reserve(self.token, self.sponsor, [self.source], 750))
        packet = tuple(self.source.reservation)
        destination = Destination()
        self.assertTrue(commit(self.token, self.sponsor, destination, attrition=650))
        self.assertEqual(self.token.debited, 750)
        self.assertEqual(self.token.credited, 100)
        self.assertEqual(self.token.attrition, 650)
        self.assertEqual(self.token.delta, 0)
        expected = [0] * 13
        remaining = 100
        for band, amount in enumerate(packet):
            expected[band] = min(amount, remaining)
            remaining -= expected[band]
        self.assertEqual(destination.bands, expected)
        self.assertEqual(sum(destination.bands), 100)

    def test_successful_ruin_arrival_spans_exact_source_holdings(self):
        first = Holding([40] * 13)
        second = Holding([60] * 13)
        before = sum(first.bands) + sum(second.bands)
        self.assertTrue(reserve(self.token, self.sponsor, [first, second], 900))
        self.assertEqual(len(self.token.packets), 2)
        destination = Destination()
        self.assertTrue(commit(self.token, self.sponsor, destination, attrition=800))
        self.assertEqual(before - sum(first.bands) - sum(second.bands), 900)
        self.assertEqual(sum(destination.bands), 100)
        self.assertEqual(self.token.delta, 0)

    def test_source_loss_before_arrival_fails_before_any_commit_mutation(self):
        self.assertTrue(reserve(self.token, self.sponsor, [self.source], 500))
        affected_band = next(i for i, value in enumerate(self.source.reservation) if value)
        self.source.bands[affected_band] = self.source.reservation[affected_band] - 1
        before = tuple(self.source.bands)
        destination = Destination()
        self.assertFalse(commit(self.token, self.sponsor, destination, attrition=400))
        self.assertEqual(tuple(self.source.bands), before)
        self.assertEqual(sum(destination.bands), 0)
        self.assertEqual(self.sponsor.reserved, 0)

    def test_military_subset_is_not_reserved(self):
        source = Holding([0, 0, 0] + [100] * 9 + [0], military=[0, 0, 0] + [90] * 9 + [0])
        self.assertTrue(reserve(self.token, self.sponsor, [source], 90))
        self.assertEqual(sum(source.reservation), 90)
        self.assertTrue(all(source.reservation[i] <= 10 for i in ADULT))

    def test_reserved_packet_stays_exact_across_unreserved_demography(self):
        self.assertTrue(reserve(self.token, self.sponsor, [self.source], 500))
        packet = tuple(self.source.reservation)
        unreserved = [self.source.bands[i] - packet[i] for i in range(13)]
        # A bounded stand-in for one synchronous tick: only the detached ledger
        # ages; the packet is reattached unchanged afterward.
        mover = min(unreserved[0], 2)
        unreserved[0] -= mover
        unreserved[1] += mover
        unreserved[12] = max(unreserved[12] - 1, 0)
        self.source.bands[:] = [unreserved[i] + packet[i] for i in range(13)]
        self.assertEqual(tuple(self.source.reservation), packet)
        self.assertTrue(all(self.source.bands[i] >= packet[i] for i in range(13)))


class SourceContracts(unittest.TestCase):
    def test_generated_outputs_match_generator(self):
        path = ROOT / "scripts" / "generate_aawc_stage4_transactions.py"
        spec = importlib.util.spec_from_file_location("stage4_generator", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual((MOD / EFFECTS_REL).read_text(encoding="utf-8-sig"), module.render_effects())
        self.assertEqual((MOD / VALUES_REL).read_text(encoding="utf-8-sig"), module.render_values())

    def test_planning_api_contains_no_population_or_reservation_mutation(self):
        planning = definition(EFFECTS_REL, "aawc_stage4_expedition_plan_effect")
        for forbidden in (
            "aawc_population_add_reserved_amount_effect",
            "aawc_reforging_cohort_debit",
            "aawc_stage4_reserved_age_",
        ):
            self.assertNotIn(forbidden, planning)
        reserve_body = definition(EFFECTS_REL, "aawc_stage4_expedition_reserve_effect")
        self.assertIn(
            "aawc_stage4_expedition_plan_effect = { AMOUNT = $AMOUNT$ DESTINATION = $DESTINATION$ }",
            reserve_body,
        )
        self.assertIn(
            "name = aawc_stage4_tx_requested value = var:aawc_stage4_tx_planned_cost",
            reserve_body,
        )
        self.assertIn(
            "name = aawc_stage4_tx_destination value = var:aawc_stage4_tx_planned_destination",
            reserve_body,
        )
        self.assertIn(
            "limit = { OR = { NOT = { has_variable = aawc_stage4_tx_state } NOT = { var:aawc_stage4_tx_state = 1 } } }",
            reserve_body,
        )
        self.assertNotIn(
            "limit = { NOT = { var:aawc_stage4_tx_state = 1 } }",
            reserve_body,
        )

    def test_reservation_source_concretely_registers_all_packet_variables(self):
        source = definition(EFFECTS_REL, "aawc_stage4_expedition_reserve_source_effect")
        first_helper = source.index("aawc_stage4_expedition_reserve_band_effect =")
        for band in RESERVED_BANDS:
            initializer = f"set_variable = {{ name = aawc_stage4_reserved_{band} value = 0 }}"
            self.assertIn(initializer, source)
            self.assertLess(source.index(initializer), first_helper)

    def test_release_and_commit_are_state_gated(self):
        release_body = definition(EFFECTS_REL, "aawc_stage4_expedition_release_effect")
        commit_body = definition(EFFECTS_REL, "aawc_stage4_expedition_commit_effect")
        self.assertIn("aawc_stage4_tx_state = 1", release_body)
        self.assertIn("aawc_stage4_tx_state = 4", release_body)
        self.assertEqual(release_body.count("aawc_population_release_reserved_amount_effect ="), 1)
        self.assertIn("limit = { var:aawc_stage4_tx_state = 1 }", commit_body)
        self.assertLess(
            commit_body.index("aawc_stage4_expedition_validate_source_effect ="),
            commit_body.index("aawc_stage4_expedition_commit_source_effect ="),
        )

    def test_native_handoff_precedes_commit_and_first_story_precedes_reserve(self):
        start = definition(ON_ACTION_REL, "lv_settlement_on_start")
        arrival = definition(ON_ACTION_REL, "lv_settlement_on_arrival")
        self.assertLess(start.index("add_to_variable_list"), start.index("aawc_stage4_expedition_reserve_effect ="))
        self.assertLess(arrival.index("lv_settlement_establish_effect ="), arrival.index("aawc_stage4_expedition_commit_effect ="))
        core = (MOD / EFFECTS_REL).read_text(encoding="utf-8-sig")
        for forbidden in ("change_title_holder", "get_title =", "create_title_and_vassal_change"):
            self.assertNotIn(forbidden, core)

    def test_cancel_and_invalid_arrival_share_idempotent_release(self):
        cancel = definition(ON_ACTION_REL, "lv_settlement_on_cancel")
        arrival = definition(ON_ACTION_REL, "lv_settlement_on_arrival")
        self.assertEqual(cancel.count("aawc_stage4_expedition_release_effect ="), 1)
        self.assertGreaterEqual(arrival.count("aawc_stage4_expedition_fail_effect ="), 4)
        self.assertNotIn("aawc_population_release_reserved_amount_effect =", cancel)
        self.assertNotIn("aawc_population_release_reserved_amount_effect =", arrival)

    def test_nonfatal_stage1_debits_exclude_reserved_bands(self):
        transfer = definition(PRODUCTION_REL, "aawc_reforging_cohort_capture_transfer_packet_effect")
        debit = definition(PRODUCTION_REL, "aawc_reforging_cohort_debit_population_effect")
        maa = definition(PRODUCTION_REL, "aawc_reforging_cohort_debit_legacy_maa_population_effect")
        self.assertEqual(transfer.count("RESERVED = aawc_stage4_reserved_age_"), 13)
        self.assertEqual(debit.count("aawc_reforging_cohort_drain_unreserved_band_effect ="), 13)
        self.assertEqual(maa.count("aawc_reforging_cohort_drain_unreserved_band_effect ="), 9)

    def test_monthly_authority_detaches_and_reattaches_exact_packet(self):
        production = definition(PRODUCTION_REL, "aawc_reforging_cohort_apply_production_month_effect")
        detach = definition(EFFECTS_REL, "aawc_stage4_expedition_detach_reserved_packet_effect")
        reattach = definition(EFFECTS_REL, "aawc_stage4_expedition_reattach_reserved_packet_effect")
        self.assertLess(
            production.index("aawc_stage4_expedition_detach_reserved_packet_effect ="),
            production.index("aawc_reforging_cohort_monthly_authority_effect ="),
        )
        self.assertLess(
            production.index("aawc_reforging_cohort_monthly_authority_effect ="),
            production.index("aawc_stage4_expedition_reattach_reserved_packet_effect ="),
        )
        self.assertEqual(detach.count("name = aawc_reforging_cohort_age_"), 13)
        self.assertEqual(reattach.count("name = aawc_reforging_cohort_age_"), 13)
        self.assertIn("aawc_stage4_reservation_detached", detach)
        self.assertIn("aawc_stage4_reservation_detached", reattach)

    def test_receipt_has_zero_delta_formula_and_per_band_attrition(self):
        values = (MOD / VALUES_REL).read_text(encoding="utf-8-sig")
        effects = (MOD / EFFECTS_REL).read_text(encoding="utf-8-sig")
        self.assertIn("aawc_stage4_receipt_reconciliation_delta", values)
        self.assertIn("aawc_stage4_receipt_delta value = aawc_stage4_receipt_reconciliation_delta", effects)
        self.assertEqual(effects.count("name = aawc_stage4_receipt_attrition_age_"), 13)

    def test_changed_script_files_have_balanced_braces(self):
        for relative in (EFFECTS_REL, VALUES_REL, ON_ACTION_REL, PRODUCTION_REL):
            text = (MOD / relative).read_text(encoding="utf-8-sig")
            stripped = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
            self.assertEqual(stripped.count("{"), stripped.count("}"), relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
