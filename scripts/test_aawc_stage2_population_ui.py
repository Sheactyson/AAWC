"""Focused current-release Stage 2 Population UI contract checks."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"
OUTER = ROOT / "mod" / "AGOT_Alternate_World_Compatch.mod"
GUI = MOD / "gui" / "window_county_view.gui"
LOC = MOD / "localization" / "english" / "aawc_population_l_english.yml"
VALUES = MOD / "common" / "script_values" / "aawc_stage2_condition_values.txt"
DIMENSIONS = ("sustenance", "habitation", "opportunity", "health", "security", "amenities")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class Stage2PopulationUI(unittest.TestCase):
    def test_all_six_effective_scores_are_bound_once_in_population_panel(self):
        gui = read(GUI)
        population = gui[gui.index("#### POPULATION ####"):gui.index("#### LEGENDS ####")]
        self.assertIn('name = "aawc_stage2_living_conditions"', population)
        panel = population[population.index('name = "aawc_stage2_living_conditions"'):]
        for dimension in DIMENSIONS:
            with self.subTest(dimension=dimension):
                accessor = f"aawc_stage2_effective_{dimension}_value"
                self.assertEqual(panel.count(accessor), 1)
                self.assertIn(f'AAWC_STAGE2_TT_{dimension.upper()}', panel)

    def test_tooltips_expose_effective_and_structural_values(self):
        loc = read(LOC)
        for dimension in DIMENSIONS:
            with self.subTest(dimension=dimension):
                self.assertIn(f"aawc_stage2_effective_{dimension}_value", loc)
                self.assertIn(f"aawc_stage2_structural_{dimension}_value", loc)
        self.assertIn("0–100; 50 is neutral", loc)

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
        gui = read(GUI)
        self.assertEqual(gui.count("AAWC_STAGE2_TT_OCCUPANCY"), 4)
        for threshold in (80, 90, 100):
            self.assertIn(f"'(CFixedPoint){threshold}'", gui)
        self.assertIn("aawc_population_holding_total", gui)
        self.assertIn("aawc_stage2_physical_capacity", gui)

    def test_localization_keys_are_unique_and_file_keeps_bom(self):
        data = LOC.read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        keys = re.findall(r"^\s*(AAWC_STAGE2_[A-Z0-9_]+):0\s", read(LOC), re.MULTILINE)
        self.assertEqual(len(keys), 20)
        self.assertEqual(len(keys), len(set(keys)))

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

    def test_current_release_is_versioned_without_stage3_payload(self):
        versions = []
        for descriptor in (MOD / "descriptor.mod", OUTER):
            match = re.search(r'^version="(\d+\.\d+\.\d+\.\d+)"$', read(descriptor), re.MULTILINE)
            self.assertIsNotNone(match, descriptor)
            versions.append(match.group(1))
        self.assertEqual(versions[0], versions[1])
        self.assertFalse(any("stage3" in path.name.lower() for path in MOD.rglob("*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
