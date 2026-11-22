"""Execute generated route selection; no native-engine certification implied."""
import copy
import itertools
import unittest
from decimal import Decimal as D
from test_aawc_stage5_native_packet import PacketVM, rows


class RoutingTests(unittest.TestCase):
    def setup_packet(self, war=0):
        vm = PacketVM(rows({'a':'.6', 'b':'.4'}))
        vm.packet['source_war'] = D(war)
        for axis in ('culture', 'faith'):
            vm.packet[axis+'_rows'][0]['quantity'] = D(100)
        vm.packet['route_candidates'] = []
        return vm

    def candidate(self, vm, pid=1, war=0, match='culture', adjacent=1, capacity=100, rating=0):
        c = dict(province_id=D(pid), war=D(war), adjacent=D(adjacent),
                 receive_capacity=D(capacity), rating_delta=D(rating), destination={'id':pid})
        for axis in ('culture', 'faith'):
            identity = vm.packet[axis+'_rows'][0]['identity'] if match in (axis, 'both') else {'key':'other'}
            c[axis+'_rows'] = [dict(identity=identity, original_factor=D(1))]
        vm.packet['route_candidates'].append(c)
        return c

    def test_peace_requires_adjacency_capacity_and_either_axis(self):
        for axis in ('culture', 'faith', 'both'):
            vm=self.setup_packet(); c=self.candidate(vm,match=axis)
            vm.call('select_route'); self.assertIs(vm.packet['destination'], c['destination'])
        for kwargs in ({'adjacent':0}, {'capacity':99}, {'match':None}, {'war':1}):
            vm=self.setup_packet(); self.candidate(vm,**kwargs)
            vm.call('select_route'); self.assertNotIn('route_prepared',vm.packet)
            self.assertNotIn('destination',vm.packet)
            self.assertEqual(vm.writes,[])
            self.assertEqual(vm.packet['source_population'],1000)

    def test_zero_factor_or_zero_packet_quantity_is_not_shared_identity(self):
        for target in ('factor', 'quantity'):
            vm=self.setup_packet(); c=self.candidate(vm)
            if target=='factor': c['culture_rows'][0]['original_factor']=D(0)
            else: vm.packet['culture_rows'][0]['quantity']=D(0)
            vm.call('select_route'); self.assertNotIn('route_prepared',vm.packet)

    def test_subthreshold_factor_cannot_unlock_peaceful_destination(self):
        vm=self.setup_packet(); c=self.candidate(vm)
        c['culture_rows'][0]['original_factor']=D('.00499')
        vm.call('select_route'); self.assertNotIn('route_prepared',vm.packet)

    def test_all_war_tiers_ordered_before_rating(self):
        for available in range(4):
            for order in itertools.permutations(range(available,4)):
                vm=self.setup_packet(war=1)
                for i in order:
                    self.candidate(vm,pid=i+1,war=int(i>=2),match='faith' if i%2==0 else None,rating=100*i)
                vm.call('select_route')
                self.assertEqual(vm.packet['destination']['id'],available+1)
                self.assertEqual(vm.packet['selected_candidate']['tier'],available+1)

    def test_rating_then_capacity_then_province_id(self):
        for order in itertools.permutations(range(4)):
            vm=self.setup_packet()
            specs=[(1,0,200),(2,1,100),(3,1,101),(4,1,101)]
            for i in order:
                pid,rating,capacity=specs[i]
                self.candidate(vm,pid=pid,rating=rating,capacity=capacity)
            vm.call('select_route'); self.assertEqual(vm.packet['destination']['id'],3)

    def test_restored_receipt_is_immutable_and_no_authority_writes(self):
        vm=self.setup_packet(); self.candidate(vm)
        vm.call('select_route')
        vm.packet=copy.deepcopy(vm.packet); vm.scopes={'aawc_stage5_packet':vm.packet}
        self.candidate(vm,pid=2,rating=999)
        before=copy.deepcopy(vm.packet)
        vm.call('select_route')
        self.assertEqual(vm.packet,before); self.assertEqual(vm.writes,[])

    def test_invalid_or_sealed_packet_cannot_route(self):
        for field in ('phase','invalid'):
            vm=self.setup_packet(); self.candidate(vm); vm.packet[field]=D(1)
            before=copy.deepcopy(vm.packet); vm.call('select_route')
            self.assertEqual(vm.packet,before)


if __name__=='__main__': unittest.main()
