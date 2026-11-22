"""Focused validation for the authoritative Stage 5 identity-migration policy."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "catalogue" / "stage5" / "identity_migration_policy.json"
MASTER_PATH = ROOT / "docs" / "AGOT_Alternate_World_Compatch_Documentation_Master.md"


class Stage5IdentityMigrationPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.master = MASTER_PATH.read_text(encoding="utf-8-sig")

    def test_policy_is_authoritative_and_ownership_is_bounded(self):
        self.assertEqual(self.policy["status"], "authoritative_implementation_contract")
        self.assertEqual(self.policy["release_baseline"], "1.11.5.0")
        ownership = self.policy["ownership"]
        self.assertEqual(ownership["absolute_population"], "AAWC")
        self.assertEqual(ownership["culture_and_faith_marginals"], "CaFG")
        self.assertEqual(ownership["joint_age_culture_faith_ledger"], "forbidden")

    def test_missing_provenance_is_source_majority_per_independent_axis(self):
        provenance = self.policy["provenance"]
        self.assertTrue(provenance["axes_are_independent"])
        self.assertEqual(
            provenance["culture_missing_fallback"],
            "source_holding_majority_culture_at_reservation",
        )
        self.assertEqual(
            provenance["faith_missing_fallback"],
            "source_holding_majority_faith_at_reservation",
        )
        self.assertEqual(provenance["destination_identity_fallback"], "forbidden")
        self.assertEqual(
            provenance["majority_tie_break"],
            "factor_descending_then_stable_identity_key_ascending",
        )
        self.assertEqual(provenance["joint_cross_product_inference"], "forbidden")
        self.assertEqual(
            provenance["proportional_d4_fallback"],
            "superseded_and_forbidden_in_production",
        )

    def test_departure_is_deterministic_and_owner_identity_weighted(self):
        departure = self.policy["departure"]
        self.assertEqual(departure["selection"], "per_axis_weighted_largest_remainder")
        self.assertLess(departure["weights"]["owner_aligned"], 1)
        self.assertGreater(departure["weights"]["owner_misaligned"], 1)
        self.assertEqual(departure["weights"]["owner_or_owner_identity_unavailable"], 1)
        self.assertEqual(departure["tie_break"], "stable_identity_key_ascending")
        self.assertEqual(departure["fractional_residuals"], "persisted_per_source_and_axis")

    def test_destination_policy_has_peace_gate_and_ordered_war_exception(self):
        destination = self.policy["destination"]
        self.assertTrue(destination["adjacency_required"])
        self.assertEqual(
            destination["peacetime_rule"],
            "destination_has_positive_factor_for_packet_culture_or_packet_faith",
        )
        self.assertEqual(destination["peaceful_source_to_war_affected_destination"], "forbidden")
        self.assertEqual(
            destination["war_source_order"],
            [
                "safe_neighbor_sharing_culture_or_faith",
                "safe_neighbor_without_identity_match",
                "war_affected_neighbor_sharing_culture_or_faith",
                "war_affected_neighbor_without_identity_match",
            ],
        )
        self.assertEqual(
            destination["no_eligible_destination"],
            "no_op_without_budget_or_factor_mutation",
        )

    def test_reconciliation_conserves_both_marginals_and_fails_closed(self):
        reconciliation = self.policy["reconciliation"]
        for key in (
            "culture_debit_sum_equals_transfer",
            "culture_credit_sum_equals_transfer",
            "faith_debit_sum_equals_transfer",
            "faith_credit_sum_equals_transfer",
        ):
            self.assertTrue(reconciliation[key])
        self.assertEqual(
            reconciliation["known_identity_absent_at_source"],
            "fail_closed_before_absolute_debit",
        )
        self.assertEqual(
            reconciliation["identity_absent_at_destination"],
            "create_factor_then_normalize",
        )
        self.assertEqual(reconciliation["births_deaths_aging"], "ratio_neutral")
        self.assertIn("source_population-transfer", reconciliation["source_formula"])
        self.assertIn("destination_population+transfer", reconciliation["destination_formula"])

    def test_refresh_is_bounded(self):
        refresh = self.policy["refresh"]
        self.assertTrue(refresh["province_factor_mutations_are_batched"])
        self.assertEqual(refresh["county_culture_refreshes_per_batch"], 1)
        self.assertEqual(refresh["county_faith_refreshes_per_batch"], 1)
        self.assertEqual(refresh["full_world_scan"], "forbidden")

    def test_master_contains_the_complete_policy_and_test_matrix(self):
        required = (
            "Stage 5 identity-migration policy baseline - 1.11.5.0",
            "source holding's majority culture",
            "source holding's majority faith",
            "must never construct an age × culture × faith cross-product",
            "owner-aligned identity receives weight `0.5`",
            "owner-misaligned identity receives weight `2.0`",
            "Peacetime destination gate",
            "War-displacement exception",
            "Known identity absent at source",
            "No eligible destination",
            "Automated and live-CK3 acceptance matrix",
            "Save/reload idempotency",
            "Batch/performance bound",
        )
        for marker in required:
            self.assertIn(marker, self.master)


if __name__ == "__main__":
    unittest.main(verbosity=2)
