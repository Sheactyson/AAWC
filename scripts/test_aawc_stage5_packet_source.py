"""Staging source contracts only; not native execution or completed integration."""
from pathlib import Path
import re
import unittest
from generate_aawc_stage5_packets import render, MOD
from test_aawc_cohort_bounded_arithmetic import parse


class PacketSourceContracts(unittest.TestCase):
    def setUp(self):
        self.text = (MOD / 'common/scripted_effects/aawc_stage5_packet_effects.txt').read_text(encoding='utf-8-sig')
        self.defs = {k: v for k, _, v in parse(self.text)}

    def body(self, name):
        return repr(self.defs['aawc_stage5_' + name + '_effect'])

    def test_generated_parity_and_parse(self):
        self.assertEqual(self.text, render())
        self.assertEqual(len(self.defs), len(parse(self.text)), 'duplicate scripted-effect definition')
        self.assertIn('aawc_stage5_execute_transaction_effect', self.defs)

    def test_native_parameterless_calls_and_global_iterators(self):
        self.assertNotRegex(self.text, r'aawc_stage5_\w+_effect\s*=\s*\{\s*\}')
        for name in ('flush_counties','recover_pending'):
            self.assertIn('every_in_global_list', self.body(name))
            self.assertNotIn('global_variable', self.body(name).replace('clear_global_variable_list',''))

    def test_no_absolute_or_cafg_mutation_during_staging(self):
        for key, body in self.defs.items():
            if key not in ("aawc_stage5_begin_packet_effect", "aawc_stage5_snapshot_axis_effect", "aawc_stage5_snapshot_carry_effect",
                           "aawc_stage5_set_packet_quantity_effect", "aawc_stage5_seal_packet_effect",
                           "aawc_stage5_validate_axis_effect", "aawc_stage5_cancel_staging_effect",
                           "aawc_stage5_weight_departures_effect", "aawc_stage5_correct_departures_up_effect",
                           "aawc_stage5_correct_departures_down_effect",
                           "aawc_stage5_select_route_effect", "aawc_stage5_match_candidate_axis_effect",
                           "aawc_stage5_compare_candidate_effect"):
                continue
            def walk(nodes):
                for k, _, v in nodes:
                    if k in ('set_variable', 'change_variable', 'remove_variable'):
                        self.assertNotIn("'aawc_population_current'", repr(v))
                        self.assertNotIn("'factor'", repr(v))
                    if isinstance(v, list):
                        walk(v)
            walk(body)
        self.assertNotIn('E_kCAFG_', self.body('begin_packet'))

    def test_retry_guards_and_seal(self):
        self.assertIn("('has_variable', '=', 'aawc_stage5_packet')", self.body('begin_packet'))
        self.assertIn("('var:phase', '=', '0')", self.body('set_packet_quantity'))
        self.assertIn("('var:phase', '=', '0')", self.body('seal_packet'))
        for axis in ('culture', 'faith'):
            self.assertIn(f"('var:{axis}_total', '=', 'var:amount')", self.body('seal_packet'))

    def test_exact_snapshots_not_live_struct_pointers(self):
        body = self.body('snapshot_axis')
        self.assertIn('scope:aawc_stage5_origin_struct.var:$TYPE$', body)
        self.assertIn('scope:aawc_stage5_origin_struct.var:factor', body)
        self.assertIn('original_factor', body)
        self.assertIn('quantity', body)
        self.assertNotIn('destination', body)

    def test_validation_rejects_overdraw_fractional_and_bad_sums(self):
        body = self.body('validate_axis')
        for field in ('whole_quantity', 'var:available', 'var:$TYPE$_factor_total', 'invalid'):
            self.assertIn(field, body)
        self.assertIn("('var:quantity', '>', 'var:available')", body)
        self.assertIn("('var:quantity', '<', '0')", body)
        self.assertIn('whole_amount', self.body('begin_packet'))

    def test_cancellation_never_discards_committed_debt(self):
        body = self.body('cancel_staging')
        self.assertIn("('var:phase', '<', '2')", body)
        self.assertEqual(body.count("('end_story', '=', 'yes')"), 3)
        self.assertIn("('remove_variable', '=', 'aawc_stage5_packet')", body)


if __name__ == '__main__':
    unittest.main()
