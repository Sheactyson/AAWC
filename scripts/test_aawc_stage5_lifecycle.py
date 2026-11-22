"""Execute preparation/commit lifecycle; native serialization is a separate gate."""
import copy
import unittest
from decimal import Decimal as D
from test_aawc_stage5_native_packet import PacketVM, rows


class LifecycleTests(unittest.TestCase):
    def fixture(self):
        vm = PacketVM(rows({'a': '.7', 'b': '.3'}))
        vm.packet.update(source={'aawc_population_current': D(1000)}, source_war=D(0))
        candidate = dict(adjacent=D(1), receive_capacity=D(200), war=D(0),
                         rating_delta=D(2), province_id=D(12), destination={})
        for axis in ('culture', 'faith'):
            candidate[axis+'_rows'] = [dict(r) for r in vm.packet[axis+'_rows']]
        vm.packet['route_candidates'] = [candidate]
        return vm

    def prepare(self, vm, ordinary='1'):
        vm.call('prepare_identity_route', {'ORDINARY': ordinary})

    def commit(self, vm):
        vm.packet['source']['aawc_population_current'] = D(900)
        vm.packet['phase'] = D(2)
        vm.call('apply_source_debit')

    def test_preparation_does_not_mutate_population_factors_or_carries(self):
        vm = self.fixture(); before = copy.deepcopy(vm.packet['source'])
        self.prepare(vm)
        self.assertEqual(vm.packet['phase'], 1)
        self.assertEqual(vm.packet['source_prepared'], 1)
        self.assertEqual(vm.packet['source'], before)
        self.assertEqual(vm.writes, [])

    def test_no_destination_preserves_source_and_does_not_seal(self):
        vm = self.fixture(); vm.packet['route_candidates'][0]['adjacent'] = D(0)
        before = copy.deepcopy(vm.packet['source'])
        self.prepare(vm); self.prepare(vm)
        self.assertEqual(vm.packet['phase'], 0)
        self.assertNotIn('source_prepared', vm.packet)
        self.assertEqual(vm.packet['source'], before)
        self.assertEqual(vm.writes, [])

    def test_known_culture_independent_faith_fallback(self):
        vm = self.fixture()
        vm.packet['culture_explicit'] = D(1)
        vm.packet['culture_rows'][1]['quantity'] = D(100)
        self.prepare(vm, '0')
        self.assertEqual(vm.packet['phase'], 1)
        self.assertEqual(vm.packet['culture_rows'][1]['quantity'], 100)
        self.assertEqual(vm.packet['faith_fallback']['key'], 'a')
        self.commit(vm)
        self.assertNotIn('aawc_stage5_culture_carries', vm.packet['source'])
        self.assertNotIn('aawc_stage5_faith_carries', vm.packet['source'])

    def test_commit_updates_existing_and_creates_missing_carries_once(self):
        vm = self.fixture(); first = vm.packet['culture_rows'][0]
        old = dict(identity=first['identity'], value=D('.25'))
        vm.packet['source']['aawc_stage5_culture_carries'] = [old]
        first['departure_carry'] = D('.25')
        self.prepare(vm)
        vm.call('apply_source_debit')  # no absolute receipt
        self.assertEqual(old['value'], D('.25'))
        self.commit(vm)
        for axis in ('culture', 'faith'):
            records = vm.packet['source']['aawc_stage5_'+axis+'_carries']
            self.assertEqual(len(records), 2)
            self.assertEqual([r['value'] for r in records],
                             [r['next_carry'] for r in vm.packet[axis+'_rows']])
        self.assertIs(vm.packet['source']['aawc_stage5_culture_carries'][0], old)
        before = copy.deepcopy(vm.packet)
        vm.packet = copy.deepcopy(vm.packet); vm.scopes = {'aawc_stage5_packet': vm.packet}
        vm.call('apply_source_debit'); self.prepare(vm)
        self.assertEqual(vm.packet, before)
        self.assertEqual(len(vm.writes), 4)
        self.assertEqual(vm.packet['source']['aawc_population_current'], 900)

    def test_invalid_or_mismatched_receipt_never_commits_carries(self):
        for invalid, population in ((1, 900), (0, 901)):
            vm = self.fixture(); self.prepare(vm)
            vm.packet.update(phase=D(2), invalid=D(invalid))
            vm.packet['source']['aawc_population_current'] = D(population)
            vm.call('apply_source_debit')
            self.assertEqual(vm.writes, [])
            self.assertNotIn('aawc_stage5_culture_carries', vm.packet['source'])

    def test_empty_axis_repair_is_written_only_at_commit(self):
        vm = self.fixture()
        vm.packet['faith_rows'] = [dict(identity={'key': 'f'}, rank=D(1),
                                      original_factor=D(1), quantity=D(0))]
        vm.packet['faith_repair'] = D(1)
        self.prepare(vm)
        self.assertEqual(vm.writes, [])
        self.commit(vm)
        self.assertEqual(len(vm.writes), 3)
        self.assertEqual(vm.writes[-1][1]['key'], 'f')
        self.assertEqual(vm.writes[-1][2], 1)


if __name__ == '__main__': unittest.main()
