"""Execute native proposal assembly through actual cohort transfer adapters."""
import copy
import itertools
import json
import unittest
from decimal import Decimal as D

from generate_aawc_stage5_runtime import build, render_runtime
from generate_aawc_stage5_registry import build as registry_build, render_registry, INVENTORY
from test_aawc_stage5_transactions import TransactionVM, bands
from test_aawc_stage5_native_packet import PacketVM
from test_aawc_cohort_bounded_arithmetic import SourceVM, parse
from generate_aawc_stage5_guards import cafg_artifacts, CORE_NAMES, EFFECTS
from validate_aawc_reforging_stage1_cohort_engine import definition_body


class RuntimeVM(TransactionVM):
    def __init__(self):
        super().__init__()
        self.text += '\n' + render_runtime()
        self.globals['aawc_stage5_migration_batch'] = D(1)
        self.source.pop('aawc_stage5_packet')
        self.source['barony'] = {'holder': {axis:self.packet[axis+'_rows'][0]['identity'] for axis in ('culture','faith')}}
        for pid, holding in enumerate((self.source, self.destination), 1):
            holding['aawc_stage5_province_id'] = D(pid)
            holding['county'].update(aawc_migration_county_rating=D(pid*5),aawc_migration_county_actual_net=D(0))
            holding['neighbors'] = [self.destination] if pid == 1 else [self.source]
            for kind in ('county','internal'):
                holding['aawc_migration_holding_'+kind+'_give_cap'] = D(100 if pid==1 and kind=='county' else 0)
                holding['aawc_migration_holding_'+kind+'_receive_cap'] = D(200 if pid==2 and kind=='county' else 0)
                holding['aawc_reforging_tx_migration_'+kind+'_plan'] = D(0)
            holding['aawc_reforging_tx_migration_plan'] = D(0)
            self.call('prepare_migration_node',cur=holding)

    def value(self, x, cur, prev):
        if x == 'county': return cur['county']
        if x == 'aawc_stage5_war_affected_trigger': return cur.get('war',False)
        if x == 'aawc_stage5_county_neighbor_trigger': return cur['county'] is not self.scopes['aawc_stage5_routing_source']['county']
        if x == 'aawc_stage5_internal_neighbor_trigger': return cur['county'] is self.scopes['aawc_stage5_routing_source']['county']
        return super().value(x,cur,prev)

    def external(self,k,v,cur,prev):
        if k == 'every_neighboring_province':
            limit = next(a for b,_,a in v if b=='limit')
            for neighbor in cur['neighbors']:
                if self.cond(limit,neighbor,cur):
                    self.run([n for n in v if n[0]!='limit'],neighbor,cur)
            return True
        if k == 'county':
            self.run(v,cur['county'],cur); return True
        return super().external(k,v,cur,prev)

    def cond(self,nodes,cur,prev):
        if len(nodes)==1 and nodes[0][0]=='is_target_in_variable_list':
            args={k:v for k,_,v in nodes[0][2]}
            return any(item is self.value(args['target'],cur,prev) for item in cur.get(args['name'],[]))
        return super().cond(nodes,cur,prev)

    def route(self,kind='county'):
        self.call('route_migration_source',{'KIND':kind},cur=self.source)

    def neighbor(self,pid,capacity=100,match=True,war=False):
        result=self.holding(500)
        result.update(aawc_stage5_province_id=D(pid),war=war)
        result['county'].update(aawc_migration_county_rating=D(pid*5),aawc_migration_county_actual_net=D(0))
        for axis in ('culture','faith'):
            ident=self.packet[axis+'_rows'][0]['identity'] if match else {'key':'unrelated_'+axis,'aawc_stage5_identity_rank':D(100)}
            result['kCAFG_province_'+axis+'_structs']=[{axis:ident,'factor':D(1)}]
        result['aawc_reforging_tx_migration_plan']=D(0)
        for kind in ('county','internal'):
            result['aawc_migration_holding_'+kind+'_give_cap']=D(0)
            result['aawc_migration_holding_'+kind+'_receive_cap']=D(capacity)
            result['aawc_reforging_tx_migration_'+kind+'_plan']=D(0)
        self.call('prepare_migration_node',cur=result)
        return result


class RuntimeTests(unittest.TestCase):
    def test_generated_native_artifacts_are_current(self):
        for path,text in {**build(),**registry_build()}.items():
            self.assertEqual(path.read_text(encoding='utf-8-sig'),text,str(path))
            self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'), str(path))

    def test_registry_static_keys_are_unique_and_canonical(self):
        data=json.loads(INVENTORY.read_text())
        for key in ('culture','faith','religions','provinces'):
            self.assertEqual(data[key],sorted(set(data[key])))
        self.assertTrue({4485,4486}.issubset(data['provinces']))
        self.assertIn('andal',data['culture'])
        self.assertIn('fots_seven',data['faith'])

    def test_native_candidate_assembly_executes_and_accounts_once(self):
        vm=RuntimeVM(); before=tuple(a+b for a,b in zip(bands(vm.source),bands(vm.destination)))
        vm.route()
        self.assertEqual(vm.source['aawc_population_current'],900)
        self.assertEqual(vm.destination['aawc_population_current'],600)
        self.assertEqual(vm.source['aawc_stage5_county_send_remaining'],0)
        self.assertEqual(vm.destination['aawc_stage5_county_receive_remaining'],100)
        self.assertEqual(vm.source['county']['aawc_migration_county_actual_net'],-100)
        self.assertEqual(vm.destination['county']['aawc_migration_county_actual_net'],100)
        # Real province ownership requires the barony link. A direct .holder
        # link silently made the native snapshot ownerless (neutral weighting).
        for axis in ('culture', 'faith'):
            self.assertEqual([row['factor'] for row in vm.source['kCAFG_province_'+axis+'_structs']], [D('.63667'), D('.36333')])
        self.assertNotIn('aawc_stage5_packet',vm.source)
        self.assertEqual(tuple(a+b for a,b in zip(bands(vm.source),bands(vm.destination))),before)
        vm.route()
        self.assertEqual(len(vm.absolute_calls),2)

    def test_no_route_preserves_budgets_carries_and_both_factor_surfaces(self):
        for mismatch in ('war','identity','nonadjacent','lock'):
            vm=RuntimeVM()
            if mismatch=='war':vm.destination['war']=True
            elif mismatch=='identity':
                for axis in ('culture','faith'):
                    vm.destination['kCAFG_province_'+axis+'_structs']=[{axis:{'key':'other'},'factor':D(1)}]
            elif mismatch=='nonadjacent':vm.source['neighbors']=[]
            else:vm.destination['aawc_stage5_identity_lock']={}
            snapshot=lambda: [{k:v for k,v in p.items() if k!='neighbors'} for p in (vm.source,vm.destination)]
            before=copy.deepcopy(snapshot())
            vm.route()
            # Draft stories are ephemeral; no source/destination variables survive.
            self.assertEqual(snapshot(),before)
            self.assertEqual(vm.absolute_calls,[])
            self.assertEqual(vm.writes,[])

    def test_small_safe_capacity_precedes_large_war_destination(self):
        vm=RuntimeVM(); vm.source['war']=True
        safe=vm.neighbor(3,capacity=13); war=vm.neighbor(4,capacity=100,war=True)
        vm.source['neighbors']=[war,safe]
        vm.route()
        self.assertEqual(safe['aawc_population_current'],513)
        self.assertEqual(war['aawc_population_current'],500)
        self.assertEqual(vm.source['aawc_stage5_county_send_remaining'],87)

    def test_proposal_order_and_war_tiers_are_independent_of_neighbor_iteration(self):
        for order in ((1,2,3,4),(4,3,2,1),(3,1,4,2)):
            vm=RuntimeVM(); vm.source['war']=True
            candidates={pid:vm.neighbor(pid+2,match=pid%2==1,war=pid>2) for pid in range(1,5)}
            vm.source['neighbors']=[candidates[n] for n in order]
            vm.route()
            self.assertEqual(candidates[1]['aawc_population_current'],600)
            self.assertEqual(sum(p['aawc_population_current'] for p in candidates.values()),2100)

    def test_internal_budget_never_crosses_a_county_boundary(self):
        vm=RuntimeVM()
        vm.source['aawc_stage5_internal_send_remaining']=D(50)
        vm.destination['aawc_stage5_internal_receive_remaining']=D(50)
        vm.route('internal');self.assertEqual(vm.absolute_calls,[])
        vm.destination['county']=vm.source['county']
        vm.route('internal')
        self.assertEqual(vm.source['aawc_population_current'],950)
        self.assertEqual(vm.destination['aawc_population_current'],550)
        self.assertEqual(vm.source['county']['aawc_migration_county_actual_net'],0)
        self.assertEqual(len(vm.globals['aawc_stage5_changed_counties']),1)

    def test_missing_identity_registry_key_fails_before_physical_debit(self):
        vm=RuntimeVM()
        vm.packet['culture_rows'][0]['identity'].pop('aawc_stage5_identity_rank')
        vm.route()
        self.assertEqual(vm.absolute_calls,[])
        self.assertEqual(vm.source['aawc_stage5_county_send_remaining'],100)

    def test_production_entry_uses_routes_before_county_cache_commit(self):
        text=(EFFECTS/'zzzz_aawc_population_migration_effects.txt').read_text(encoding='utf-8-sig')
        pair=definition_body(text,'aawc_migration_pair_adjacent_county_effect')
        internal=definition_body(text,'aawc_migration_commit_county_movement_effect')
        world=definition_body(text,'aawc_migration_update_world_effect')
        self.assertIn('aawc_stage5_route_migration_source_effect = { KIND = county }',pair)
        self.assertIn('aawc_stage5_route_migration_source_effect = { KIND = internal }',internal)
        self.assertNotIn('aawc_migration_commit_internal_population_effect',internal)
        self.assertNotIn('aawc_migration_transfer_to_scoped_target_effect',pair)
        self.assertLess(world.index('aawc_stage5_recover_pending_effect'),world.index('every_county'))
        self.assertGreater(world.index('aawc_stage5_flush_counties_effect'),world.index('aawc_migration_commit_county_movement_effect'))

    def test_locked_demography_defers_without_identity_or_age_changes(self):
        vm=SourceVM();vm.initialize(1000)
        vm.vars['aawc_stage5_identity_lock']=41
        before=dict(vm.vars)
        vm.call('aawc_reforging_cohort_apply_production_month_effect')
        self.assertEqual(vm.vars,before)
        vm.vars['aawc_reforging_cohort_last_transfer_debit']=2000000
        vm.call('aawc_reforging_cohort_debit_population_effect',AMOUNT=20)
        self.assertEqual(vm.vars['aawc_reforging_cohort_last_transfer_debit'],0)
        self.assertEqual(vm.vars['aawc_population_current'],before['aawc_population_current'])

    def test_sparse_county_refresh_accepts_missing_optional_loaded_caches(self):
        class CacheVM(PacketVM):
            def value(self, x, cur, prev):
                if isinstance(x, str):
                    if x == 'has_holding': return cur.get('holding', False)
                    if x == 'yes': return True
                    if x == 'prev.aawc_population_holding_current_readonly': return prev['aawc_population_current']
                    if x == 'aawc_migration_county_building_rating_average':
                        n = cur['aawc_migration_county_rated_holding_count']
                        return cur['aawc_migration_county_building_rating_sum'] / n if n else D(0)
                return super().value(x, cur, prev)
            def external(self, k, v, cur, prev):
                if k == 'every_in_de_jure_hierarchy':
                    for title in cur['baronies']:
                        self.run([n for n in v if n[0] != 'limit'], title, cur)
                    return True
                if k == 'title_province':
                    self.run(v, cur['province'], cur); return True
                if k == 'aawc_stage4_refresh_colonization_costs_effect': return True
                return False
        a = dict(holding=True, aawc_population_current=D(900))
        b = dict(holding=True, aawc_population_current=D(600), aawc_population_expected=D(1000),
                 aawc_population_debug_main_capacity=D(12), aawc_population_debug_building_capacity=D(8),
                 aawc_population_debug_growth_rating=D(3), aawc_migration_holding_building_rating_eligible=D(1),
                 aawc_migration_holding_building_rating=D(7))
        county = {'baronies':[{'province':a},{'province':b}]}
        before = copy.deepcopy((a,b))
        text = (EFFECTS/'aawc_population_effects.txt').read_text(encoding='utf-8-sig')
        vm = CacheVM([])
        vm.run(parse(definition_body(text,'aawc_population_reaggregate_county_cached_effect')),county,None)
        self.assertEqual((a,b),before)
        self.assertEqual(county['aawc_population_total'],1500)
        self.assertEqual(county['aawc_population_expected'],1000)
        self.assertEqual(county['aawc_population_county_dev_weight'],12)
        self.assertEqual(county['aawc_population_county_income_component'],8)
        self.assertEqual(county['aawc_population_county_levy_component'],3)
        self.assertEqual(county['aawc_migration_county_building_rating'],7)

    def test_real_cafg_setter_obeys_exact_packet_lock(self):
        vm=RuntimeVM(); identity=vm.packet['culture_rows'][0]['identity']
        vm.source['kCAFG_province_cultures']=[r['culture'] for r in vm.source['kCAFG_province_culture_structs']]
        vm.scopes['test_identity']=identity
        owner={}; vm.source['aawc_stage5_identity_lock']=owner
        text=cafg_artifacts()[EFFECTS/'kei_cafg_province_struct_effects.txt']
        text=text.replace('$TYPE$','culture').replace('$SCOPE$','scope:test_identity').replace('$FACTOR$','0.3')
        setter={k:v for k,_,v in parse(text)}['E_kCAFG_set_struct_factor']
        for marker in (None,{}):
            if marker is None:vm.globals.pop('aawc_stage5_mutating_packet',None)
            else:vm.globals['aawc_stage5_mutating_packet']=marker
            vm.run(setter,vm.source,None)
            self.assertEqual(vm.source['kCAFG_province_culture_structs'][0]['factor'],D('.6'))
        vm.globals['aawc_stage5_mutating_packet']=owner
        vm.run(setter,vm.source,None)
        self.assertEqual(vm.source['kCAFG_province_culture_structs'][0]['factor'],D('.3'))

    def test_guard_overlays_match_dependency_and_cover_absolute_entrypoints(self):
        for path,text in cafg_artifacts().items():self.assertEqual(path.read_text(encoding='utf-8-sig'),text)
        text=(EFFECTS/'aawc_reforging_cohort_production_effects.txt').read_text(encoding='utf-8-sig')
        for key in CORE_NAMES:
            self.assertIn('aawc_stage5_mutation_allowed_trigger',definition_body(text,'aawc_reforging_cohort_'+key+'_effect'))

    def test_dynamic_keys_persist_and_do_not_depend_on_factor_order(self):
        vm=PacketVM([])
        vm.text+='\n'+render_registry(dict(culture=[],faith=[],provinces=[],religions=[]))
        a,b={},{}
        vm.call('register_dynamic_identity',{'TYPE':'culture'},cur=a)
        vm.call('register_dynamic_identity',{'TYPE':'culture'},cur=b)
        vm.globals,a,b=copy.deepcopy((vm.globals,a,b))
        vm.call('register_dynamic_identity',{'TYPE':'culture'},cur=b)
        vm.call('register_dynamic_identity',{'TYPE':'culture'},cur=a)
        self.assertEqual(a['aawc_stage5_identity_rank'],1000000)
        self.assertEqual(b['aawc_stage5_identity_rank'],1000001)
        self.assertEqual(vm.globals['aawc_stage5_next_culture_key'],1000002)


if __name__=='__main__':unittest.main()
