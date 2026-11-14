import copy
import csv
import io
import re
import unittest
import generate_aawc_stage2_conditions as adapter
import generate_aawc_stage3_catalogue as catalogue
from test_aawc_cohort_bounded_arithmetic import SourceVM, S

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.data = catalogue.load_source(catalogue.SOURCE)
        self.rows = adapter.stage3_rows(self.data)

    def test_exact_all_level_projection(self):
        expected = {l['id']: (c,l) for c in self.data['chains'] for l in c['levels']}
        self.assertEqual(len(self.rows),771)
        self.assertEqual({r['building'] for r in self.rows},set(expected))
        self.assertEqual(len({r['chain'] for r in self.rows}),131)
        for row in self.rows:
            chain,level = expected[row['building']]
            self.assertEqual(row['chain'],chain['id'])
            self.assertEqual(int(row['level']),level['tier'])
            for field in adapter.DIMENSIONS:
                self.assertEqual(float(row[field]),level['conditions'][field])
            self.assertEqual(float(row['space_percent']),level['capacity']['space_percent'])
        self.assertEqual(list(csv.DictReader(io.StringIO(adapter.render_input_table(self.rows)))),self.rows)
        self.assertEqual(adapter.STAGE3_TABLE.read_text(),adapter.render_input_table(self.rows))

    def test_existing_renderer_exact_effects_and_highest_tier(self):
        runtime = adapter.rows()
        output = adapter.render(runtime)
        self.assertEqual(output.count('aawc_stage2_add_contribution_effect ='),771)
        self.assertEqual(output.count('\n\tif ='),131)
        self.assertEqual(output.count('\n\telse_if ='),640)
        self.assertEqual(output.count('\n\t\t\tOR = {'), 616)
        self.assertEqual(len(re.findall(r'^aawc_stage2_building_contributions_effect\s*=\s*\{', output, re.M)), 1)
        for row in runtime:
            args=' '.join(f'{f.upper()} = {row[f]}' for f in adapter.FIELDS)
            self.assertEqual(output.count('has_building = '+row['building']), 1)
            if row['legacy_building']:
                self.assertEqual(output.count('has_building = '+row['legacy_building']), 1)
                self.assertIn('has_building = '+row['building']+'\n\t\t\t\thas_building = '+row['legacy_building'], output)
            self.assertIn('aawc_stage2_add_contribution_effect = { '+args+' }',output)
        for chain in self.data['chains']:
            positions=[output.index('has_building = '+l['id']) for l in chain['levels']]
            self.assertEqual(positions,sorted(positions,reverse=True))
        self.assertEqual(set(re.findall(r'([A-Za-z_0-9]+)\s*=', output)), {'aawc_stage2_building_contributions_effect','if','else_if','limit','OR','has_building','aawc_stage2_add_contribution_effect', *(f.upper() for f in adapter.FIELDS)})

    def test_runtime_reads_validated_csv_and_target_legacy_pair_contributes_once(self):
        runtime = adapter.rows()
        with adapter.STAGE3_TABLE.open(encoding='utf-8') as stream:
            csv_rows = list(csv.DictReader(stream))
        self.assertEqual([{key: row[key] for key in csv_rows[0]} for row in runtime], csv_rows)
        mapped = [row for row in runtime if row['legacy_building']]
        self.assertEqual(len(mapped), 616)
        row = mapped[0]
        vm = SourceVM()
        vm.buildings = {row['building'], row['legacy_building']}
        for dimension in adapter.DIMENSIONS:
            vm.vars['aawc_stage2_structural_'+dimension] = 50*S
        vm.vars['aawc_stage2_space_percent'] = 0
        vm.call('aawc_stage2_building_contributions_effect')
        actual = [vm.vars['aawc_stage2_structural_'+field] - 50*S for field in adapter.DIMENSIONS]
        actual.append(vm.vars['aawc_stage2_space_percent'])
        self.assertEqual(actual, [int(float(row[field])*S) for field in adapter.FIELDS])

    def test_absent_powder_magazine_legacy_ids_are_never_probed(self):
        runtime = adapter.rows()
        powder = [row for row in runtime if row['chain'] == 'aawc_powder_magazine']
        self.assertEqual(len(powder), 8)
        generated = adapter.render(runtime)
        custom = adapter.render_building_custom_loc(runtime)
        for tier, row in enumerate(powder, 1):
            legacy = f'powder_magazine_{tier:02}'
            self.assertIsNone(row['legacy_building'])
            self.assertNotRegex(generated, rf'has_building = {legacy}(?:\s|$)')
            self.assertNotRegex(custom, rf'has_building = {legacy}(?:\s|$)')
            self.assertIn(f'has_building = aawc_{legacy}', generated)
            self.assertIn(f'has_building = aawc_{legacy}', custom)

    def test_tooltips_preserve_signed_inputs(self):
        runtime=adapter.rows()
        text=adapter.render_building_localization(runtime)
        custom=adapter.render_building_custom_loc(runtime)
        for row in runtime:
            self.assertIn('localization_key = aawc_stage2_building_'+row['building'],custom)
            line=next(l for l in text.splitlines() if l.startswith(' aawc_stage2_building_'+row['building']+':'))
            for field in adapter.FIELDS:
                if float(row[field]):
                    self.assertIn(adapter.format_contribution(row[field]),line)

    def test_policy_is_tier_sensitive_and_positive_growth_dominates(self):
        bychain={c['id']:c for c in self.data['chains']}
        for chain in self.data['chains']:
            values=[l['capacity']['space_percent'] for l in chain['levels']]
            self.assertEqual(values,[values[0]*l['tier'] for l in chain['levels']])
            if chain['family']=='mine':
                self.assertEqual(set(values),{0})
            if chain['family']=='housing':
                self.assertGreaterEqual(values[0],10)
        top=lambda cid: bychain[cid]['levels'][-1]['capacity']['space_percent']
        self.assertGreater(top('aawc_urban_tenements'),top('aawc_village_cottages'))
        penalties=sorted(c['levels'][-1]['capacity']['space_percent'] for c in self.data['chains'])[:4]
        self.assertGreater(top('aawc_village_cottages')+sum(penalties),0)

    def test_missing_unapproved_nonfinite_rejected(self):
        for capacity in ({'status':'missing','space_percent':None},
                         {'status':'proposed','space_percent':0},
                         {'status':'approved','space_percent':float('nan')}):
            data=copy.deepcopy(self.data)
            data['chains'][0]['levels'][0]['capacity']=capacity
            with self.assertRaises((ValueError,catalogue.ContractError)):
                adapter.stage3_rows(data)

    def test_deterministic_pure_and_ignores_deferred_metadata(self):
        before=copy.deepcopy(self.data)
        original=adapter.render_input_table(self.rows)
        self.data['chains'].reverse()
        for chain in self.data['chains']:
            chain['levels'].reverse()
            for level in chain['levels']:
                level['native_role']['proposal']['native_effect_contract']='change_variable = { name = population add = 999 }'
        self.assertEqual(original,adapter.render_input_table(adapter.stage3_rows(self.data)))
        self.assertEqual(self.rows,adapter.stage3_rows(before))
        self.assertEqual(adapter.OUTPUT.read_text(encoding='utf-8-sig'),adapter.render(adapter.rows()))

    def test_runtime_artifacts_are_stage2_only_and_never_mutate_population(self):
        output = adapter.render(adapter.rows())
        self.assertNotRegex(output, r'(?:set|change|remove)_variable\s*=\s*\{?\s*name\s*=\s*aawc_(?:population|reforging_cohort)')
        self.assertNotIn('native_effect_contract', output)
        self.assertNotIn('workforce', output)
        self.assertNotIn('men_at_arms', output)
        self.assertNotIn('tax_mult', output)

if __name__=='__main__':
    unittest.main()

