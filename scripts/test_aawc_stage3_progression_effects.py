"""Focused prerequisite-DAG and effects-policy validation; not CK3 certification."""
import json
import re
import unittest

import generate_aawc_stage3_buildings as g
from test_aawc_cohort_bounded_arithmetic import parse


RETAINED_MAIN_LINE_LEVELS = {
    *(f'castle_{tier:02}' for tier in range(1, 6)),
    *(f'city_{tier:02}' for tier in range(1, 6)),
    *(f'settlement_{tier:02}' for tier in range(1, 4)),
    *(f'temple_{tier:02}' for tier in range(1, 5)),
    *(f'temple_citadel_{tier:02}' for tier in range(1, 5)),
    *(f'tribe_{tier:02}' for tier in range(1, 3)),
}


class ProgressionEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = g.load_source(g.SOURCE)
        cls.contract = g.load_source(g.CONSTRUCTION)
        cls.artifacts = g.compile_buildings(cls.data, cls.contract)
        cls.metadata_root = json.loads(cls.artifacts[g.METADATA])
        cls.metadata = {row['id']: row for row in cls.metadata_root['levels']}
        cls.chains = {chain['id'].removeprefix('aawc_'): chain for chain in cls.data['chains']}
        script = cls.artifacts[g.BUILDINGS].decode('utf-8-sig')
        cls.definitions = {bid: {key: value for key, _, value in body}
                           for bid, _, body in parse(script)}

    def test_progression_policy_has_expected_bounded_coverage(self):
        self.assertEqual(len(g.PREREQUISITE_PROGRESSIONS), 52)
        self.assertEqual(sum(len(value) for value in g.PREREQUISITE_PROGRESSIONS.values()), 53)
        self.assertLess(len(g.PREREQUISITE_PROGRESSIONS), len(self.chains))
        for target, requirements in g.PREREQUISITE_PROGRESSIONS.items():
            self.assertIn(target, self.chains)
            self.assertTrue(requirements)
            for requirement in requirements:
                self.assertTrue(requirement['rationale'])
                self.assertTrue(requirement['sources'])

    def test_schedules_are_monotonic_in_range_and_never_regressive(self):
        for target, requirements in g.PREREQUISITE_PROGRESSIONS.items():
            target_max = len(self.chains[target]['levels'])
            for requirement in requirements:
                schedule = requirement['schedule']
                target_tiers = [row[0] for row in schedule]
                source_tiers = [row[1] for row in schedule]
                with self.subTest(target=target, sources=requirement['sources']):
                    self.assertEqual(target_tiers[0], 1)
                    self.assertEqual(target_tiers, sorted(set(target_tiers)))
                    self.assertEqual(source_tiers, sorted(set(source_tiers)))
                    self.assertLessEqual(target_tiers[-1], target_max)
                    for source in requirement['sources']:
                        self.assertIn(source, self.chains)
                        self.assertLessEqual(source_tiers[-1], len(self.chains[source]['levels']))
                        self.assertNotEqual(source, target)

    def test_progression_graph_is_acyclic_and_terminates_at_regular_foundations(self):
        graph = {target: {source for requirement in requirements
                          for source in requirement['sources']}
                 for target, requirements in g.PREREQUISITE_PROGRESSIONS.items()}
        visiting = set()
        visited = set()

        def visit(node):
            self.assertNotIn(node, visiting, f'positive prerequisite cycle reaches {node}')
            if node in visited:
                return
            visiting.add(node)
            for child in graph.get(node, ()):
                visit(child)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)
        foundations = {source for sources in graph.values() for source in sources if source not in graph}
        self.assertTrue(foundations)
        for source in foundations:
            self.assertEqual(self.chains[source]['kind'], 'regular')

    def test_no_duchy_chain_requires_another_duchy_slot(self):
        for target, requirements in g.PREREQUISITE_PROGRESSIONS.items():
            if self.chains[target]['kind'] != 'duchy':
                continue
            for requirement in requirements:
                for source in requirement['sources']:
                    with self.subTest(target=target, source=source):
                        self.assertEqual(self.chains[source]['kind'], 'regular')

    def test_each_level_emits_the_selected_reachable_requirement(self):
        for target in g.PREREQUISITE_PROGRESSIONS:
            chain = self.chains[target]
            previous = None
            for level in chain['levels']:
                expected = g.progression_requirements(target, level['tier'])
                actual = self.metadata[level['id']]['prerequisite_progression']
                normalized = [{**row, 'ids': list(row['ids'])} for row in expected]
                for row in normalized:
                    row.pop('text')
                with self.subTest(level=level['id']):
                    self.assertEqual(actual, normalized)
                    gate = '\n'.join(self.metadata[level['id']]['gates'].values())
                    for row in expected:
                        for source_id in row['ids']:
                            self.assertIn(f'has_building_or_higher = {source_id}', gate)
                    current = tuple(row['source_tier'] for row in expected)
                    if previous is not None:
                        self.assertTrue(all(a <= b for a, b in zip(previous, current)))
                    previous = current

    def test_effects_inventory_is_exhaustive_and_embedded_in_runtime_metadata(self):
        expected_statuses = {
            'structural_conditions': 'implemented',
            'settlement_space': 'implemented',
            'construction_unlocks': 'implemented',
            'custom_holding_modifiers': 'deferred_population_scaling',
            'custom_county_modifiers': 'deferred_population_scaling',
            'custom_holder_modifiers': 'deferred_population_scaling',
            'custom_military_modifiers': 'deferred_military_lifecycle',
            'neutral_effect_desc_bridge': 'implemented_non_gameplay',
            'retained_main_line_native_modifiers': 'implemented_preserved',
            'retained_old_growth_capacity_effect_desc': 'removed',
        }
        self.assertEqual({key: row['status'] for key, row in g.EFFECTS_POLICY.items()}, expected_statuses)
        self.assertEqual(self.metadata_root['effects_policy'], g.EFFECTS_POLICY)
        for row in g.EFFECTS_POLICY.values():
            self.assertTrue(row['scope'])
            self.assertTrue(row['authority'])

    def test_deferred_custom_outputs_are_not_represented_as_functional(self):
        forbidden = {'province_modifier', 'character_modifier', 'holding_modifier'}
        for bid, definition in self.definitions.items():
            with self.subTest(bid=bid):
                self.assertFalse(forbidden & set(definition))
                self.assertEqual(definition['county_modifier'], [('development_growth_factor', '=', '0')])
                self.assertEqual(self.metadata[bid]['native_role']['status'], 'deferred')
        localization = self.artifacts[g.LOC].decode('utf-8-sig')
        # Deferred Stage 6/7 policy belongs in project documentation, not in
        # every player-facing building panel. The compact presentation must
        # not imply those proposal-only outputs are live.
        self.assertNotIn('Native economic and military outputs are deferred.', localization)
        self.assertNotIn('This Holding:', localization)
        self.assertNotIn('This County:', localization)
        self.assertNotIn('Holder:', localization)
        self.assertNotIn('placeholder effect', localization.lower())

    def test_obsolete_growth_capacity_effects_are_removed_from_retained_main_lines(self):
        overlay = (g.MOD / 'common/buildings/zzzz_aawc_population_building_effects.txt').read_text(encoding='utf-8-sig')
        referenced = set(re.findall(r'(?m)^\s*effect_desc\s*=\s*aawc_population_building_effect_(\w+)\s*$', overlay))
        self.assertFalse(RETAINED_MAIN_LINE_LEVELS & referenced)
        self.assertEqual(len(RETAINED_MAIN_LINE_LEVELS), 23)

    def test_dedicated_policy_document_records_graph_and_effect_decisions(self):
        path = g.ROOT / 'catalogue/stage3/PROGRESSION_EFFECTS_POLICY.md'
        text = path.read_text(encoding='utf-8')
        self.assertIn('52 specialized chains', text)
        self.assertIn('53 positive prerequisite requirements', text)
        for key, row in g.EFFECTS_POLICY.items():
            with self.subTest(policy=key):
                self.assertIn(f'`{key}`', text)
                self.assertIn(f'`{row["status"]}`', text)


if __name__ == '__main__':
    unittest.main()
