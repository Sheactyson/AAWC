"""Focused source contract for Stage 2 environmental and disruption inputs."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
EFFECTS = MOD / "common" / "scripted_effects" / "aawc_stage2_condition_effects.txt"
VALUES = MOD / "common" / "script_values" / "aawc_stage2_condition_values.txt"
WARFARE = MOD / "common" / "on_action" / "aawc_population_warfare_on_actions.txt"
LOC = MOD / "localization" / "english" / "aawc_population_l_english.yml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class Stage2DisruptionConditions(unittest.TestCase):
    def test_realm_war_is_mild_and_purpose_specific(self):
        effects = read(EFFECTS)
        self.assertIn("county.holder ?= { is_at_war = yes }", effects)
        war = effects[effects.index("# A distant realm war"):effects.index("# County disruption")]
        self.assertIn("aawc_stage2_effective_opportunity add = -4", war)
        self.assertIn("aawc_stage2_effective_security add = -5", war)
        for dimension in ("sustenance", "habitation", "health", "amenities"):
            self.assertNotIn(f"aawc_stage2_effective_{dimension}", war)

    def test_county_and_direct_raid_siege_paths_are_distinct(self):
        effects, values, warfare = read(EFFECTS), read(VALUES), read(WARFARE)
        for kind in ("raid", "siege"):
            county_marker = f"aawc_population_{kind}_growth_suppressed"
            direct_marker = f"aawc_population_direct_{kind}_disrupted"
            self.assertIn(county_marker, effects)
            self.assertIn(direct_marker, effects)
            self.assertIn(f"name = {direct_marker}", warfare)
            self.assertIn(f"remove_variable = {direct_marker}", warfare)
            for scope in ("county", "direct"):
                self.assertRegex(values, rf"aawc_stage2_adjustment_{scope}_{kind}_[a-z]+\s*=")
        self.assertIn("aawc_stage2_adjustment_direct_siege_health", values)
        self.assertIn("aawc_stage2_adjustment_direct_raid_opportunity", values)

    def test_direct_event_losses_remain_the_only_warfare_debit(self):
        effects, warfare = read(EFFECTS), read(WARFARE)
        self.assertNotIn("aawc_population_apply_warfare_population_loss_effect", effects)
        self.assertNotRegex(effects, r"(?:set|change)_variable\s*=\s*\{\s*name\s*=\s*aawc_(?:population_current|reforging_cohort_age_)")
        self.assertEqual(warfare.count("aawc_population_apply_warfare_population_loss_effect"), 3)
        self.assertIn("LOSS_FACTOR = 0.15", warfare)
        self.assertIn("LOSS_FACTOR = 0.30", warfare)
        self.assertIn("LOSS_FACTOR = 0.10", warfare)

    def test_terrain_plague_and_building_routes_are_retained(self):
        effects = read(EFFECTS)
        self.assertEqual(effects.count("limit = { agot_is_"), 21)
        self.assertIn("aawc_stage2_building_contributions_effect = yes", effects)
        self.assertIn("has_province_with_epidemic = { intensity = apocalyptic }", effects)
        self.assertIn("has_province_with_epidemic = { intensity >= major }", effects)
        self.assertIn("has_province_with_epidemic = { intensity = any }", effects)

    def test_player_facing_rows_and_nested_explanations_cover_every_input(self):
        loc = read(LOC)
        for key in (
            "AAWC_STAGE2_HELP_REALM_WAR",
            "AAWC_STAGE2_HELP_COUNTY_DISRUPTION",
            "AAWC_STAGE2_HELP_DIRECT_DISRUPTION",
            "AAWC_STAGE2_HELP_PLAGUE",
        ):
            self.assertIn(f"#tooltip:{key}", loc)
            self.assertRegex(loc, re.compile(rf"^ {key}:0 ", re.MULTILINE))
        for label in ("County siege", "Direct siege", "County raid", "Direct raid", "Realm at war", "County plague"):
            self.assertIn(label, loc)
        self.assertIn("Completion casualties remain a separate one-time warfare loss", loc)

    def test_no_stage3_catalogue_was_added(self):
        self.assertFalse(any("stage3" in path.name.lower() for path in MOD.rglob("*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
