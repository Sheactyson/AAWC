"""Execute emitted identity coordination AND existing thirteen-band transfers.

The bounded VM executes the actual cohort capture/credit scripts. Native CK3
scope persistence and rendering still require the separately recorded live run.
"""
import copy
import operator
import random
import unittest
from decimal import Decimal as D

from generate_aawc_stage5_packets import MOD
from generate_aawc_stage4_transactions import BANDS
from test_aawc_stage5_native_packet import PacketVM, rows, fixed
from test_aawc_cohort_bounded_arithmetic import SourceVM, S, parse
from aawc_stage5_identity_reference import reconcile


class TransactionVM(PacketVM):
    def __init__(self):
        super().__init__(rows({'a': '.6', 'b': '.4'}))
        self.text += '\n' + (MOD / 'common/scripted_effects/aawc_reforging_cohort_production_effects.txt').read_text(encoding='utf-8-sig')
        self.absolute_calls = []
        self.refreshes = []
        self.source = self.holding(1000)
        self.destination = self.holding(500)
        self.packet.update(source=self.source, destination=self.destination, source_war=D(0))
        self.source['aawc_stage5_packet'] = self.packet
        for axis in ('culture', 'faith'):
            rs = self.packet[axis+'_rows']
            for r in rs: r['identity']['aawc_stage5_identity_rank'] = r['rank']
            self.source['kCAFG_province_'+axis+'_structs'] = [
                {axis:r['identity'], 'factor':r['original_factor']} for r in rs]
            self.destination['kCAFG_province_'+axis+'_structs'] = [
                {axis:rs[0]['identity'], 'factor':D('.2')},
                {axis:{'key':'c', 'aawc_stage5_identity_rank':D(3)}, 'factor':D('.8')}]
        self.packet['route_candidates'] = [dict(adjacent=D(1), receive_capacity=D(200), war=D(0),
            rating_delta=D(5), province_id=D(2), destination=self.destination,
            culture_rows=[dict(r) for r in self.packet['culture_rows']],
            faith_rows=[dict(r) for r in self.packet['faith_rows']])]

    def holding(self, population):
        core = SourceVM(); core.initialize(population)
        result = {k:D(v)/S for k,v in core.vars.items()}
        result.update(county={}, aawc_migration_holding_protective_floor=D(250), valid=True)
        return result

    def core(self, cur):
        if not hasattr(self, '_core'): self._core = SourceVM()
        vm = self._core
        vm.vars = {k:int(v*S) for k,v in cur.items() if isinstance(v,D)}
        vm.valid_settlement = cur.get('valid', True)
        return vm

    def value(self, x, cur, prev):
        if x == 'yes': return True
        if x == 'no': return False
        if x == 'aawc_stage5_mutation_allowed_trigger':
            return 'aawc_stage5_identity_lock' not in cur or cur['aawc_stage5_identity_lock'] is self.globals.get('aawc_stage5_mutating_packet')
        if x == 'aawc_population_valid_settlement_for_cohort_trigger': return cur.get('valid',True)
        if x == 'aawc_stage4_unreserved_civilian_total':
            return sum(max(D(0), cur['aawc_reforging_cohort_'+b] - cur.get('aawc_stage4_reserved_'+b,D(0)) -
                           (cur.get('aawc_reforging_'+m,D(0)) if m else 0)) for b,m in BANDS)
        if isinstance(x,str) and x.startswith('aawc_reforging_'):
            vm = self.core(cur)
            if x in vm.values: return D(vm.value(vm.values[x]))/S
        return super().value(x,cur,prev)

    def external(self, k, v, cur, prev):
        if k == 'end_story':
            cur['_ended'] = True; return True
        if k.startswith('E_kCAFG_update_county_'):
            self.refreshes.append((cur,k)); return True
        if k in ('aawc_population_reaggregate_county_cached_effect','aawc_population_reaggregate_character_cached_effect'):
            return True  # read-only aggregate cache refresh, not the transfer oracle
        if k == 'holder':
            if 'holder' in cur:self.run(v,cur['holder'],cur)
            return True
        if k.startswith('aawc_reforging_cohort_'):
            if 'transfer_' in k:
                if k in ('aawc_reforging_cohort_capture_transfer_packet_effect','aawc_reforging_cohort_apply_transfer_packet_effect'):
                    self.absolute_calls.append((k,cur))
                text = self.text
                if isinstance(v,list):
                    for a,_,b in v: text = text.replace('$'+a+'$',b)
                self.run({a:b for a,_,b in parse(text)}[k],cur,prev)
            else:
                vm = self.core(cur); before = set(vm.vars)
                vm.call(k)
                for name in before-set(vm.vars): cur.pop(name,None)
                cur.update({name:D(val)/S for name,val in vm.vars.items()})
            return True
        return False

    def write_factor(self,cur,axis,identity,factor):
        super().write_factor(cur,axis,identity,factor)
        structs = cur.setdefault('kCAFG_province_'+axis+'_structs',[])
        found = [s for s in structs if s[axis] is identity]
        if factor == 0: structs[:] = [s for s in structs if s[axis] is not identity]
        elif found:
            for s in found: s['factor'] = factor
        else: structs.append({axis:identity, 'factor':factor})

    def prepare(self, ordinary='1'):
        self.call('prepare_identity_route',{'ORDINARY':ordinary})

    def reload(self):
        # One graph copy preserves reference identity. This is persistence-model
        # regression, not a claim about CK3 serialization.
        self.packet, self.globals = copy.deepcopy((self.packet,self.globals))
        self.source, self.destination = self.packet['source'], self.packet['destination']
        self.scopes = {}
        self.steps = 0


def bands(holding):
    return tuple(holding['aawc_reforging_cohort_'+b] for b,_ in BANDS)


class TransactionTests(unittest.TestCase):
    def assert_normalized(self, vm):
        for holding in (vm.source, vm.destination):
            for axis in ('culture','faith'):
                self.assertEqual(sum(s['factor'] for s in holding['kCAFG_province_'+axis+'_structs']),1)

    def test_real_age_packet_and_marginal_execution_conserve(self):
        vm=TransactionVM(); before=tuple(a+b for a,b in zip(bands(vm.source),bands(vm.destination)))
        vm.prepare(); vm.call('execute_transaction')
        self.assertEqual(vm.packet['phase'],5)
        self.assertEqual(vm.source['aawc_population_current'],900)
        self.assertEqual(vm.destination['aawc_population_current'],600)
        self.assertEqual(tuple(a+b for a,b in zip(bands(vm.source),bands(vm.destination))),before)
        for axis in ('culture','faith'):
            self.assertEqual(sum(r['quantity'] for r in vm.packet[axis+'_rows']),100)
            self.assertEqual(sum(r['quantity'] for r in vm.packet['destination_'+axis+'_rows']),100)
        self.assert_normalized(vm)
        self.assertEqual(len(vm.absolute_calls),2)
        self.assertNotIn('aawc_stage5_identity_lock',vm.source)
        self.assertNotIn('aawc_stage5_identity_lock',vm.destination)

    def test_all_persisted_boundaries_resume_once(self):
        for stop in ('reserve_transaction','commit_absolute_source','apply_source_debit',
                     'commit_absolute_destination','apply_destination_credit','finish_transaction'):
            with self.subTest(stop=stop):
                vm=TransactionVM(); vm.prepare()
                sequence=['reserve_transaction','commit_absolute_source','apply_source_debit',
                          'commit_absolute_destination','apply_destination_credit','finish_transaction']
                for step in sequence[:sequence.index(stop)+1]: vm.call(step)
                vm.reload(); vm.call('execute_transaction'); vm.call('execute_transaction')
                self.assertEqual(vm.packet['phase'],5)
                self.assertEqual(vm.source['aawc_population_current']+vm.destination['aawc_population_current'],1500)
                self.assertEqual(len(vm.absolute_calls),2)
                self.assert_normalized(vm)

    def test_abort_refund_restores_bands_and_factors_once(self):
        for stop in ('apply_source_debit','commit_absolute_refund','apply_refund'):
            vm=TransactionVM(); before=bands(vm.source)
            vm.prepare(); vm.call('reserve_transaction'); vm.call('commit_absolute_source'); vm.call('apply_source_debit')
            vm.packet['abort_requested']=D(1)
            if stop != 'apply_source_debit': vm.call('commit_absolute_refund')
            if stop == 'apply_refund': vm.call('apply_refund')
            vm.reload(); vm.call('execute_transaction'); vm.call('execute_transaction')
            self.assertEqual(vm.packet['phase'],7)
            self.assertEqual(bands(vm.source),before)
            self.assertEqual(vm.destination['aawc_population_current'],500)
            self.assertEqual([s['factor'] for s in vm.source['kCAFG_province_culture_structs']],[D('.6'),D('.4')])
            self.assertEqual(len(vm.absolute_calls),2)

    def test_source_stale_duplicate_or_locked_fails_before_debit(self):
        for kind in ('factor','extra','duplicate','population','floor','reserved','lock'):
            vm=TransactionVM(); vm.prepare()
            source=vm.source; structs=source['kCAFG_province_culture_structs']
            if kind=='factor': structs[0]['factor']=D('.7')
            elif kind=='extra': structs.append({'culture':{'key':'x'},'factor':D(0)})
            elif kind=='duplicate': structs.append(dict(structs[0]))
            elif kind=='population': source['aawc_population_current']=D(1001)
            elif kind=='floor': source['aawc_migration_holding_protective_floor']=D(950)
            elif kind=='reserved':
                for b,_ in BANDS: source['aawc_stage4_reserved_'+b]=source['aawc_reforging_cohort_'+b]
            else: source['aawc_stage5_identity_lock']={'other':True}
            before=bands(source); vm.call('execute_transaction')
            self.assertEqual(bands(source),before,kind)
            self.assertEqual(vm.absolute_calls,[],kind)
            self.assertEqual(vm.writes,[],kind)

    def test_bad_destination_rejected_before_source_debit(self):
        for kind in ('duplicate','sum','rank','negative','invalid'):
            vm=TransactionVM(); vm.prepare()
            structs=vm.destination['kCAFG_province_culture_structs']
            if kind=='duplicate': structs.append(dict(structs[0]))
            elif kind=='sum': structs[0]['factor']=D('.1')
            elif kind=='rank': del structs[1]['culture']['aawc_stage5_identity_rank']
            elif kind=='negative': structs[1]['factor']=D(-1)
            else: vm.destination['valid']=False
            vm.call('execute_transaction')
            self.assertEqual(vm.absolute_calls,[],kind)
            self.assertEqual(vm.writes,[],kind)

    def test_destination_changes_after_debit_refund_instead_of_overwrite(self):
        vm=TransactionVM(); vm.prepare(); vm.call('reserve_transaction'); vm.call('commit_absolute_source'); vm.call('apply_source_debit')
        vm.destination['kCAFG_province_faith_structs'][0]['factor']=D('.1')
        vm.call('execute_transaction')
        self.assertEqual(vm.packet['phase'],7)
        self.assertEqual(vm.source['aawc_population_current'],1000)
        self.assertEqual(vm.destination['kCAFG_province_faith_structs'][0]['factor'],D('.1'))

    def test_pending_recovery_uses_persistent_sparse_list(self):
        vm=TransactionVM(); vm.prepare(); vm.call('reserve_transaction'); vm.call('commit_absolute_source')
        vm.reload(); vm.call('recover_pending',cur={}); vm.call('recover_pending',cur={})
        self.assertEqual(vm.packet['phase'],5)
        self.assertEqual(vm.globals['aawc_stage5_pending_packets'],[])
        self.assertEqual(len(vm.absolute_calls),2)

    def test_same_county_is_refreshed_once_per_axis_per_batch(self):
        vm=TransactionVM(); vm.destination['county']=vm.source['county']
        vm.prepare(); vm.call('execute_transaction')
        county=vm.source['county']
        vm.call('queue_county',cur=county)
        self.assertEqual(len(vm.globals['aawc_stage5_changed_counties']),1)
        vm.call('flush_counties',cur={}); vm.call('flush_counties',cur={})
        self.assertEqual(len(vm.refreshes),4)  # list + majority, each axis
        self.assertNotIn('aawc_stage5_refresh_queued',county)

    def test_known_and_missing_axes_survive_physical_transaction(self):
        vm=TransactionVM(); vm.packet['culture_explicit']=D(1)
        vm.packet['culture_rows'][1]['quantity']=D(100)
        vm.prepare('0'); vm.call('execute_transaction')
        self.assertEqual(vm.packet['phase'],5)
        self.assertEqual(vm.packet['faith_fallback']['key'],'a')
        self.assertEqual(vm.packet['culture_rows'][1]['quantity'],100)
        self.assert_normalized(vm)

    def test_demographic_tick_does_not_touch_identity_surfaces(self):
        vm=TransactionVM()
        for step in range(1,4):
            identities={k:copy.deepcopy(v) for k,v in vm.source.items() if k.startswith('kCAFG')}
            core=vm.core(vm.source); core.tick(step)
            vm.source.update({k:D(v)/S for k,v in core.vars.items()})
            self.assertEqual({k:v for k,v in vm.source.items() if k.startswith('kCAFG')},identities)
        text=(MOD/'common/scripted_effects/aawc_reforging_cohort_production_effects.txt').read_text(encoding='utf-8-sig')
        # Entry guards may defer a locked endpoint; they cannot reconcile any
        # identity during births/deaths/aging themselves.
        self.assertNotIn('aawc_stage5_',text.replace('aawc_stage5_mutation_allowed_trigger',''))
        self.assertNotIn('E_kCAFG_',text)

    def test_weighted_transactions_match_normalization_oracle(self):
        rng=random.Random(118)
        for _ in range(8):
            vm=TransactionVM()
            vm.packet['amount']=D(rng.randint(1,200))
            for axis in ('culture','faith'):
                vm.packet['owner_'+axis]=vm.packet[axis+'_rows'][0]['identity']
            vm.prepare(); vm.call('execute_transaction')
            self.assertEqual(vm.packet['phase'],5)
            for axis in ('culture','faith'):
                q={r['identity']['key']:int(r['quantity']) for r in vm.packet[axis+'_rows']}
                expected_source=reconcile({'a':60000,'b':40000},1000,q,debit=True)
                expected_dest=reconcile({'a':20000,'c':80000},500,q)
                actual=lambda h:{s[axis]['key']:int(s['factor']*100000) for s in h['kCAFG_province_'+axis+'_structs']}
                self.assertEqual(actual(vm.source),{k:v for k,v in expected_source.items() if v})
                self.assertEqual(actual(vm.destination),{k:v for k,v in expected_dest.items() if v})

    def test_cleanup_keeps_inflight_payload_and_removes_terminal_children(self):
        vm=TransactionVM(); vm.prepare(); vm.call('reserve_transaction'); vm.call('commit_absolute_source')
        vm.call('cleanup_packet',cur=vm.source)
        self.assertIs(vm.source['aawc_stage5_packet'],vm.packet)
        vm.call('execute_transaction'); vm.call('cleanup_packet',cur=vm.source)
        self.assertNotIn('aawc_stage5_packet',vm.source)
        self.assertTrue(vm.packet['_ended'])
        for key in ('culture_rows','faith_rows','destination_culture_rows','destination_faith_rows','route_candidates'):
            self.assertTrue(all(row['_ended'] for row in vm.packet[key]))
        self.assertNotIn('aawc_stage5_identity_lock',vm.source)

    def test_no_route_and_invalid_provenance_make_no_absolute_calls(self):
        for bad in ('no_route','unknown','overdraw'):
            vm=TransactionVM()
            if bad=='no_route': vm.packet['route_candidates']=[]
            elif bad=='unknown':
                vm.scopes['absent']={'key':'unknown'}
                vm.call('set_packet_quantity',{'TYPE':'culture','IDENTITY':'scope:absent','QUANTITY':'100'})
            else:
                vm.packet['culture_explicit']=D(1); vm.packet['culture_rows'][0]['quantity']=D(1001)
            before=bands(vm.source); vm.prepare(); vm.call('execute_transaction')
            self.assertEqual(vm.absolute_calls,[])
            self.assertEqual(vm.writes,[])
            self.assertEqual(vm.globals,{})
            self.assertEqual(bands(vm.source),before)

    def test_factor_drift_at_absolute_receipt_is_not_silently_overwritten(self):
        vm=TransactionVM(); vm.prepare(); vm.call('reserve_transaction'); vm.call('commit_absolute_source')
        vm.source['kCAFG_province_culture_structs'][0]['factor']=D('.7')
        vm.reload(); vm.call('execute_transaction')
        self.assertEqual(vm.packet['phase'],2)
        self.assertEqual(vm.writes,[])
        self.assertEqual(len(vm.absolute_calls),1)
        self.assertEqual(len(vm.globals['aawc_stage5_pending_packets']),1)
        # Repair the contradictory external write, then the same receipt resumes.
        vm.source['kCAFG_province_culture_structs'][0]['factor']=D('.6')
        vm.call('execute_transaction')
        self.assertEqual(vm.packet['phase'],5)


if __name__=='__main__': unittest.main()
