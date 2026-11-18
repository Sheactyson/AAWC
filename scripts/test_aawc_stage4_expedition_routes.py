"""Focused Stage 4 expedition-route adoption contracts.

These tests prove that each production route brackets the native handoff with
the shared cohort transaction API. They complement the executable accounting
fixtures in test_aawc_stage4_cohort_reservation.py.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"

ON_ACTION = "common/on_action/LV/ruin_restoration_on_actions/lv_settlement_on_actions.txt"
GUI = "common/scripted_guis/zz_agot_ruins_override.txt"
AI = "common/scripted_effects/aawc_population_ai_effects.txt"
AGOT_EVENTS = "events/agot_events/agot_colonization_events.txt"
CORE = "common/scripted_effects/aawc_stage4_cohort_reservation_effects.txt"


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


class ExpeditionRouteContracts(unittest.TestCase):
    def test_player_travel_success_uses_reserve_then_native_handoff_then_commit(self):
        start = definition(ON_ACTION, "lv_settlement_on_start")
        arrival = definition(ON_ACTION, "lv_settlement_on_arrival")
        self.assertIn("aawc_stage4_expedition_reserve_effect =", start)
        self.assertLess(
            arrival.index("lv_settlement_establish_effect ="),
            arrival.index("aawc_stage4_expedition_commit_effect ="),
        )
        self.assertIn("var:aawc_stage4_receipt_delta = 0", arrival)

    def test_player_travel_failure_routes_only_use_idempotent_failure_api(self):
        arrival = definition(ON_ACTION, "lv_settlement_on_arrival")
        cancel = definition(ON_ACTION, "lv_settlement_on_cancel")
        self.assertGreaterEqual(arrival.count("aawc_stage4_expedition_fail_effect ="), 4)
        self.assertEqual(cancel.count("aawc_stage4_expedition_release_effect ="), 1)
        for legacy in (
            "aawc_population_consume_reserved_amount_effect =",
            "aawc_population_prepare_settlement_receipt_effect =",
        ):
            self.assertNotIn(legacy, arrival)
            self.assertNotIn(legacy, cancel)

    def test_direct_reclaim_success_exposes_exact_committed_receipt(self):
        body = definition(GUI, "reconstruct_ruin")
        direct = body[body.index("AAWC DEBUG reconstruct_ruin AGOT direct-claim branch") : body.index("AAWC DEBUG reconstruct_ruin LoV expedition branch")]
        self.assertLess(direct.index("aawc_stage4_expedition_reserve_effect ="), direct.index("get_title ="))
        self.assertLess(direct.index("get_title ="), direct.index("aawc_stage4_expedition_commit_effect ="))
        self.assertIn("scope:actor.var:aawc_stage4_tx_state = 1", direct)
        self.assertIn("var:aawc_stage4_tx_state = 2 var:aawc_stage4_receipt_delta = 0", direct)

    def test_direct_wilderness_success_exposes_exact_committed_receipt(self):
        body = definition(GUI, "agot_can_colonize")
        direct = body[body.index("aawc_stage4_expedition_reserve_effect =") : body.index("AAWC DEBUG agot_can_colonize LoV expedition branch")]
        self.assertLess(direct.index("aawc_stage4_expedition_reserve_effect ="), direct.index("ai_colonization_effect ="))
        self.assertLess(direct.index("ai_colonization_effect ="), direct.index("aawc_stage4_expedition_commit_effect ="))
        self.assertIn("var:aawc_stage4_tx_state = 2 var:aawc_stage4_receipt_delta = 0", direct)

    def test_direct_failure_paths_have_no_legacy_debit_or_synthetic_credit(self):
        reclaim = definition(GUI, "reconstruct_ruin")
        reclaim = reclaim[reclaim.index("AAWC DEBUG reconstruct_ruin AGOT direct-claim branch") : reclaim.index("AAWC DEBUG reconstruct_ruin LoV expedition branch")]
        wilderness = definition(GUI, "agot_can_colonize")
        wilderness = wilderness[wilderness.index("aawc_stage4_expedition_reserve_effect =") : wilderness.index("AAWC DEBUG agot_can_colonize LoV expedition branch")]
        for route in (reclaim, wilderness):
            self.assertIn("var:aawc_stage4_tx_state = 1", route)
            self.assertIn("without debit or credit", route)
            for forbidden in (
                "aawc_population_add_reserved_amount_effect =",
                "aawc_population_consume_reserved_amount_effect =",
                "aawc_population_prepare_settlement_receipt_effect =",
                "aawc_reforging_cohort_initialize_production_ledger_effect =",
                "aawc_population_pending_settlement_credit",
            ):
                self.assertNotIn(forbidden, route)

    def test_instant_ai_success_uses_shared_api_and_exact_receipt(self):
        body = definition(AI, "aawc_population_ai_colonize_selected_external_target_effect")
        self.assertLess(body.index("aawc_stage4_expedition_reserve_effect ="), body.index("lv_settlement_establish_effect ="))
        self.assertLess(body.index("lv_settlement_establish_effect ="), body.index("aawc_stage4_expedition_commit_effect ="))
        self.assertIn("var:aawc_stage4_tx_state = 2 var:aawc_stage4_receipt_delta = 0", body)
        self.assertNotIn("aawc_population_consume_reserved_amount_effect =", body)
        self.assertNotIn("aawc_population_prepare_settlement_receipt_effect =", body)

    def test_instant_ai_failure_does_not_mark_action_taken_or_synthesize_residents(self):
        body = definition(AI, "aawc_population_ai_colonize_selected_external_target_effect")
        success = body.index("var:aawc_stage4_tx_state = 2 var:aawc_stage4_receipt_delta = 0")
        action = body.index("name = aawc_ai_yearly_action_taken value = 1")
        self.assertLess(success, action)
        self.assertIn("without debit or credit", body)
        self.assertNotIn("aawc_population_pending_settlement_credit", body)
        self.assertNotIn("aawc_reforging_cohort_initialize_production_ledger_effect =", body)

    def test_dormant_native_ai_adapter_cannot_reintroduce_independent_debit(self):
        body = definition(AGOT_EVENTS, "agot_colonization_events.0006")
        self.assertIn("aawc_stage4_expedition_reserve_effect =", body)
        self.assertIn("aawc_stage4_expedition_commit_effect =", body)
        self.assertNotIn("aawc_population_consume_reserved_amount_effect =", body)
        self.assertNotIn("aawc_population_prepare_settlement_receipt_effect =", body)

    def test_core_validates_every_source_and_destination_before_debit_or_credit(self):
        body = definition(CORE, "aawc_stage4_expedition_commit_effect")
        self.assertLess(body.index("aawc_stage4_expedition_validate_source_effect ="), body.index("aawc_stage4_expedition_commit_source_effect ="))
        self.assertLess(body.index("aawc_stage4_tx_valid = 1"), body.index("aawc_reforging_cohort_apply_transfer_packet_effect ="))
        self.assertIn("aawc_stage4_expedition_release_effect =", body)

    def test_changed_route_files_have_balanced_braces(self):
        for relative in (ON_ACTION, GUI, AI, AGOT_EVENTS, CORE):
            text = (MOD / relative).read_text(encoding="utf-8-sig")
            stripped = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
            self.assertEqual(stripped.count("{"), stripped.count("}"), relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
