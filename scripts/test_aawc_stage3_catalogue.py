"""Bounded compiler contract and adversarial input checks, not gameplay tests."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import generate_aawc_stage3_catalogue as gen


def fixture():
    """Synthetic census fixture; deliberately not product catalogue authoring."""
    chains = []
    for i in range(131):
        cid = f'fixture_{i}'
        # 79 inherited regular chains contain 546 levels, 26 inherited duchy
        # chains contain 78; the remaining 26 chains contain 147 new levels.
        legacy = i < 79 or 99 <= i < 125
        count = (7 if i < 72 or 79 <= i < 90 else 6) if i < 99 else (3 if i < 129 else 2)
        levels = []
        for tier in range(1, count + 1):
            bid = f'{cid}_{tier}'
            levels.append({'id': bid, 'legacy_id': f'legacy_{i}_{tier}' if legacy else None, 'tier': tier,
                           'upgrades_to': f'{cid}_{tier + 1}' if tier < count else None,
                           'costs': {'gold': 100, 'prestige': 0, 'piety': 0},
                           'construction_days': 365,
                           'conditions': dict.fromkeys(gen.DIMENSIONS, 0),
                           'capacity': {'status': 'missing', 'space_percent': None},
                           'tradeoffs': {'negative_conditions': {}, 'notes': None},
                           'gates': {'era_innovation_proposal': 'fixture', 'geography_proposal': 'fixture'},
                           'native_role': {'status': 'deferred', 'proposal': {
                               'economic_potential_pct_cumulative': '0', 'workforce_requirement_candidate': '0',
                               'native_effect_contract': 'fixture', 'chain_role': 'fixture',
                               'distinct_identity': 'fixture', 'construction_rationale': 'fixture', 'review_status': 'fixture'}},
                           'constructibility': {'status': 'blocked_review', 'reasons': ['Fixture only']},
                           'player': {'name': f'Fixture {tier}', 'name_key': f'building_{bid}',
                                      'description_key': f'building_{bid}_desc',
                                      'effect_description_key': f'aawc_stage3_{bid}_effects'}})
        chains.append({'id': cid, 'kind': 'regular' if i < 99 else 'duchy', 'family': 'fixture',
                       'lineage': {'status': 'legacy' if legacy else 'new',
                                   'legacy_chain': f'legacy_{i}' if legacy else None},
                       'gates': {'status': 'missing', 'proposal': 'Fixture only',
                                 'source_predicates': None, 'source_reference': None},
                       'player': {'status': 'missing', 'name': cid, 'description': None,
                                  'icon': None, 'model': None, 'effect_description': None},
                       'ai': {'status': 'missing', 'value': None},
                       'semantic_review': {'status': 'pending', 'reason': 'Fixture only'},
                       'levels': levels})
    return {'schema_version': 1, 'catalogue_id': 'aawc_stage3_d7_d8_v2',
            'imports': [{'path': 'fixture.csv', 'sha256': '0' * 64}],
            'policy': dict(gen.POLICY), 'chains': chains}


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()
        self.chain = self.data['chains'][0]
        self.level = self.chain['levels'][0]

    def reject(self):
        with self.assertRaises(gen.ContractError):
            gen.compile_catalogue(self.data)

    def test_census_and_all_level_fields(self):
        artifacts = gen.compile_catalogue(self.data)
        levels = json.loads(artifacts['levels.json'])['levels']
        self.assertEqual(len(levels), 771)
        self.assertTrue(all(set(gen.DIMENSIONS) == set(x['conditions']) for x in levels))
        self.assertTrue(all(x['gates'] and x['presentation'] and x['ai'] for x in levels))
        self.assertEqual(len(artifacts['condition_candidates.csv'].splitlines()), 772)

    def test_repeated_generation_is_byte_identical_and_pure(self):
        before = copy.deepcopy(self.data)
        self.assertEqual(gen.compile_catalogue(self.data), gen.compile_catalogue(self.data))
        self.assertEqual(before, self.data)

    def test_order_independent_level_and_csv_artifacts(self):
        before = gen.compile_catalogue(self.data)
        self.data['chains'].reverse()
        for chain in self.data['chains']:
            chain['levels'].reverse()
        after = gen.compile_catalogue(self.data)
        self.assertEqual(before['levels.json'], after['levels.json'])
        self.assertEqual(before['condition_candidates.csv'], after['condition_candidates.csv'])

    def test_missing_chain(self):
        self.data['chains'].pop()
        self.reject()

    def test_duplicate_chain(self):
        self.data['chains'][1]['id'] = self.chain['id']
        self.reject()

    def test_duplicate_building(self):
        self.data['chains'][1]['levels'][0]['id'] = self.level['id']
        self.reject()

    def test_noncontiguous_tier(self):
        self.level['tier'] = 0
        self.reject()

    def test_cross_chain_upgrade(self):
        self.level['upgrades_to'] = self.data['chains'][1]['levels'][0]['id']
        self.reject()

    def test_terminal_upgrade_loop(self):
        self.chain['levels'][-1]['upgrades_to'] = self.level['id']
        self.reject()

    def test_missing_dimension(self):
        del self.level['conditions']['health']
        self.reject()

    def test_nonfinite_or_boolean_numbers(self):
        for value in (float('nan'), float('inf'), True, '1'):
            with self.subTest(value=value):
                self.level['conditions']['health'] = value
                self.reject()

    def test_costs_and_duration(self):
        for target, key, value in ((self.level['costs'], 'gold', 0),
                                   (self.level['costs'], 'piety', -1),
                                   (self.level, 'construction_days', 0)):
            with self.subTest(key=key):
                old = target[key]
                target[key] = value
                self.reject()
                target[key] = old

    def test_mixed_currency_preserved(self):
        self.level['costs'].update(prestige=75, piety=50)
        rows = json.loads(gen.compile_catalogue(self.data)['levels.json'])['levels']
        self.assertEqual(rows[0]['costs'], self.level['costs'])

    def test_missing_capacity_not_invented_as_zero(self):
        artifacts = gen.compile_catalogue(self.data)
        rows = json.loads(artifacts['levels.json'])['levels']
        self.assertIsNone(rows[0]['capacity']['space_percent'])
        self.assertIn(b',,missing,blocked_review\n', artifacts['condition_candidates.csv'])
        self.level['capacity']['status'] = 'approved'
        self.reject()

    def test_tradeoffs_must_match(self):
        self.level['conditions']['health'] = -5
        self.reject()
        self.level['tradeoffs']['negative_conditions'] = {'health': -5}
        gen.compile_catalogue(self.data)

    def test_unresolved_gates_cannot_be_marked_approved(self):
        self.chain['gates']['status'] = 'approved'
        self.reject()

    def test_unresolved_assets_cannot_be_marked_approved(self):
        self.chain['player']['status'] = 'approved'
        self.reject()

    def test_unresolved_ai_cannot_be_marked_approved(self):
        self.chain['ai']['status'] = 'approved'
        self.reject()

    def test_activation_and_deferred_boundaries(self):
        for key in gen.POLICY:
            old = self.data['policy'][key]
            self.data['policy'][key] = 'activated'
            self.reject()
            self.data['policy'][key] = old
        self.level['native_role']['status'] = 'active'
        self.reject()

    def test_constructibility_cannot_enable_runtime(self):
        self.level['constructibility']['status'] = 'constructible'
        self.reject()

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(gen.ContractError):
            json.loads('{"schema_version": 1, "schema_version": 2}', object_pairs_hook=gen.unique_object)

    def test_kind_level_census(self):
        self.data['chains'][0]['kind'] = 'duchy'
        self.data['chains'][-1]['kind'] = 'regular'
        self.reject()

    def test_unknown_fields_and_script_injection_ids_rejected(self):
        self.level['on_complete'] = 'change_variable = { name = population add = 1 }'
        self.reject()
        del self.level['on_complete']
        self.level['id'] = 'bad = { effect = yes }'
        self.reject()

    def test_cli_check_is_read_only_and_detects_drift(self):
        with tempfile.TemporaryDirectory(prefix='aawc-stage3-test-') as folder:
            root = Path(folder)
            source = root / 'source.json'
            source.write_bytes(gen.json_bytes(self.data))
            output = root / 'generated'
            cmd = [sys.executable, '-B', str(Path(gen.__file__)), '--source', str(source), '--output', str(output)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertEqual(subprocess.run(cmd + ['--check'], capture_output=True).returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
            (output / 'levels.json').write_bytes(b'corrupt')
            self.assertNotEqual(subprocess.run(cmd + ['--check'], capture_output=True).returncode, 0)
            self.assertEqual((output / 'levels.json').read_bytes(), b'corrupt')
            blocked = subprocess.run(cmd[:-1] + [str(root / 'mod' / 'generated')], capture_output=True)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertFalse((root / 'mod').exists())


class AuthoredSourceTests(unittest.TestCase):
    def test_complete_source_and_generated_parity(self):
        data = json.loads(gen.SOURCE.read_text(encoding='utf-8'))
        for name, expected in gen.compile_catalogue(data).items():
            self.assertEqual((gen.OUTPUT / name).read_bytes(), expected, name)

    def test_import_provenance_matches_retained_bytes(self):
        data = json.loads(gen.SOURCE.read_text(encoding='utf-8'))
        for item in data['imports']:
            self.assertEqual(hashlib.sha256((gen.ROOT / item['path']).read_bytes()).hexdigest(), item['sha256'])

    def test_all_authored_level_values_survive_import(self):
        data = gen.load_source(gen.SOURCE)
        actual = {x['id']: x for c in data['chains'] for x in c['levels']}
        path = gen.ROOT / 'evidence/stage3/imported/AAWC_Reforging_Proposed_Building_Levels_v2.csv'
        with path.open(encoding='utf-8-sig', newline='') as stream:
            original = list(csv.DictReader(stream))
        self.assertEqual(set(actual), {x['level_id'] for x in original})
        negative_secondary = 0
        for row in original:
            level = actual[row['level_id']]
            self.assertEqual(level['tier'], int(row['level']))
            self.assertEqual(level['construction_days'], int(row['construction_days']))
            for currency in ('gold', 'prestige', 'piety'):
                self.assertEqual(level['costs'][currency], int(row[f'{currency}_cost']))
            expected = dict.fromkeys(gen.DIMENSIONS, 0)
            for role in ('primary', 'secondary', 'tradeoff'):
                expected[row[f'{role}_dimension'].lower()] = int(row[f'{role}_score_cumulative'])
            self.assertEqual(level['conditions'], expected)
            self.assertEqual(level['gates']['era_innovation_proposal'], row['era_innovation_gate_candidate'])
            self.assertEqual(level['gates']['geography_proposal'], row['geography_contract'])
            for field in ('economic_potential_pct_cumulative', 'workforce_requirement_candidate', 'native_effect_contract'):
                self.assertEqual(level['native_role']['proposal'][field], row[field])
            negative_secondary += int(row['secondary_score_cumulative']) < 0
        self.assertEqual(negative_secondary, 42)

    def test_legacy_ids_and_two_heritage_extensions(self):
        data = gen.load_source(gen.SOURCE)
        expected = set()
        path = gen.ROOT / 'evidence/stage3/imported/AAWC_REFORGING_M1_V2_LEGACY_LINEAGE.csv'
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                expected.update(row['legacy_ids'].split(' | '))
        levels = [x for c in data['chains'] for x in c['levels']]
        self.assertEqual({x['legacy_id'] for x in levels if x['legacy_id']}, expected)
        self.assertEqual(len(expected), 624)
        extensions = [x['id'] for c in data['chains'] if c['lineage']['status'] == 'legacy'
                      for x in c['levels'] if x['legacy_id'] is None]
        self.assertEqual(sorted(extensions), ['aawc_great_megalith_02', 'aawc_tower_of_silence_02'])

    def test_import_cannot_overwrite_authored_source(self):
        with tempfile.TemporaryDirectory(prefix='aawc-stage3-import-test-') as folder:
            path = Path(folder) / 'existing.json'
            path.write_bytes(b'authored changes')
            command = [sys.executable, '-B', str(gen.ROOT / 'scripts/import_aawc_stage3_catalogue.py'), '--output', str(path)]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(path.read_bytes(), b'authored changes')


if __name__ == '__main__':
    unittest.main()
