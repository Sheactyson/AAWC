"""Execute emitted weighted allocation, independently checked against oracle."""
import copy
import random
import unittest
from decimal import Decimal as D
from aawc_stage5_identity_reference import departure
from test_aawc_stage5_native_packet import PacketVM, rows


class DepartureTests(unittest.TestCase):
    def allocate(self, shares, population, amount, owner=None, carries=None, axis='culture'):
        vm = PacketVM(rows({k:str(D(v)/100000) for k,v in shares.items()}), amount, population)
        rs = vm.packet[axis+'_rows']
        if owner is not None:
            vm.packet['owner_'+axis] = next(r['identity'] for r in rs if r['identity']['key']==owner)
        for r in rs:
            r['departure_carry'] = D((carries or {}).get(r['identity']['key'], 0))
        vm.call('weight_departures', {'TYPE':axis})
        return vm, {r['identity']['key']:int(r['quantity']) for r in rs}

    def test_owner_faith_pressure_and_neutral(self):
        for axis in ('culture', 'faith'):
            vm, result = self.allocate({'a':50000,'b':50000},1000,100,'a',axis=axis)
            self.assertEqual(result, {'a':20,'b':80})
            self.assertEqual(vm.writes, [])
            self.assertEqual(vm.packet['source_population'],1000)
        _, neutral = self.allocate({'a':50000,'b':50000},1000,100)
        self.assertEqual(neutral, {'a':50,'b':50})

    def test_capped_weighted_vectors_match_oracle(self):
        rng = random.Random(55)
        for _ in range(50):
            a = rng.randint(1,99999)
            shares = {'a':a, 'b':100000-a}
            amount = rng.randint(1,998)
            vm, actual = self.allocate(shares,1000,amount,'a')
            expected, _ = departure(shares,1000,amount,'a')
            self.assertEqual(actual,expected)
            self.assertEqual(vm.packet['invalid'],0)

    def test_signed_carries_and_stable_tie(self):
        for carries in ({'a':'-0.7','b':'0.7'},{'a':'0.7','b':'-0.7'},{}):
            vm, actual = self.allocate({'a':50000,'b':50000},1000,1,carries=carries)
            expected, _ = departure({'a':50000,'b':50000},1000,1,residuals=carries)
            self.assertEqual(actual,expected)
        vm = PacketVM(list(reversed(rows({'a':'.5','b':'.5'}))),1)
        vm.call('weight_departures',{'TYPE':'culture'})
        self.assertEqual({r['identity']['key']:r['quantity'] for r in vm.packet['culture_rows']},{'a':1,'b':0})

    def test_retry_restored_graph_and_explicit_preservation(self):
        vm,_ = self.allocate({'a':60000,'b':40000},1000,53,'a')
        vm.packet = copy.deepcopy(vm.packet)
        vm.scopes={'aawc_stage5_packet':vm.packet}
        before=copy.deepcopy(vm.packet)
        vm.call('weight_departures',{'TYPE':'culture'})
        vm.call('resolve_missing_axis',{'TYPE':'culture'})
        self.assertEqual(vm.packet,before)
        explicit=PacketVM(rows({'a':'.5','b':'.5'}))
        explicit.packet['culture_explicit']=D(1)
        explicit.packet['culture_rows'][0]['quantity']=D(100)
        before=copy.deepcopy(explicit.packet)
        explicit.call('weight_departures',{'TYPE':'culture'})
        self.assertEqual(explicit.packet,before)

    def test_insufficient_capacity_fails_closed(self):
        vm,_=self.allocate({'a':50000,'b':50000},3,3)
        self.assertEqual(vm.packet['invalid'],1)
        self.assertNotIn('culture_weighted',vm.packet)
        self.assertEqual(vm.writes,[])


if __name__=='__main__': unittest.main()
