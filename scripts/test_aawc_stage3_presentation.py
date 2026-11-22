"""Focused Stage 3 building-copy and compact-presentation validation."""
import json
import re
import unittest

import generate_aawc_stage3_buildings as g
from validate_aawc_reforging_stage1_cohort_engine import definition_body


def localization(payload):
    return {
        key: json.loads(value)
        for key, value in re.findall(
            r'^ ([A-Za-z0-9_]+):0 (.*)$', payload.decode('utf-8-sig'), re.MULTILINE
        )
    }


class Presentation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = g.load_source(g.SOURCE)
        cls.artifacts = g.compile_buildings(cls.data, g.load_source(g.CONSTRUCTION))
        cls.custom = localization(cls.artifacts[g.LOC])
        cls.retained = localization(cls.artifacts[g.RETAINED_LOC])

    def test_every_custom_level_has_flavor_and_functional_clarity(self):
        seen = set()
        functional_sentence = (
            'Its current functional effects are the structural-condition and '
            'settlement-space values shown below.'
        )
        for chain in self.data['chains']:
            for level in chain['levels']:
                description = self.custom[level['player']['description_key']]
                with self.subTest(level=level['id']):
                    self.assertTrue(description.startswith('#F '))
                    self.assertTrue(description.endswith(f'#!\n\n{functional_sentence}'))
                    functional_copy = description.split('#!\n\n', 1)[1]
                    self.assertEqual(functional_copy, functional_sentence)
                    self.assertNotIn('This tier provides ', description)
                    self.assertGreaterEqual(len(description), 130)
                    self.assertNotIn('deferred', description.lower())
                seen.add(chain['id'])
        self.assertEqual(len(seen), 131)

    def test_custom_effects_are_exact_compact_icon_rows(self):
        forbidden = ('Structural conditions:', ';', 'Native economic',
                     'Growth Rating', 'Building Capacity', 'Migration Rating')
        for chain in self.data['chains']:
            for level in chain['levels']:
                effect = self.custom[level['player']['effect_description_key']]
                expected = ['#T AAWC Structural Conditions#!',
                            *g.dimension_lines(level['conditions'], level['capacity']['space_percent'])]
                rows = g.progression_requirements(
                    chain['id'].removeprefix('aawc_'), level['tier']
                )
                if rows:
                    expected += ['', '#T Building Prerequisites#!', *g.prerequisite_lines(rows)]
                with self.subTest(level=level['id']):
                    self.assertEqual(effect, '\n'.join(expected))
                    self.assertFalse(any(term in effect for term in forbidden))
                    for row in g.dimension_lines(
                            level['conditions'], level['capacity']['space_percent']):
                        self.assertRegex(row, r'^@[A-Za-z0-9_]+! #(P|N|high) ')

    def test_prerequisite_copy_resolves_exact_scripted_tiers(self):
        localized_buildings = {
            level['player']['name_key']
            for chain in self.data['chains'] for level in chain['levels']
        }
        for chain in self.data['chains']:
            for level in chain['levels']:
                rows = g.progression_requirements(
                    chain['id'].removeprefix('aawc_'), level['tier']
                )
                effect = self.custom[level['player']['effect_description_key']]
                referenced = set(re.findall(r'\$building_(aawc_[A-Za-z0-9_]+)\$', effect))
                expected = {bid for row in rows for bid in row['ids']}
                self.assertEqual(referenced, expected)
                self.assertTrue({f'building_{bid}' for bid in referenced} <= localized_buildings)

    def test_retained_main_lines_have_exact_tier_dimensions(self):
        overlay_path = g.MOD / 'common/buildings/zzzz_aawc_population_building_effects.txt'
        overlay = overlay_path.read_text(encoding='utf-8-sig')
        count = 0
        for chain, (tiers, _) in g.RETAINED_MAIN_LINE.items():
            for tier in range(1, tiers + 1):
                bid = f'{chain}_{tier:02}'
                body = definition_body(overlay, bid)
                effect_key = f'aawc_retained_{bid}_effects'
                effect = self.retained[effect_key]
                with self.subTest(building=bid):
                    self.assertRegex(body, rf'(?m)^\s*effect_desc\s*=\s*{effect_key}\s*$')
                    self.assertEqual(
                        effect,
                        '\n'.join([
                            '#T AAWC Structural Conditions#!',
                            *g.dimension_lines({
                                'sustenance': 0,
                                'habitation': (tier - 1) * 3,
                                'opportunity': tier - 1,
                                'health': 0,
                                'security': 0,
                                'amenities': 0,
                            }, 0, include_zero=True),
                        ]),
                    )
                    self.assertTrue(self.retained[f'building_{bid}_desc'].startswith('#F '))
                    self.assertNotRegex(effect, r'Growth Rating|Building Capacity|Migration Rating')
                count += 1
        self.assertEqual(count, 23)

    def test_retained_ruins_show_zero_inactive_structural_values(self):
        path = g.MOD / 'common/buildings/lv_blocker_buildings.txt'
        text = path.read_text(encoding='utf-8-sig')
        count = 0
        for chain in g.RETAINED_RUINS:
            for tier in range(1, 4):
                bid = f'{chain}_{tier:02}'
                effect_key = f'aawc_retained_{bid}_effects'
                body = definition_body(text, bid)
                effect = self.retained[effect_key]
                with self.subTest(building=bid):
                    self.assertRegex(body, rf'(?m)^\s*effect_desc\s*=\s*{effect_key}\s*$')
                    self.assertIn('@building_icon! #high 0%#! Settlement Space', effect)
                    for _, label in g.DIMENSION_PRESENTATION.values():
                        self.assertIn(label, effect)
                    self.assertIn('inactive while this holding is a ruin', effect)
                    self.assertNotRegex(effect, r'Growth Rating|Building Capacity|Migration Rating')
                    self.assertTrue(self.retained[f'building_{bid}_desc'].startswith('#F '))
                count += 1
        self.assertEqual(count, 9)

    def test_retained_localization_is_exhaustive_and_unique(self):
        self.assertEqual(len(self.retained), (23 + 9) * 3)
        self.assertEqual(
            set(re.findall(r'^ ([A-Za-z0-9_]+):0 ',
                           self.artifacts[g.RETAINED_LOC].decode('utf-8-sig'), re.MULTILINE)),
            set(self.retained),
        )


if __name__ == '__main__':
    unittest.main()
