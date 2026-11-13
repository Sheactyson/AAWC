"""Execute the repaired source subset against independent fixedpoint oracles.

This deliberately small interpreter is a regression tool, not CK3 certification.
Unknown syntax fails closed. Arithmetic uses the retained-save five-decimal
truncation hypothesis; engine parser/runtime, zero elision and UI require CK3.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import operator
import re
import unittest

from validate_aawc_reforging_stage1_cohort_engine import (
    ALL_FRACTIONS, BANDS, MILITARY, MOD_ROOT, definition_body,
    top_level_definitions,
)

S = 100000
P = "aawc_reforging_cohort_"


def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\#[^\n]*|>=|<=|!=|\?=|[{}=<>]|[^\s{}=<>!?]+', text)
    tokens = [t for t in tokens if not t.startswith('#')]
    pos = 0

    def block():
        nonlocal pos
        result = []
        while pos < len(tokens) and tokens[pos] != '}':
            key, op = tokens[pos:pos + 2]
            pos += 2
            if op not in ('=', '!=', '>', '<', '>=', '<=', '?='):
                raise ValueError((key, op))
            value = tokens[pos]
            pos += 1
            if value == '{':
                value = block()
                assert tokens[pos] == '}'
                pos += 1
            result.append((key, op, value))
        return result

    result = block()
    assert pos == len(tokens)
    return result


class SourceVM:
    def __init__(self, mod_root=MOD_ROOT):
        self.effects, self.values = {}, {}
        for category, stems, target in (
            ('scripted_effects', ('stage1', 'production', 'pilot', 'diagnostics', 'apportionment', 'rounding', 'transaction'), self.effects),
            ('script_values', ('stage1', 'pilot', 'diagnostics', 'apportionment', 'rounding', 'transaction'), self.values),
        ):
            for stem in stems:
                path = mod_root / 'common' / category / f'aawc_reforging_cohort_{stem}_{"effects" if category == "scripted_effects" else "values"}.txt'
                text = path.read_text(encoding='utf-8-sig')
                for name in top_level_definitions(text):
                    target[name] = parse(definition_body(text, name))
        self.vars, self.logs = {}, []
        # Stage 2 extends production initialization with derived conditions only.
        # Native environmental predicates are explicit fixture inputs, not inferred
        # CK3 runtime evidence. Existing ledger-only fixtures use a plain settlement.
        self.holding = 'settlement_holding'
        self.buildings, self.building_flags, self.terrains = set(), set(), set()
        self.development, self.control, self.epidemic = 0, 100, 0
        self.at_war = False
        self.county_vars = {}
        for category, names, target in (
            ('scripted_effects', ('aawc_stage2_condition_effects', 'aawc_stage2_building_contributions'), self.effects),
            ('script_values', ('aawc_stage2_condition_values',), self.values),
        ):
            for name in names:
                text = (mod_root / 'common' / category / (name + '.txt')).read_text(encoding='utf-8-sig')
                for key in top_level_definitions(text):
                    target[key] = parse(definition_body(text, key))
        text = (mod_root / 'common/script_values/aawc_population_values.txt').read_text(encoding='utf-8-sig')
        for name in ('aawc_population_holding_main_line_capacity_base',
                     'aawc_population_holding_main_line_development_bonus',
                     'aawc_population_holding_main_line_expected_capacity',
                     'aawc_population_holding_building_expected_capacity',
                     'aawc_population_holding_expected'):
            self.values[name] = parse(definition_body(text, name))
        self.constants = {k: int(Decimal(v) * S) for k, v in re.findall(r'^(@\w+)\s*=\s*(-?[\d.]+)', text, re.M)}
        self.diagnostics_enabled = False
        self.valid_settlement = True
        self.steps = 0

    def value(self, expr, initial=0):
        if not isinstance(expr, list):
            if expr == 'county.development_level': return int(Decimal(str(self.development)) * S)
            if expr == 'county.county_control': return int(Decimal(str(self.control)) * S)
            if expr in self.constants: return self.constants[expr]
            if expr.startswith('var:'):
                return self.vars.get(expr[4:], 0)
            if expr in self.values:
                return self.value(self.values[expr])
            return int(Decimal(expr) * S)
        result = initial
        branch = False
        for key, _, arg in expr:
            if key in ('if', 'else_if'):
                take = (key == 'if' or not branch) and self.condition(next(v for k, _, v in arg if k == 'limit'))
                if key == 'if': branch = False
                if take:
                    result = self.value([x for x in arg if x[0] != 'limit'], result)
                    branch = True
                continue
            if key == 'else':
                if not branch: result = self.value(arg, result)
                continue
            if key == 'round':
                assert arg == 'yes'
                result = int((Decimal(result) / S).quantize(Decimal(1), rounding=ROUND_HALF_UP)) * S
                continue
            if key == 'floor':
                assert arg == 'yes'
                result = result // S * S
                continue
            right = self.value(arg)
            if key == 'value': result = right
            elif key == 'add': result += right
            elif key == 'subtract': result -= right
            elif key == 'multiply': result = int(Decimal(result) * right / S)
            elif key == 'divide': result = int(Decimal(result) * S / right)
            elif key == 'min': result = max(result, right)  # CK3 lower bound
            elif key == 'max': result = min(result, right)  # CK3 upper bound
            else: raise ValueError(('unsupported value', key))
        return result

    def condition(self, body):
        checks = []
        for key, op, arg in body:
            if key in ('aawc_diagnostics_summary_enabled', 'aawc_diagnostics_verbose_enabled'): checks.append(self.diagnostics_enabled == (arg == 'yes'))
            elif key == 'aawc_population_valid_settlement_for_cohort_trigger': checks.append(self.valid_settlement == (arg == 'yes'))
            elif key == 'has_holding': checks.append(bool(self.holding) == (arg == 'yes'))
            elif key == 'has_holding_type': checks.append(self.holding == arg)
            elif key == 'has_building': checks.append(arg in self.buildings)
            elif key == 'has_building_with_flag': checks.append(arg in self.building_flags)
            elif key.startswith('agot_is_') and key.endswith('_terrain'):
                checks.append((key[8:-8] in self.terrains) == (arg == 'yes'))
            elif key == 'county':
                checks.append(self.county_condition(arg))
            elif key == 'county.holder':
                checks.append(self.holder_condition(arg))
            elif key == 'has_variable': checks.append(arg in self.vars)
            elif key == 'NOT': checks.append(not self.condition(arg))
            elif key == 'OR': checks.append(any(self.condition([x]) for x in arg))
            elif key == 'AND': checks.append(self.condition(arg))
            else:
                if key.startswith('var:') and isinstance(arg,list):
                    raise ValueError('CK3 treats variable = { ... } as a scope trigger, not inline comparison arithmetic')
                comparison = {'=': operator.eq, '!=': operator.ne, '>': operator.gt,
                              '<': operator.lt, '>=': operator.ge, '<=': operator.le}[op]
                checks.append(comparison(self.value(key), self.value(arg)))
        return all(checks)

    def holder_condition(self, body):
        checks = []
        for key, op, arg in body:
            if key == 'is_at_war': checks.append(self.at_war == (arg == 'yes'))
            else: raise ValueError(('unsupported holder condition', key))
        return all(checks)

    def county_condition(self, body):
        checks = []
        for key, op, arg in body:
            if key == 'has_variable': checks.append(arg in self.county_vars)
            elif key == 'OR': checks.append(any(self.county_condition([x]) for x in arg))
            elif key == 'has_province_with_epidemic':
                kind, comparison, intensity = arg[0]
                assert kind == 'intensity'
                level = {'any': 1, 'major': 2, 'apocalyptic': 3}[intensity]
                checks.append(self.epidemic >= level if comparison == '>=' or intensity == 'any' else self.epidemic == level)
            else: raise ValueError(('unsupported county condition', key))
        return all(checks)

    def call(self, name, **params):
        def subst(text):
            for key, value in params.items():
                if text == '$' + key + '$' and isinstance(value, list):
                    return value
            for key, value in params.items(): text = text.replace('$' + key + '$', str(value))
            return text

        def transform(body):
            return [(subst(k), op, transform(v) if isinstance(v, list) else subst(v)) for k, op, v in body]
        self.run(transform(self.effects[name]) if params else self.effects[name])

    def run(self, body):
        branch = False
        for key, _, arg in body:
            self.steps += 1
            if key == 'if' or key == 'else_if':
                take = (key == 'if' or not branch) and self.condition(next(v for k, _, v in arg if k == 'limit'))
                if key == 'if': branch = False
                if take:
                    self.run([x for x in arg if x[0] != 'limit'])
                    branch = True
            elif key == 'else':
                if not branch: self.run(arg)
            elif key == 'hidden_effect': self.run(arg)
            elif key in ('set_variable', 'change_variable'):
                name = next(v for k, _, v in arg if k == 'name')
                self.vars[name] = self.value([x for x in arg if x[0] != 'name'],
                                             self.vars.get(name, 0) if key == 'change_variable' else 0)
            elif key == 'remove_variable': self.vars.pop(arg, None)
            elif key in ('debug_log', 'error_log'): self.logs.append((key, arg))
            elif key in self.effects:
                self.call(key, **({k: v for k, _, v in arg} if isinstance(arg, list) else {}))
            else: raise ValueError(('unsupported effect', key))

    def initialize(self, total=100):
        self.call(P + 'initialize_production_ledger_effect', POPULATION=total)

    def tick(self, tick):
        self.call(P + 'monthly_authority_effect', TICK_ID=tick)


class BoundedArithmetic(unittest.TestCase):
    def test_production_completion_marker_is_valid_without_test_marker(self):
        # Canonical session03 rejected all 158 production ledgers because its
        # read-only invariant required the opt-in test-fixture marker.
        vm = SourceVM()
        vm.initialize()
        production = P + 'production_initialized'
        test = P + 'test_initialized'
        self.assertIn(production, vm.vars)
        self.assertNotIn(test, vm.vars)
        before = dict(vm.vars)
        self.assertEqual(vm.value(P + 'invariant_status'), S)
        self.assertEqual(vm.vars, before)
        vm.vars.pop(production)
        self.assertEqual(vm.value(P + 'invariant_status'), 0)
        vm.vars[test] = S
        self.assertEqual(vm.value(P + 'invariant_status'), S)
        # Either marker still requires the ledger and its existing bounds.
        vm.vars[BANDS[0]] = -S
        self.assertEqual(vm.value(P + 'invariant_status'), 0)

    def test_vm_fixedpoint_and_bounds(self):
        vm = SourceVM()
        self.assertEqual(vm.value(parse('value = 12.34567 max = 8 floor = yes')), 8 * S)
        self.assertEqual(vm.value(parse('value = -1 min = 0')), 0)
        self.assertEqual(vm.value(parse('value = 1 divide = 60')), 1666)
        with self.assertRaises(ValueError): vm.run(parse('invented = yes'))

    def test_600_source_ticks_match_independent_reference_and_duplicate_guard(self):
        from aawc_cohort_rounding_reference import reference as rounded_reference
        from validate_aawc_reforging_stage1_cohort_engine import MORTALITY_FRACTIONS, AGING_FRACTIONS, MILITARY_AGING_FRACTIONS
        vm = SourceVM()
        vm.initialize()
        for dimension in ('sustenance', 'habitation', 'opportunity', 'health', 'security', 'amenities'):
            vm.vars[f'aawc_stage2_effective_{dimension}'] = 50 * S
        for tick in range(600): vm.tick(tick)
        expected = rounded_reference(600)
        carries = {'aawc_reforging_birth_fraction': expected.birth}
        carries.update(zip(MORTALITY_FRACTIONS, expected.mortality))
        carries.update(zip(AGING_FRACTIONS, expected.aging))
        carries.update(zip(MILITARY_AGING_FRACTIONS, expected.military_aging))
        carries['aawc_reforging_military_training_fraction'] = 0
        self.assertEqual([vm.vars[b] for b in BANDS], [n * S for n in expected.bands])
        self.assertEqual({k: vm.vars[k] for k in ALL_FRACTIONS}, carries)
        before = dict(vm.vars)
        vm.tick(599)
        self.assertEqual(vm.vars, before)
        self.assertFalse(any(k == 'error_log' for k, _ in vm.logs))

    def test_births_exceed_1000_without_losing_carry(self):
        vm = SourceVM()
        vm.initialize(100000000)
        vm.vars['aawc_reforging_birth_fraction'] = 11747 * S + 39326
        expected = vm.value('aawc_reforging_cohort_candidate_monthly_births') + vm.vars['aawc_reforging_birth_fraction']
        before = vm.vars[BANDS[0]]
        vm.steps = 0
        vm.call(P + 'apply_births_effect')
        whole, remainder = divmod(expected, S)
        self.assertGreater(whole, 1000)
        self.assertEqual(vm.vars[BANDS[0]] - before, whole * S)
        self.assertEqual(vm.vars['aawc_reforging_birth_fraction'], remainder)
        self.assertLess(vm.steps, 12)

    def test_mortality_large_empty_and_exhausted_pools(self):
        for source, carry, rate in ((2000000, 99999, 3000), (2, 450000, 0), (0, 150000, 0)):
            vm = SourceVM()
            vm.vars.update(pool=source * S, carry=carry)
            vm.call(P + 'apply_band_mortality_effect', BAND='pool', FRACTION='carry', RATE=rate)
            deaths = min(source, (carry + rate * S) // S)
            self.assertEqual(vm.vars['pool'], (source - deaths) * S)
            self.assertEqual(vm.vars.get(P + 'last_deaths', 0), deaths * S)
            self.assertTrue(0 <= vm.vars['carry'] < S)

    def test_large_aging_and_military_parent_conservation(self):
        for source, military, carry in ((6000000, 3000000, 99999), (60, 60, 0), (3, 2, 99000)):
            vm = SourceVM()
            vm.vars.update(pool=source * S, dest=0, m=military * S, mdest=0, carry=carry, mcarry=99000)
            vm.call(P + 'apply_aging_band_effect', SOURCE='pool', DESTINATION='dest', FRACTION='carry')
            moved = (carry + source * S // 60) // S
            vm.call(P + 'apply_military_aging_band_effect', SOURCE='m', DESTINATION='mdest', PARENT_SOURCE='pool', FRACTION='mcarry')
            self.assertEqual(vm.vars['pool'] + vm.vars['dest'], source * S)
            self.assertEqual(vm.vars['dest'], moved * S)
            self.assertEqual(vm.vars['m'] + vm.vars['mdest'], military * S)
            self.assertLessEqual(vm.vars['m'], vm.vars['pool'])
            self.assertLessEqual(vm.vars['mdest'], vm.vars['dest'])
            self.assertTrue(0 <= vm.vars['mcarry'] < S)
            # Bounded guards and backlog settlement add constant work, not
            # loops proportional to the resident population.
            self.assertLess(vm.steps, 90)

    def test_large_retirement_preserves_people(self):
        vm = SourceVM()
        vm.initialize(100000000)
        vm.vars[MILITARY[-1]] = vm.vars[BANDS[-2]]
        before_people = sum(vm.vars[b] for b in BANDS)
        before_military = vm.vars[MILITARY[-1]]
        vm.call(P + 'apply_aging_band_effect', SOURCE=BANDS[-2], DESTINATION=BANDS[-1], FRACTION='aawc_reforging_aging_fraction_age_55_59')
        movers = vm.vars[P + 'work_aged']
        vm.call(P + 'apply_military_retirement_effect')
        self.assertEqual(sum(vm.vars[b] for b in BANDS), before_people)
        self.assertEqual(before_military - vm.vars[MILITARY[-1]], movers)
        self.assertEqual(vm.vars[P + 'last_military_retired'], movers)

    def test_complete_large_tick_bounds_and_conservation(self):
        for total in (100, 1000000, 100000000):
            vm = SourceVM()
            vm.initialize(total)
            for b, m in zip(BANDS[3:12], MILITARY): vm.vars[m] = vm.vars[b] // (2 * S) * S
            vm.steps = 0
            vm.tick(0)
            self.assertEqual(sum(vm.vars[b] for b in BANDS), total * S + vm.vars[P + 'last_births'] - vm.vars[P + 'last_deaths'])
            self.assertTrue(all(0 <= vm.vars[k] < S for k in ALL_FRACTIONS))
            self.assertTrue(all(0 <= vm.vars[m] <= vm.vars[b] for b, m in zip(BANDS[3:12], MILITARY)))
            self.assertTrue(all(vm.vars[b] % S == 0 for b in BANDS))
            # Three bounded Hamilton allocations replace scalar per-band
            # floors. Bound is in band-count work, never a per-person loop;
            # this is not a CK3 wall-clock performance acceptance threshold.
            self.assertLess(vm.steps, 30000)
            self.assertFalse(any(k == 'error_log' for k, _ in vm.logs))

    def test_external_deaths_do_not_rewrite_completed_tick(self):
        vm = SourceVM()
        vm.initialize(1000000)
        vm.tick(0)
        snapshot = {k: v for k, v in vm.vars.items() if k.startswith(P + 'last_')}
        before = sum(vm.vars[b] for b in BANDS)
        for amount in (36871.73898, 3):
            vm.call(P + 'death_population_effect', AMOUNT=amount)
        actual_loss = before - sum(vm.vars[b] for b in BANDS)
        self.assertEqual(actual_loss, 36874 * S)
        self.assertEqual(actual_loss + vm.vars['aawc_reforging_round_population_death_pending'], 3687473898)
        self.assertEqual(vm.vars[P + 'external_deaths_total'], actual_loss)
        self.assertEqual(vm.vars[P + 'last_external_deaths'], 3 * S)
        self.assertEqual({k: vm.vars[k] for k in snapshot}, snapshot)
        self.assertEqual(vm.value('aawc_reforging_ui_last_deaths'), snapshot[P + 'last_deaths'])
        vm.tick(1)
        self.assertEqual(vm.vars[P + 'external_deaths_total'], actual_loss)

    def test_no_population_dependent_loops_in_repaired_primitives(self):
        vm = SourceVM()
        for name in ('births', 'band_mortality', 'aging_band', 'military_aging_band', 'military_retirement'):
            self.assertNotIn("'while'", repr(vm.effects[P + 'apply_' + name + '_effect']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
