"""Execute native source snapshot assembly; engine certification remains separate."""
import copy
import unittest
from decimal import Decimal as D
from test_aawc_stage5_native_packet import PacketVM

class SnapshotTests(unittest.TestCase):
    def fixture(self):
        a,b,f,g=({'key':x} for x in ('a','b','f','g'))
        source={'barony':{'holder':{'culture':a,'faith':g}}, 'county':{'culture':b,'faith':f},
                'kCAFG_province_culture_structs':[{'culture':a,'factor':D('.7')},{'culture':b,'factor':D('.3')}],
                'aawc_population_current':D(1000),
                'aawc_stage5_culture_carries':[{'identity':b,'value':D('-.4')}]}
        vm=PacketVM([])
        vm.packet.pop('culture_rows');vm.packet.pop('faith_rows')
        vm.packet['source']=source
        return vm,source

    def snapshot(self,vm,source,axis):
        vm.call('snapshot_axis',{'TYPE':axis},cur=source)

    def test_owner_factors_and_identity_keyed_carries(self):
        vm,source=self.fixture(); before=copy.deepcopy(source)
        self.snapshot(vm,source,'culture')
        self.assertEqual(vm.packet['owner_culture']['key'],'a')
        self.assertEqual([r['original_factor'] for r in vm.packet['culture_rows']],[D('.7'),D('.3')])
        self.assertEqual([r['departure_carry'] for r in vm.packet['culture_rows']],[0,D('-.4')])
        self.assertEqual(source,before);self.assertEqual(vm.writes,[])

    def test_independent_empty_axis_repair_uses_source_title_not_owner(self):
        vm,source=self.fixture()
        self.snapshot(vm,source,'culture');self.snapshot(vm,source,'faith')
        self.assertNotIn('culture_repair',vm.packet)
        self.assertEqual(vm.packet['faith_repair'],1)
        self.assertEqual(vm.packet['faith_rows'][0]['identity']['key'],'f')
        self.assertEqual(vm.packet['owner_faith']['key'],'g')
        self.assertEqual(vm.packet['faith_rows'][0]['original_factor'],1)
        self.assertEqual(vm.writes,[])

    def test_retry_after_graph_restore_does_not_read_mutated_source(self):
        vm,source=self.fixture()
        self.snapshot(vm,source,'culture');self.snapshot(vm,source,'faith')
        vm.packet=copy.deepcopy(vm.packet);vm.scopes={'aawc_stage5_packet':vm.packet}
        source=vm.packet['source']; source['barony']['holder']={};source['kCAFG_province_culture_structs']=[]
        source['aawc_stage5_culture_carries'][0]['value']=D('.9')
        before=copy.deepcopy(vm.packet)
        self.snapshot(vm,source,'culture');self.snapshot(vm,source,'faith')
        self.assertEqual(vm.packet,before)

    def test_missing_owner_is_neutral_and_missing_title_fails_closed(self):
        vm,source=self.fixture();source.pop('barony');source.pop('county')
        self.snapshot(vm,source,'culture');self.snapshot(vm,source,'faith')
        self.assertNotIn('owner_culture',vm.packet)
        self.assertNotIn('owner_faith',vm.packet)
        self.assertEqual(vm.packet['invalid'],1)
        self.assertNotIn('faith_repair',vm.packet)

    def test_duplicate_carry_records_fail_closed(self):
        vm,source=self.fixture()
        source['aawc_stage5_culture_carries']*=2
        self.snapshot(vm,source,'culture')
        self.assertEqual(vm.packet['invalid'],1)
        self.assertEqual(source['aawc_population_current'],1000)
        self.assertEqual(vm.writes,[])

if __name__=='__main__': unittest.main()
