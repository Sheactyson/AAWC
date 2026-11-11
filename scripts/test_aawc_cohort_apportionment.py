"""Selected-policy regression: exact oracle versus actual generated CK3 source.

The allocator is wired only through the generated demographic adapter. Full
integration and runtime gates remain separate. These tests do not certify CK3.
"""
import itertools
import random
import unittest

from aawc_cohort_apportionment import apportion, flow
from generate_aawc_cohort_apportionment import generate, P, N, MOD, VARIABLES
from test_aawc_cohort_bounded_arithmetic import SourceVM, S, parse
from validate_aawc_reforging_stage1_cohort_engine import definition_body, top_level_definitions


class ZeroElidingDict(dict):
    def __setitem__(self, key, value):
        if value == 0:
            self.pop(key, None)
        else:
            super().__setitem__(key, value)


class AllocationVM(SourceVM):
    def __init__(self, zero_elision=False):
        super().__init__()
        self.zero_elision = zero_elision
        for path, destination in ((MOD / 'scripted_effects/aawc_reforging_cohort_apportionment_effects.txt', self.effects),
                                  (MOD / 'script_values/aawc_reforging_cohort_apportionment_values.txt', self.values)):
            text = path.read_text(encoding='utf-8-sig')
            for name in top_level_definitions(text):
                destination[name] = parse(definition_body(text, name))

    def value(self, expression, initial=0):
        if self.zero_elision and isinstance(expression, str) and expression.startswith('var:'):
            if expression[4:] not in self.vars:
                raise AssertionError('unguarded absent-variable read: ' + expression)
        return super().value(expression, initial)

    def allocate(self, capacities, weights, requested):
        self.vars = ZeroElidingDict() if self.zero_elision else {}
        self.vars[P + 'requested'] = requested * S
        for i, (cap, weight) in enumerate(zip(capacities, weights)):
            self.vars[P + f'capacity_{i:02}'] = cap * S
            self.vars[P + f'weight_{i:02}'] = weight
        self.steps = 0
        self.call(P + 'allocate_effect')
        self.assert_valid = self.vars.get(P + 'valid', 0) == S
        return ([self.vars.get(P + f'allocation_{i:02}', 0) // S for i in range(N)],
                self.vars.get(P + 'remaining', 0) // S)


class LargestRemainder(unittest.TestCase):
    def test_known_hamilton_result_and_tie_order(self):
        self.assertEqual(apportion([20] * 3, [59, 26, 16], 10), ([6, 2, 2], 0))
        self.assertEqual(apportion([2] * 3, [1, 1, 1], 2), ([1, 1, 0], 0))

    def test_saturation_recomputes_quotas_without_borrowing_unavailable_people(self):
        self.assertEqual(apportion([1, 100, 100], [1000, 2, 1], 100), ([1, 66, 33], 0))
        self.assertEqual(apportion([1, 3, 9], [10, 1, 0], 10), ([1, 3, 0], 6))

    def test_pooled_subperson_flows_and_conserved_pending(self):
        amounts, pending = flow([1, 1, 1], [40000, 35000, 25000])
        self.assertEqual((amounts, pending), ([1, 0, 0], 0))
        amounts, pending = flow([1, 1], [40000, 35000])
        self.assertEqual((amounts, pending), ([0, 0], 75000))
        amounts, pending = flow([1, 1], [40000, 35000], pending)
        self.assertEqual((amounts, pending), ([1, 0], 50000))
        self.assertEqual(flow([0, 0], [50000, 40000], 120000), ([0, 0], 210000))

    def test_invalid_inputs_fail_instead_of_rounding_people(self):
        for caps, weights, request in (([.5], [1], 1), ([1], [-1], 1), ([1], [1], .5), ([1], [1], -1)):
            with self.assertRaises(ValueError):
                apportion(caps, weights, request)

    def test_generated_source_is_exact_and_callers_are_bounded_adapter(self):
        for path, expected in generate().items():
            self.assertEqual(path.read_bytes(), expected.encode('utf-8-sig'))
        generated = {p.resolve() for p in generate()}
        generated.add((MOD / 'scripted_effects/aawc_reforging_cohort_rounding_effects.txt').resolve())
        for path in MOD.parent.rglob('*.txt'):
            if path.resolve() not in generated:
                self.assertNotIn(P + 'allocate_effect', path.read_text(encoding='utf-8-sig'), str(path))

    def assert_case(self, vm, capacities, weights, requested):
        padded_caps = list(capacities) + [0] * (N - len(capacities))
        padded_weights = list(weights) + [0] * (N - len(weights))
        expected = apportion(padded_caps, padded_weights, requested)
        actual = vm.allocate(padded_caps, padded_weights, requested)
        self.assertTrue(vm.assert_valid)
        self.assertEqual(actual, expected, (capacities, weights, requested))
        self.assertEqual(sum(actual[0]) + actual[1], requested)
        self.assertTrue(all(0 <= a <= c for a, c in zip(actual[0], padded_caps)))
        self.assertTrue(all(a == 0 for a, w in zip(actual[0], padded_weights) if not w))
        self.assertLess(vm.steps, 8000)  # fixed band-count bound, independent of people

    def test_exhaustive_two_band_capacities_weights_requests(self):
        vm = AllocationVM()
        for caps in itertools.product(range(3), repeat=2):
            for weights in itertools.product((0, 1, 7), repeat=2):
                for request in range(7):
                    self.assert_case(vm, caps, weights, request)

    def test_seeded_thirteen_band_and_large_number_cases(self):
        vm = AllocationVM()
        rng = random.Random(3107)
        for _ in range(120):
            caps = [rng.randrange(0, 100000000) for _ in range(N)]
            weights = [rng.randrange(0, 10000000) for _ in range(N)]
            self.assert_case(vm, caps, weights, rng.randrange(sum(caps) * 2))
        # Quotient truncation would tie these fractions; exact numerators must not.
        self.assert_case(vm, [100, 100], [10000001, 10000002], 1)

    def test_zero_elision_and_no_durable_side_effects(self):
        vm = AllocationVM(zero_elision=True)
        for caps, weights, request in (([0, 2], [0, 1], 1), ([1, 10, 20], [1000, 3, 1], 12), ([0], [0], 0)):
            self.assert_case(vm, caps, weights, request)
        self.assertTrue(all(k.startswith(P) for k in vm.vars))
        vm.call(P + 'cleanup_effect')
        self.assertEqual(vm.vars, {})

    def test_source_rejects_fractional_capacity_and_request_without_consumption(self):
        vm = AllocationVM()
        vm.allocate([1], [S], 1)
        vm.vars[P + 'capacity_00'] = S // 2
        vm.call(P + 'allocate_effect')
        self.assertEqual(vm.vars.get(P + 'valid'), 0)
        self.assertEqual(vm.vars[P + 'remaining'], S)
        self.assertEqual(vm.vars[P + 'allocation_00'], 0)

    def test_arithmetic_envelope_rejects_unsafe_intermediate_without_consumption(self):
        vm = AllocationVM()
        actual = vm.allocate([100000000], [100000000 * S], 100000000)
        self.assertFalse(vm.assert_valid)
        self.assertEqual(actual, ([0] * N, 100000000))


if __name__ == '__main__':
    unittest.main(verbosity=2)
