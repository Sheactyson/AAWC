"""Focused current-release Stage 2 Population UI contract checks."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
OUTER = ROOT / "mod" / "AGOT_Alternate_World_Compatch.mod"
GUI = MOD / "gui" / "window_county_view.gui"
VALYRIA_GUI = MOD / "gui_folder_valyria" / "window_county_view.gui"
LOC = MOD / "localization" / "english" / "aawc_population_l_english.yml"
BUILDING_LOC = MOD / "localization" / "english" / "aawc_stage2_building_contributions_l_english.yml"
BUILDING_CUSTOM_LOC = MOD / "common" / "customizable_localization" / "aawc_stage2_building_contributions_custom_loc.txt"
VALUES = MOD / "common" / "script_values" / "aawc_stage2_condition_values.txt"
EFFECTS = MOD / "common" / "scripted_effects" / "aawc_stage2_condition_effects.txt"
DIMENSIONS = ("sustenance", "habitation", "opportunity", "health", "security", "amenities")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class Stage2PopulationUI(unittest.TestCase):
    def test_all_six_effective_scores_are_bound_once_in_both_population_panels(self):
        for path in (GUI, VALYRIA_GUI):
            with self.subTest(gui=path.parent.name):
                gui = read(path)
                population = gui[gui.index("#### POPULATION ####"):gui.index("#### LEGENDS ####")]
                self.assertIn('name = "aawc_stage2_living_conditions"', population)
                panel = population[population.index('name = "aawc_stage2_living_conditions"'):]
                for dimension in DIMENSIONS:
                    accessor = f"aawc_stage2_effective_{dimension}_value"
                    self.assertEqual(panel.count(accessor), 1)
                    self.assertIn(f'AAWC_STAGE2_TT_{dimension.upper()}', panel)

    def test_tooltips_expose_breakdowns_and_nested_formula_help(self):
        loc = read(LOC)
        for dimension in DIMENSIONS:
            with self.subTest(dimension=dimension):
                self.assertIn(f"aawc_stage2_effective_{dimension}_value", loc)
                self.assertIn(f"aawc_stage2_structural_{dimension}_value", loc)
                self.assertIn(f"AAWC_STAGE2_HELP_{dimension.upper()}_FORMULA", loc)
                self.assertIn(f"aawc_stage2_contrib_holding_type_{dimension}", loc)
                self.assertIn(f"aawc_stage2_contrib_terrain_{dimension}", loc)
                self.assertIn(f"aawc_stage2_contrib_buildings_{dimension}", loc)
                self.assertIn(f"aawc_stage2_contrib_blockers_{dimension}", loc)
        self.assertIn("0–100; 50 is neutral", loc)
        for nested in (
            "AAWC_STAGE2_HELP_EFFECTIVE",
            "AAWC_STAGE2_HELP_STRUCTURAL",
            "AAWC_STAGE2_HELP_PHYSICAL_CAPACITY",
            "AAWC_STAGE2_HELP_CAPACITY_PRESSURE",
            "AAWC_STAGE2_HELP_BUILDINGS",
        ):
            self.assertIn(f"#tooltip:{nested}", loc)
            self.assertIsNotNone(re.search(rf"^ {nested}:0 ", loc, re.MULTILINE))

    def test_breakdown_accessors_share_the_authoritative_contribution_path(self):
        effects = read(EFFECTS)
        values = read(VALUES)
        for category in ("holding_type", "terrain", "buildings", "blockers"):
            marker_category = {"buildings": "building", "blockers": "blocker"}.get(category, category)
            marker = f"aawc_stage2_record_{marker_category}_contributions"
            self.assertIn(f"set_variable = {{ name = {marker} value = 1 }}", effects)
            self.assertIn(f"remove_variable = {marker}", effects)
            for dimension in DIMENSIONS:
                name = f"aawc_stage2_contrib_{category}_{dimension}"
                self.assertIn(f"change_variable = {{ name = {name} add = ${dimension.upper()}$ }}", effects)
                self.assertIsNotNone(re.search(rf"^{name}\s*=", values, re.MULTILINE))
        for accessor in (
            "aawc_stage2_adjustment_disruption_sustenance",
            "aawc_stage2_adjustment_disruption_security",
            "aawc_stage2_adjustment_control_security",
            "aawc_stage2_adjustment_plague_health",
            "aawc_stage2_adjustment_realm_war_opportunity",
            "aawc_stage2_adjustment_realm_war_security",
            "aawc_stage2_adjustment_county_siege_security",
            "aawc_stage2_adjustment_direct_siege_security",
            "aawc_stage2_adjustment_county_raid_security",
            "aawc_stage2_adjustment_direct_raid_security",
        ):
            self.assertIsNotNone(re.search(rf"^{accessor}\s*=", values, re.MULTILINE))

    def test_generated_building_drilldown_covers_every_reviewed_level(self):
        generated_loc = read(BUILDING_LOC)
        custom_loc = read(BUILDING_CUSTOM_LOC)
        calls = re.findall(r"AAWC_Stage2Building_([A-Za-z0-9_]+)", custom_loc)
        definitions = re.findall(r"^AAWC_Stage2Building_([A-Za-z0-9_]+) =", custom_loc, re.MULTILINE)
        entries = [
            entry for entry in re.findall(
                r"^ aawc_stage2_building_([A-Za-z0-9_]+):0 ", generated_loc, re.MULTILINE
            ) if entry != "empty"
        ]
        self.assertEqual(len(definitions), 771)
        self.assertEqual(len(entries), 771)
        self.assertEqual(set(definitions), set(entries))
        self.assertEqual(set(definitions), set(calls))
        self.assertEqual(len(re.findall(r"^ AAWC_STAGE2_BUILDING_LINES_\d+:0 ", generated_loc, re.MULTILINE)), 31)

    def test_occupancy_adapter_and_four_pressure_states_are_bound(self):
        values = read(VALUES)
        body = re.search(
            r"aawc_stage2_occupancy_percent_display\s*=\s*\{(.*?)\n\}",
            values,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(body)
        self.assertIn("value = aawc_stage2_occupancy", body.group(1))
        self.assertIn("multiply = 100", body.group(1))
        self.assertNotIn("max =", body.group(1))
        for path in (GUI, VALYRIA_GUI):
            gui = read(path)
            self.assertEqual(gui.count("AAWC_STAGE2_TT_OCCUPANCY"), 4)
            for threshold in (80, 90, 100):
                self.assertIn(f"'(CFixedPoint){threshold}'", gui)
            self.assertIn("aawc_population_holding_total", gui)
            self.assertIn("aawc_stage2_physical_capacity", gui)

    def test_localization_keys_are_unique_and_file_keeps_bom(self):
        data = LOC.read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        keys = re.findall(r"^\s*(AAWC_STAGE2_[A-Z0-9_]+):0\s", read(LOC), re.MULTILINE)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(keys), 31)
        self.assertTrue(BUILDING_LOC.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_aggregate_capacity_adjustment_label_is_not_building_only(self):
        loc = read(LOC)
        self.assertIn('AAWC_POPULATION_LABEL_INCOME:0 "Capacity Adjustment"', loc)
        self.assertNotIn('AAWC_POPULATION_LABEL_INCOME:0 "Building Capacity Bonus"', loc)
        for key in (
            "AAWC_POPULATION_TT_HOLDING_BUILDING_CAPACITY_DEBUG",
            "AAWC_POPULATION_TT_HOLDING_BUILDING_CAPACITY_BREAKDOWN",
        ):
            line = next(row for row in loc.splitlines() if row.startswith(f" {key}:0"))
            self.assertIn("Capacity Adjustment", line)
            self.assertIn("Aggregate adjustment", line)
            self.assertIn("may be positive or negative", line) if key.endswith("BREAKDOWN") else None

    def test_current_release_descriptors_match_without_parallel_stage3_system(self):
        versions = []
        for descriptor in (MOD / "descriptor.mod", OUTER):
            match = re.search(r'^version="(\d+\.\d+\.\d+\.\d+)"$', read(descriptor), re.MULTILINE)
            self.assertIsNotNone(match, descriptor)
            versions.append(match.group(1))
        self.assertEqual(versions[0], versions[1])
        self.assertFalse(any("stage3" in path.name.lower() for path in MOD.rglob("*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
