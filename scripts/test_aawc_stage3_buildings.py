"""Focused construction compiler and native-predicate fixture checks, not CK3 certification."""
import copy
import json
import re
import unittest
from collections import Counter

import generate_aawc_stage3_buildings as g
from generate_aawc_stage3_catalogue import ContractError
from test_aawc_cohort_bounded_arithmetic import parse
from validate_aawc_release import structural_error, top_level_definitions


def evaluate(nodes, fixture):
    """Only new-chain native subset; unknown operations fail, never default true."""
    def one(k,op,v):
        if k in ('AND','OR','NOT'):
            values=[one(*n) for n in v]
            return {'AND':all(values),'OR':any(values),'NOT':not all(values)}[k]
        if k in ('culture','county','county.holder'): return evaluate(v,fixture)
        if k=='aawc_population_valid_settlement_for_cohort_trigger': return fixture['holding']!='ruins_holding'
        if k=='has_holding_type': return fixture['holding']==v
        if k=='has_building_or_higher': return v in fixture['buildings']
        if k=='has_innovation': return v in fixture['innovations']
        if k=='has_title': return fixture['duchy_owner']
        if k=='development_level':
            assert op=='>='
            return fixture['development']>=int(v)
        if k.startswith('agot_is_') and k.endswith('_terrain'): return fixture['terrain']==k[8:-8]
        if k=='is_coastal': return fixture['coast']==(v=='yes')
        if k=='is_riverside_province': return fixture['river']==(v=='yes')
        raise AssertionError(('unsupported fixture predicate',k,op,v))
    return all(one(*node) for node in nodes)


class Buildings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=g.load_source(g.SOURCE);cls.contract=g.load_source(g.CONSTRUCTION)
        cls.artifacts=g.compile_buildings(cls.data,cls.contract)
        cls.script=cls.artifacts[g.BUILDINGS].decode()
        cls.parsed=parse(cls.script)
        cls.definitions={k:{key:val for key,_,val in body} for k,_,body in cls.parsed}
        cls.levels={l['id']:(c,l) for c in cls.data['chains'] for l in c['levels']}
        cls.metadata=json.loads(cls.artifacts[g.METADATA])['levels']

    def test_all_definitions_unique_and_no_protected_ids(self):
        self.assertEqual(len(self.parsed),771)
        self.assertEqual(set(self.definitions),set(self.levels))
        counts=Counter(k for k,_,_ in self.parsed)
        self.assertEqual(set(counts.values()),{1})
        global_defs=top_level_definitions(g.MOD/'common/buildings')
        self.assertTrue(all(len(global_defs[bid])==1 for bid in self.levels))
        self.assertIsNone(structural_error(g.BUILDINGS))

    def test_all_costs_times_types_and_upgrade_topology(self):
        for bid,(chain,level) in self.levels.items():
            with self.subTest(bid=bid):
                actual=self.definitions[bid]
                self.assertEqual(float(actual['construction_time']),level['construction_days'])
                self.assertEqual({k:float(v) for k,_,v in actual['cost']},level['costs'])
                self.assertEqual(actual.get('next_building'),level['upgrades_to'])
                self.assertEqual(actual['type'],'duchy_capital' if chain['kind']=='duchy' else 'regular')

    def test_localization_and_signed_effects_cover_every_level(self):
        raw=self.artifacts[g.LOC].decode('utf-8-sig')
        keys=re.findall(r'^ (\w+):0 ',raw,re.M)
        self.assertEqual(len(keys),len(set(keys)))
        localized={m[0]:json.loads(m[1]) for m in re.findall(r'^ (\w+):0 (.*)$',raw,re.M)}
        self.assertEqual(len(keys),771*3+131*2)
        for bid,(chain,level) in self.levels.items():
            for field in ('name_key','description_key','effect_description_key'):
                self.assertTrue(localized[level['player'][field]])
            effect=localized[level['player']['effect_description_key']]
            for dimension,value in level['conditions'].items():
                if value:self.assertIn(f'{dimension.title()} {value:+g}',effect)
            self.assertIn(f'{level["capacity"]["space_percent"]:+g}%',effect)
            self.assertEqual(self.definitions[bid]['effect_desc'],level['player']['effect_description_key'])

    def test_native_roles_and_ai_all_levels_no_stage6_or_stage7_outputs(self):
        allowed={'construction_time','cost','type','type_icon','show_disabled',*g.GATE_KEYS,'next_building','effect_desc','ai_value'}
        self.assertEqual({r['id'] for r in self.metadata},set(self.levels))
        for r in self.metadata:
            actual=self.definitions[r['id']]
            self.assertLessEqual(set(actual),allowed)
            self.assertEqual(r['native_role'],self.levels[r['id']][1]['native_role'])
            self.assertEqual(r['native_role']['status'],'deferred')
            self.assertGreater(r['ai_value'],0)
            self.assertEqual(actual['ai_value'],[('base','=',str(r['ai_value']))])

    def test_all_direct_references_close_and_era_schedule_applies(self):
        symbols=self.contract['symbols']
        for r in self.metadata:
            text='\n'.join(r['gates'].values())
            self.assertFalse(g.gate_keys(text)-g.NATIVE_GATE_KEYS-set(symbols['scripted_triggers']))
            self.assertFalse(set(re.findall(r'has_building(?:_or_higher)?\s*=\s*(\w+)',text))-set(symbols['buildings'])-set(self.levels))
            if r['era_innovation']:self.assertIn('has_innovation = '+r['era_innovation'],text)

    def test_new_chain_positive_and_negative_holding_fixtures_every_tier(self):
        seen=set()
        for c in self.data['chains']:
            if c['lineage']['status']!='new':continue
            name=c['id'].removeprefix('aawc_');seen.add(name)
            fixture={'holding':'castle_holding','development':20,'terrain':'plains','coast':True,'river':True,'duchy_owner':True,
                     'buildings':set(self.levels)|{'city_02','castle_02'},'innovations':set(self.contract['symbols']['culture/innovations'])}
            if name in ('irrigation_estates','saltworks'):fixture['terrain']='drylands'
            if name=='terraced_farms':fixture['terrain']='hills'
            if name in ('trade_guilds','urban_tenements'):fixture['holding']='city_holding'
            for level in c['levels']:
                gates=self.definitions[level['id']]
                with self.subTest(bid=level['id']):
                    for key in g.GATE_KEYS:
                        if key in gates:self.assertTrue(evaluate(gates[key],fixture),(name,key))
                    bad={**fixture,'holding':'ruins_holding'}
                    self.assertFalse(evaluate(gates['can_construct_potential'],bad))
        self.assertEqual(seen,set(g.NEW))

    def test_specific_ecology_institutions_and_ownership_reject_invalid_fixtures(self):
        fixture={'holding':'castle_holding','development':20,'terrain':'plains','coast':True,'river':True,'duchy_owner':True,
                 'buildings':set(self.levels)|{'castle_02'},'innovations':set(self.contract['symbols']['culture/innovations'])}
        cases=[('coastal_fisheries','can_construct_potential',{'coast':False}),
               ('river_docks','can_construct_potential',{'river':False}),
               ('river_fisheries','can_construct_potential',{'river':False}),
               ('shipwrights','can_construct_potential',{'river':False,'coast':False}),
               ('sewers','can_construct',{'development':9}),
               ('sewers','can_construct',{'buildings':set()}),
               ('public_baths','can_construct',{'river':False,'buildings':set()}),
               ('cavalry_courses','can_construct',{'buildings':set()}),
               ('scholars_quarters','can_construct',{'buildings':set()}),
               ('duchy_grand_hospital','can_construct',{'buildings':set()}),
               ('duchy_civic_court','can_construct',{'duchy_owner':False}),
               ('mustering_fields','can_construct',{'terrain':'mountains'}),
               ('terraced_farms','can_construct_potential',{'terrain':'desert'})]
        for name,key,delta in cases:
            with self.subTest(name=name,delta=delta):
                self.assertFalse(evaluate(self.definitions['aawc_'+name+'_01'][key],{**fixture,**delta}))

    def test_heritage_restrictions_and_exceptions_remain_explicit(self):
        for name,token in [('gold_mines','agot_province_gold_veins'),('amber_collection','agot_province_amber_deposits'),
                           ('godswood','can_build_weirwood_groves'),('dragon_kiln','unlock_dragon_kiln_buildings'),
                           ('tribe','tribal_holding'),('temple_citadel','government_is_mandala'),('pirate_control','pirate_den_01')]:
            for r in self.metadata:
                if r['chain']=='aawc_'+name:self.assertIn(token,'\n'.join(r['gates'].values()))

    def test_deterministic_pure_generation_and_committed_artifact_parity(self):
        before=copy.deepcopy(self.contract)
        self.assertEqual(self.artifacts,g.compile_buildings(self.data,self.contract))
        self.assertEqual(before,self.contract)
        for path,payload in self.artifacts.items():self.assertEqual(path.read_bytes(),payload)

    def test_fail_closed_missing_extra_malformed_or_unknown_gates(self):
        bid='aawc_amber_collection_01';cid='aawc_amber_collection'
        mutations=[lambda c:c['chains'].pop(cid),
                   lambda c:c['chains'][cid]['levels'].pop(bid),
                   lambda c:c['chains'][cid]['levels'][bid]['gates'].update(can_construct='always = no'),
                   lambda c:c['chains'][cid]['levels'][bid]['gates'].update(can_construct='unknown_trigger = yes'),
                   lambda c:c['chains'][cid]['levels'][bid]['gates'].update(can_construct='has_building = nonexistent_building'),
                   lambda c:c['chains'][cid]['levels'][bid]['gates'].update(can_construct='culture = { has_innovation = nonexistent_innovation }'),
                   lambda c:c['chains'][cid]['levels'][bid]['gates'].update(can_construct='{'),
                   lambda c:c['chains'][cid]['levels'][bid]['provenance'].update(sha256='invalid'),
                   lambda c:c['chains'][cid].update(catalogue_geography='silently changed')]
        for mutate in mutations:
            contract=copy.deepcopy(self.contract);mutate(contract)
            with self.assertRaises(ContractError):g.compile_buildings(self.data,contract)

if __name__=='__main__':unittest.main()
