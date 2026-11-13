import copy
import csv
import io
import re
import unittest
import generate_aawc_stage2_conditions as adapter
import generate_aawc_stage3_catalogue as catalogue

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
        output = adapter.render(self.rows)
        self.assertEqual(output.count('aawc_stage2_add_contribution_effect ='),771)
        self.assertEqual(output.count('\n\tif ='),131)
        self.assertEqual(output.count('\n\telse_if ='),640)
        for row in self.rows:
            args=' '.join(f'{f.upper()} = {row[f]}' for f in adapter.FIELDS)
            self.assertIn('has_building = '+row['building']+' }\n\t\taawc_stage2_add_contribution_effect = { '+args+' }',output)
        for chain in self.data['chains']:
            positions=[output.index('has_building = '+l['id']+' ') for l in chain['levels']]
            self.assertEqual(positions,sorted(positions,reverse=True))
        self.assertEqual(set(re.findall(r'([A-Za-z_0-9]+)\s*=', output)), {'aawc_stage2_building_contributions_effect','if','else_if','limit','has_building','aawc_stage2_add_contribution_effect', *(f.upper() for f in adapter.FIELDS)})

    def test_tooltips_preserve_signed_inputs(self):
        text=adapter.render_building_localization(self.rows)
        custom=adapter.render_building_custom_loc(self.rows)
        for row in self.rows:
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

if __name__=='__main__':
    unittest.main()

