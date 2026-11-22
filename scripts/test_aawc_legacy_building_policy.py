from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_aawc_legacy_building_policy as policy_gen


ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads(policy_gen.POLICY.read_text(encoding="utf-8"))
INVENTORY = json.loads(policy_gen.ORDINARY_INVENTORY.read_text(encoding="utf-8"))
CATALOGUE = json.loads(policy_gen.CATALOGUE.read_text(encoding="utf-8"))
CONSTRUCTION = json.loads(policy_gen.CONSTRUCTION.read_text(encoding="utf-8"))
STAGE3 = policy_gen.all_definitions(
    (policy_gen.MOD / "common/buildings/zz_aawc_stage3_catalogue.txt").read_text(encoding="utf-8-sig")
)
OVERRIDE = policy_gen.all_definitions(policy_gen.SPECIAL_OVERRIDE.read_text(encoding="utf-8-sig"))


def field(body: str, key: str) -> str:
    span = policy_gen.extract_value_span(body, key)
    if not span:
        return ""
    return re.sub(r"\s+", " ", body[span[0] : span[1]]).strip()


class LegacyBuildingPolicy(unittest.TestCase):
    def test_policy_and_inventory_contracts_are_complete(self):
        self.assertEqual(POLICY["schema_version"], 1)
        self.assertEqual(POLICY["policy"], "compatibility_safe_legacy_suppression_v1")
        self.assertEqual(INVENTORY["policy"], "pre_suppression_ordinary_roots_v1")
        mapped = {row["legacy_root"] for row in POLICY["ordinary_routes"]["mapped"]}
        excepted = {row["legacy_root"] for row in POLICY["ordinary_routes"]["no_replacement"]}
        inventoried = {
            root for roots in INVENTORY["roots_by_holding"].values() for root in roots
        }
        self.assertEqual(mapped | excepted, inventoried)
        self.assertFalse(mapped & excepted)
        self.assertEqual(len(mapped), 88)
        self.assertEqual(len(excepted), 3)

    def test_ordinary_holdings_expose_only_aawc_or_lifecycle_roots(self):
        retained = POLICY["ordinary_routes"]["retained_roots_by_holding"]
        for path in policy_gen.HOLDING_FILES:
            text = path.read_text(encoding="utf-8-sig")
            for holding, (roots, *_rest) in policy_gen.holding_blocks(text).items():
                self.assertEqual(roots, retained[holding], holding)
                if holding in policy_gen.FULL_ROOT_RETENTION:
                    continue
                allowed = {
                    root
                    for root in roots
                    if root.startswith("aawc_")
                    or (holding == "settlement_holding" and root in policy_gen.SETTLEMENT_LIFECYCLE_ROOTS)
                }
                self.assertEqual(set(roots), allowed, holding)
                self.assertFalse(
                    set(roots) & set(INVENTORY["roots_by_holding"].get(holding, [])), holding
                )

    def test_main_and_ruin_exceptions_remain_available(self):
        all_holding_text = "\n".join(
            path.read_text(encoding="utf-8-sig") for path in policy_gen.HOLDING_FILES
        )
        holding_defs = policy_gen.all_definitions(all_holding_text)
        primaries = {}
        for holding in policy_gen.MAIN_HOLDINGS & holding_defs.keys():
            match = re.search(
                r"(?m)^\s*primary_building\s*=\s*([A-Za-z0-9_]+)", holding_defs[holding]
            )
            self.assertIsNotNone(match, holding)
            primaries[holding] = match.group(1)
        self.assertEqual(primaries["castle_holding"], "castle_01")
        self.assertEqual(primaries["city_holding"], "city_01")
        self.assertEqual(primaries["church_holding"], "temple_01")
        self.assertEqual(primaries["tribal_holding"], "tribe_01")
        self.assertEqual(primaries["ruin_holding"], "ruin_01")
        suppressed = set(OVERRIDE)
        self.assertFalse(set(primaries.values()) & suppressed)
        ruin_roots = set(policy_gen.holding_blocks(
            next(
                path.read_text(encoding="utf-8-sig")
                for path in policy_gen.HOLDING_FILES
                if "ruin_holding" in path.read_text(encoding="utf-8-sig")
            )
        )["ruin_holding"][0])
        self.assertTrue({"small_ruin_01", "medium_ruin_01", "large_ruin_01"} <= ruin_roots)

    def test_every_ordinary_mapping_is_reachable(self):
        chain_kind = {chain["id"]: chain["kind"] for chain in CATALOGUE["chains"]}
        level_chain = {
            level["id"]: chain["id"]
            for chain in CATALOGUE["chains"]
            for level in chain["levels"]
        }
        holding_roots = {}
        for path in policy_gen.HOLDING_FILES:
            holding_roots.update(
                {
                    holding: set(row[0])
                    for holding, row in policy_gen.holding_blocks(
                        path.read_text(encoding="utf-8-sig")
                    ).items()
                }
            )
        for row in POLICY["ordinary_routes"]["mapped"]:
            target = row["replacement_root"]
            self.assertIn(target, STAGE3, row["legacy_root"])
            chain = level_chain[target]
            if chain_kind[chain] == "regular":
                for holding in row["holding_types"]:
                    self.assertIn(target, holding_roots[holding], (row["legacy_root"], holding))
            else:
                self.assertRegex(STAGE3[target], r"(?m)^\s*type\s*=\s*duchy_capital\s*$")
                for holding in row["holding_types"]:
                    self.assertNotIn(target, holding_roots[holding])

    def test_complete_tier_unlock_mapping_matches_construction_authority(self):
        expected = {
            level["legacy_id"]: level["id"]
            for chain in CATALOGUE["chains"]
            for level in chain["levels"]
            if level["legacy_id"]
        }
        routes = {
            row["legacy_id"]: row for row in POLICY["unlock_routes"]["catalogue_tiers"]
        }
        self.assertEqual({key: row["replacement_id"] for key, row in routes.items()}, expected)
        self.assertEqual(len(routes), 624)
        self.assertEqual(POLICY["unlock_routes"]["replacement_count"], 618)
        self.assertEqual(POLICY["unlock_routes"]["retained_main_line_count"], 6)
        self.assertEqual(
            {
                row["legacy_id"]
                for row in routes.values()
                if row["disposition"] == "retained_main_line_with_aawc_annex"
            },
            {"tribe_01", "tribe_02", "temple_citadel_01", "temple_citadel_02", "temple_citadel_03", "temple_citadel_04"},
        )
        contract_levels = {
            bid: level
            for chain in CONSTRUCTION["chains"].values()
            for bid, level in chain["levels"].items()
        }
        for legacy, row in routes.items():
            gates = "\n".join(contract_levels[row["replacement_id"]]["gates"].values())
            digest = hashlib.sha256(re.sub(r"\s+", " ", gates).strip().encode()).hexdigest()
            self.assertEqual(row["gate_contract_sha256"], digest, legacy)
            self.assertEqual(row["gate_categories"], policy_gen.gate_categories(gates), legacy)

    def test_special_and_duchy_suppression_preserves_payload(self):
        mapped = {row["legacy_id"]: row for row in POLICY["special_routes"]["mapped"]}
        excepted = {
            row["legacy_id"]: row for row in POLICY["special_routes"]["no_replacement"]
        }
        self.assertEqual(set(OVERRIDE), set(mapped) | set(excepted))
        self.assertFalse(set(mapped) & set(excepted))
        self.assertEqual(len(mapped), 74)
        self.assertEqual(len(excepted), 561)
        for bid, body in OVERRIDE.items():
            self.assertEqual(field(body, "show_disabled"), "show_disabled = no", bid)
            self.assertEqual(
                field(body, "can_construct_potential"),
                "can_construct_potential = { always = no }",
                bid,
            )
            self.assertEqual(field(body, "can_construct"), "can_construct = { always = no }", bid)
            self.assertEqual(field(body, "ai_value"), "ai_value = { base = 0 }", bid)
            digest = hashlib.sha256(policy_gen.remove_fields(body).encode()).hexdigest()
            self.assertEqual((mapped.get(bid) or excepted[bid])["preserved_payload_sha256"], digest, bid)

    def test_retained_specials_and_aawc_chains_are_not_suppressed(self):
        retained = set(POLICY["special_routes"]["retained_ids"])
        self.assertFalse(retained & set(OVERRIDE))
        self.assertTrue({bid for bid in STAGE3 if bid.startswith("aawc_")} <= retained | {
            bid for bid, body in STAGE3.items() if not re.search(r"(?m)^\s*type\s*=", body)
        })
        for bid in ("aawc_duchy_grand_harbor_01", "aawc_duchy_military_college_01"):
            self.assertIn(bid, retained)
            self.assertNotIn(bid, OVERRIDE)

    def test_skill_and_dynasty_gates_are_classified_without_invention(self):
        self.assertEqual(POLICY["gate_audit"]["direct_character_skill_gate_count"], 0)
        self.assertEqual(POLICY["gate_audit"]["direct_character_skill_legacy_ids"], [])
        exceptions = {
            row["legacy_id"]: row for row in POLICY["special_routes"]["no_replacement"]
        }
        self.assertIn("legendary_watchtower", exceptions)
        self.assertIn("dynasty_legacy", exceptions["legendary_watchtower"]["gate_categories"])
        self.assertNotIn("character_skill_or_lifestyle", exceptions["legendary_watchtower"]["gate_categories"])

    def test_changed_runtime_files_have_balanced_braces(self):
        for path in (*policy_gen.HOLDING_FILES, policy_gen.SPECIAL_OVERRIDE):
            text = path.read_text(encoding="utf-8-sig")
            stripped = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
            self.assertEqual(stripped.count("{"), stripped.count("}"), path.name)


if __name__ == "__main__":
    unittest.main()
