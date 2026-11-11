"""Hospice presentation must match Stage 2's capacity model, not legacy values."""
import csv
from pathlib import Path
import re
import unittest

from test_aawc_stage2_conditions import S, fixture


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod' / 'AGOT_Alternate_World_Compatch'
TABLE = ROOT / 'evidence' / 'stage2' / 'AAWC_REFORGING_STAGE2_BUILDING_CONTRIBUTIONS.csv'
EFFECTS = MOD / 'localization' / 'english' / 'aawc_population_building_effects_l_english.yml'
CAPACITY_LOC = MOD / 'localization' / 'english' / 'aawc_population_building_capacity_l_english.yml'
CAPACITY_CUSTOM = MOD / 'common' / 'customizable_localization' / 'aawc_population_building_capacity_custom_loc.txt'


class HospiceTooltipConsistency(unittest.TestCase):
    def test_health_only_hospices_have_no_capacity_presentation_or_effect(self):
        with TABLE.open(encoding='utf-8', newline='') as stream:
            hospice = {
                row['building']: row
                for row in csv.DictReader(stream)
                if row['building'].startswith('hospices_')
            }
        self.assertEqual(set(hospice), {f'hospices_{level:02}' for level in range(1, 9)})

        effects = EFFECTS.read_text(encoding='utf-8-sig')
        capacity_loc = CAPACITY_LOC.read_text(encoding='utf-8-sig')
        capacity_custom = CAPACITY_CUSTOM.read_text(encoding='utf-8-sig')
        self.assertNotIn('hospices_', capacity_loc)
        self.assertNotIn('hospices_', capacity_custom)

        base = fixture()
        for building, row in hospice.items():
            with self.subTest(building=building):
                self.assertEqual(row['sustenance'], '0')
                self.assertEqual(row['habitation'], '0')
                self.assertEqual(row['opportunity'], '0')
                self.assertEqual(row['security'], '0')
                self.assertEqual(row['amenities'], '0')
                self.assertEqual(row['space_percent'], '0')
                health = row['health'].rstrip('0').rstrip('.') if '.' in row['health'] else row['health']
                tooltip = re.search(
                    rf'^ aawc_population_building_effect_{building}:0 "([^"]*)"$',
                    effects,
                    re.MULTILINE,
                )
                self.assertIsNotNone(tooltip)
                self.assertIn(f'#Y Health:#! #P +{health}#!', tooltip.group(1))
                self.assertNotIn('Building Capacity:', tooltip.group(1))
                self.assertNotIn('Growth Rating:', tooltip.group(1))
                self.assertEqual(
                    fixture(buildings=(building,)).vars['aawc_population_expected'],
                    base.vars['aawc_population_expected'],
                )


if __name__ == '__main__':
    unittest.main()
