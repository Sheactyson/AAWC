"""Execution coverage for emitted destination and refund helpers, not CK3."""
import copy
import unittest
from decimal import Decimal as D
from test_aawc_stage5_native_packet import PacketVM, rows
from aawc_stage5_identity_reference import reconcile


def fixture(population=1000):
    vm = PacketVM(rows({'a': '.6', 'b': '.4'}))
    for axis in ('culture', 'faith'):
        vm.packet[axis + '_rows'][0]['quantity'] = D(100)
    vm.packet['phase'] = D(1)
    vm.call('prepare_source_debit')
    vm.packet.update(phase=D(3), destination_population=D(population))
    vm.packet['source'] = {'aawc_population_current': D(900)}
    vm.packet['destination'] = {'aawc_population_current': D(population)}
    for axis in ('culture', 'faith'):
        source = vm.packet[axis + '_rows']
        vm.packet['source']['kCAFG_province_' + axis + '_structs'] = [
            {axis: r['identity'], 'factor': r['new_factor']} for r in source]
        # 'a' newly arrives at destination; destination-only 'c' retains mass.
        vm.packet['destination_' + axis + '_rows'] = [
            dict(identity=source[0]['identity'], rank=D(1), original_factor=D(0), quantity=D(100)),
            dict(identity={'key': 'c'}, rank=D(3), original_factor=D(1 if population else 0), quantity=D(0))]
    return vm


class SettlementTests(unittest.TestCase):
    def test_new_identity_credit_matches_oracle_and_conserves(self):
        vm = fixture()
        vm.call('prepare_destination_credit')
        self.assertEqual(vm.packet['destination_prepared'], 1)
        expected = reconcile({'c': 100000}, 1000, {'a': 100})
        for axis in ('culture', 'faith'):
            actual = {r['identity']['key']: int(r['units']) for r in vm.packet['destination_' + axis + '_rows']}
            self.assertEqual(actual, expected)
            self.assertEqual(sum(actual.values()), 100000)
        self.assertEqual(vm.writes, [])

    def test_empty_destination_initializes_from_packet(self):
        vm = fixture(0)
        vm.call('prepare_destination_credit')
        self.assertEqual(vm.packet['destination_prepared'], 1)
        self.assertEqual([r['new_factor'] for r in vm.packet['destination_culture_rows']], [1, 0])

    def test_invalid_destination_vectors_fail_before_credit(self):
        for kind in ('missing', 'extra', 'negative', 'duplicate', 'bad_total', 'wrong_identity'):
            with self.subTest(kind=kind):
                vm = fixture()
                rs = vm.packet['destination_culture_rows']
                if kind == 'missing': rs.pop(0)
                elif kind == 'extra': rs[1]['quantity'] = D(1)
                elif kind == 'negative': rs[1]['original_factor'] = D(-1)
                elif kind == 'duplicate':
                    rs.append(dict(rs[0], rank=D(9)))
                elif kind == 'bad_total': rs[1]['original_factor'] = D('.9')
                else: rs[0]['identity'] = {'key': 'z'}
                vm.call('prepare_destination_credit')
                self.assertEqual(vm.packet['invalid'], 1)
                self.assertNotIn('destination_prepared', vm.packet)
                self.assertEqual(vm.writes, [])

    def test_credit_receipt_retry_and_serialized_state_boundary(self):
        vm = fixture()
        vm.call('prepare_destination_credit')
        vm.call('apply_destination_credit')
        self.assertEqual(vm.writes, [])
        vm.packet['phase'] = D(4)
        vm.call('apply_destination_credit')
        self.assertEqual(vm.writes, [])  # no absolute credit yet
        # Deep copy simulates scope graph persistence, not native save/load.
        vm.packet = copy.deepcopy(vm.packet)
        vm.packet['destination']['aawc_population_current'] = D(1100)
        vm.call('apply_destination_credit')
        self.assertEqual(len(vm.writes), 4)
        self.assertEqual(vm.packet['phase'], 5)
        vm.call('apply_destination_credit')
        self.assertEqual(len(vm.writes), 4)
        self.assertEqual(vm.packet['source']['aawc_population_current'], 900)

    def test_refund_restores_exact_snapshots_despite_failed_destination(self):
        vm = fixture()
        vm.packet['invalid'] = D(1)
        vm.call('prepare_refund')
        self.assertEqual(vm.packet['refund_prepared'], 1)
        vm.call('apply_refund')
        self.assertEqual(vm.writes, [])
        vm.packet['phase'] = D(6)
        vm.call('apply_refund')
        self.assertEqual(vm.writes, [])
        vm.packet['source']['aawc_population_current'] = D(1000)
        vm.call('apply_refund')
        self.assertEqual([w[2] for w in vm.writes], [D('.6'), D('.4')] * 2)
        self.assertEqual(vm.packet['phase'], 7)
        vm.call('apply_refund')
        self.assertEqual(len(vm.writes), 4)

    def test_refund_rejects_interleaved_changes_and_settled_packets(self):
        for kind in ('population', 'culture', 'faith', 'missing', 'settled'):
            with self.subTest(kind=kind):
                vm = fixture()
                if kind == 'population': vm.packet['source']['aawc_population_current'] += 1
                elif kind == 'settled': vm.packet['phase'] = D(5)
                elif kind == 'missing': vm.packet['source']['kCAFG_province_culture_structs'].clear()
                else: vm.packet['source']['kCAFG_province_' + kind + '_structs'][0]['factor'] -= D('.01')
                vm.call('prepare_refund')
                self.assertNotIn('refund_prepared', vm.packet)
                self.assertEqual(vm.writes, [])

    def test_refund_rejects_duplicate_live_identity_even_with_normalized_total(self):
        vm = fixture()
        rs = vm.packet['culture_rows']
        for row in rs:
            row['new_factor'] = D('.5')
        vm.packet['source']['kCAFG_province_culture_structs'] = [
            {'culture': rs[0]['identity'], 'factor': D('.5')} for _ in range(2)]
        vm.call('prepare_refund')
        self.assertNotIn('refund_prepared', vm.packet)

    def test_invalid_absolute_destination_snapshot(self):
        for population in (D('-1'), D('1.5')):
            vm = fixture()
            vm.packet['destination_population'] = population
            vm.call('prepare_destination_credit')
            self.assertEqual(vm.packet['invalid'], 1)
            self.assertNotIn('destination_prepared', vm.packet)


if __name__ == '__main__':
    unittest.main()
