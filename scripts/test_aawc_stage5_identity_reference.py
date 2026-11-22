"""Mathematical Stage 5 regressions; these do not certify native execution."""
from fractions import Fraction
import random
import unittest

from aawc_stage5_identity_reference import (
    SCALE, departure, majority, normalize, reconcile, resolve_axis,
)


class IdentityArithmetic(unittest.TestCase):
    def test_independent_missing_axes(self):
        cultures = {'a': 60000, 'b': 40000}
        faiths = {'x': 25000, 'y': 75000}
        self.assertEqual(resolve_axis(cultures, 10)[1], {'a': 10})
        self.assertEqual(resolve_axis(faiths, 10, {'x': 10})[1], {'x': 10})
        self.assertEqual(resolve_axis(cultures, 10, {'b': 10})[1], {'b': 10})
        self.assertEqual(resolve_axis(faiths, 10)[1], {'y': 10})

    def test_majority_tie_and_empty_axis_repair(self):
        self.assertEqual(majority({'b': 50000, 'a': 50000}), 'a')
        self.assertEqual(resolve_axis({}, 2, title_majority='a'), ({'a': SCALE}, {'a': 2}))
        with self.assertRaises(ValueError):
            resolve_axis({}, 2)

    def test_contradictory_or_malformed_provenance(self):
        for vector in ({'b': 2}, {'a': 1}, {'a': -2}, {'a': 2.0}):
            with self.assertRaises(ValueError):
                resolve_axis({'a': SCALE}, 2, vector)

    def test_owner_pressure_and_explicit_bypass(self):
        shares = {'aligned': 50000, 'other': 50000}
        self.assertEqual(departure(shares, 1000, 100, 'aligned')[0], {'aligned': 20, 'other': 80})
        self.assertEqual(departure(shares, 1000, 100)[0], {'aligned': 50, 'other': 50})
        self.assertEqual(resolve_axis(shares, 100, {'aligned': 100})[1], {'aligned': 100})

    def test_persisted_fractional_departures(self):
        carry = {}
        totals = {'a': 0, 'b': 0}
        for _ in range(100):
            vector, carry = departure({'a': 50000, 'b': 50000}, 1000, 1, 'a', carry)
            totals = {k: totals[k] + vector[k] for k in totals}
            # Exact rational state can be persisted without losing a remainder.
            carry = {k: Fraction(str(v)) for k, v in carry.items()}
        self.assertEqual(totals, {'a': 20, 'b': 80})

    def test_saturation_does_not_overdraw_identity(self):
        vector, _ = departure({'a': 90000, 'b': 10000}, 100, 95, 'a')
        self.assertEqual(vector, {'a': 85, 'b': 10})
        with self.assertRaises(ValueError):
            departure({'a': SCALE}, 10, 11)

    def test_debit_and_credit_formulas(self):
        source = {'a': 60000, 'b': 40000}
        source_new = reconcile(source, 1000, {'a': 100}, debit=True, protective_floor=250)
        target_new = reconcile({'b': SCALE}, 1000, {'a': 100})
        self.assertEqual(source_new, {'a': 55556, 'b': 44444})
        self.assertEqual(target_new, {'a': 9091, 'b': 90909})
        # Quantization bounds are explicit; normalized factors are not persons.
        for key in source:
            before = Fraction(1000 * source[key] + 1000 * {'b': SCALE}.get(key, 0), SCALE)
            after = Fraction(900 * source_new[key] + 1100 * target_new[key], SCALE)
            self.assertLessEqual(abs(before - after), Fraction(2000, SCALE))

    def test_empty_destination_and_absorption(self):
        self.assertEqual(reconcile({}, 0, {'a': 3, 'b': 1}), {'a': 75000, 'b': 25000})
        self.assertEqual(normalize({'a': 999, 'b': 1}), {'a': SCALE, 'b': 0})
        self.assertEqual(normalize({'a': 995, 'b': 5}), {'a': 99500, 'b': 500})

    def test_fail_closed_source_and_floor(self):
        for vector, floor in (({'b': 1}, 0), ({'a': 751}, 250), ({'a': 1000}, 0)):
            with self.assertRaises(ValueError):
                reconcile({'a': SCALE}, 1000, vector, debit=True, protective_floor=floor)

    def test_randomized_capacity_and_normalization(self):
        rng = random.Random(5)
        for _ in range(300):
            shares = normalize({str(k): rng.randint(1, 1000) for k in range(8)})
            population = 100000
            amount = rng.randint(1, 90000)
            vector, _ = departure(shares, population, amount, '0')
            self.assertEqual(sum(vector.values()), amount)
            for k, v in vector.items():
                self.assertLessEqual(v, population * shares[k] // SCALE)
            self.assertEqual(sum(reconcile(shares, population, vector, debit=True).values()), SCALE)
            self.assertEqual(sum(reconcile({}, 0, vector).values()), SCALE)

    def test_zero_demand_preserves_carries_and_inputs(self):
        carry = {'a': Fraction(1, 3)}
        self.assertEqual(departure({'a': SCALE}, 100, 0, residuals=carry), ({'a': 0}, carry))


if __name__ == '__main__':
    unittest.main()
