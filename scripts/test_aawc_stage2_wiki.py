"""Focused player-reference contract for Stage 2 living conditions."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
EVENTS = MOD / "events" / "aawc_population_events.txt"
LOC = MOD / "localization" / "english" / "aawc_population_l_english.yml"
VALUES = MOD / "common" / "script_values" / "aawc_stage2_condition_values.txt"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class Stage2Wiki(unittest.TestCase):
    def setUp(self) -> None:
        self.events = read(EVENTS)
        self.loc = read(LOC)
        self.values = read(VALUES)

    def test_living_conditions_are_reachable_from_information_contents(self):
        contents = self.events[
            self.events.index("aawc_population_event.0410 ="):
            self.events.index("aawc_population_event.0411 =")
        ]
        self.assertIn("name = aawc_population_event.0410.conditions", contents)
        self.assertIn("trigger_event = aawc_population_event.0423", contents)
        for event in ("0423", "0424", "0425"):
            self.assertIn(f"aawc_population_event.{event} =", self.events)
            self.assertRegex(self.loc, re.compile(rf"^ aawc_population_event\.{event}\.t:0 ", re.MULTILINE))
        for option in ("dimensions", "capacity", "disruption"):
            self.assertIn(f"aawc_population_event.0423.{option}", self.events)

    def test_wiki_covers_all_six_dimensions_and_structural_effective_distinction(self):
        page = re.search(
            r"^ aawc_population_event\.0424\.desc:0 \"(.*)$", self.loc, re.MULTILINE
        )
        self.assertIsNotNone(page)
        for label in ("Sustenance", "Habitation", "Opportunity", "Health", "Security", "Amenities"):
            self.assertIn(label, page.group(1))
        self.assertIn("Structural Conditions", page.group(1))
        self.assertIn("Effective Conditions", page.group(1))
        self.assertIn("Stage 1 age-band births and ordinary mortality", page.group(1))

    def test_wiki_describes_actual_contributor_categories_and_capacity_pressure(self):
        dimensions = re.search(
            r"^ aawc_population_event\.0424\.desc:0 \"(.*)$", self.loc, re.MULTILINE
        ).group(1)
        capacity = re.search(
            r"^ aawc_population_event\.0422\.desc:0 \"(.*)$", self.loc, re.MULTILINE
        ).group(1)
        for contributor in (
            "holding type", "main holding level", "county development", "terrain",
            "installed buildings", "regional blockers",
        ):
            self.assertIn(contributor, dimensions)
        self.assertIn("0.012 × Structural Habitation", capacity)
        self.assertIn("0.003 × Structural Sustenance", capacity)
        self.assertIn("Above 80% occupancy", capacity)
        self.assertIn("above 90%", capacity)
        self.assertIn("not a population target or a hard cap", capacity)

    def test_wiki_explains_environment_and_scoped_disruptions_from_live_accessors(self):
        page = re.search(
            r"^ aawc_population_event\.0425\.desc:0 \"(.*)$", self.loc, re.MULTILINE
        ).group(1)
        for topic in ("Terrain", "Buildings", "Realm at War", "County Plague", "County-wide raid or siege", "directly affected holding"):
            self.assertIn(topic, page)
        for value in (
            "Opportunity -4", "Security -5", "Health by 15 / 30 / 45",
            "Sustenance -3", "Security -12", "Sustenance -2", "Security -10",
            "Sustenance -7", "Health -5", "Security -20", "Sustenance -5", "Security -18",
        ):
            self.assertIn(value, page)
        for accessor in (
            "aawc_stage2_adjustment_realm_war_opportunity",
            "aawc_stage2_adjustment_plague_health",
            "aawc_stage2_adjustment_county_siege_security",
            "aawc_stage2_adjustment_direct_siege_security",
            "aawc_stage2_adjustment_county_raid_security",
            "aawc_stage2_adjustment_direct_raid_security",
        ):
            self.assertRegex(self.values, re.compile(rf"^{accessor}\s*=", re.MULTILINE))

    def test_wiki_replaces_obsolete_target_and_broken_help_references(self):
        growth_context = re.search(
            r"^  aawc_population_event\.0432\.desc:0 \"(.*)$", self.loc, re.MULTILINE
        ).group(1)
        for obsolete in (
            "AAWC_POPULATION_HELP_BUILDING_RATING",
            "AAWC_POPULATION_HELP_TERRAIN",
            "AAWC_POPULATION_HELP_PRESSURE",
            "AAWC_POPULATION_HELP_PLAGUE",
        ):
            self.assertNotIn(obsolete, growth_context)
        self.assertNotIn("Building Capacity Bonus comes from buildings", self.loc)
        self.assertIn("Stage 3 custom building catalogue is deliberately not part", self.loc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
