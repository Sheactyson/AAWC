"""Bounded Stage 2 behavioral checks, optionally executing an extracted release.

SourceVM executes the real effects/values, including the Stage 1 ledger. Native
environment predicates are fixture inputs and fixed point is a five-decimal
hypothesis; this does not certify CK3 event dispatch, parser, performance or UI.
No alternate demographic simulator, gameplay installation or save is used.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

from generate_aawc_stage2_conditions import DIMENSIONS, FIELDS, TABLE, rows
from test_aawc_cohort_bounded_arithmetic import P, S, SourceVM, parse
from test_aawc_stage2_demographic_integration import expected_month, set_effective, set_structural_and_refresh
from validate_aawc_reforging_stage1_cohort_engine import ALL_FRACTIONS, BANDS, BAND_SUFFIXES, MOD_ROOT, definition_body

CONDITION = 'aawc_stage2_'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class ProductionVM(SourceVM):
    """Execute the production wrapper with an explicitly supplied monthly expiry.

    Only its known 27-day guard is supported. Tests remove that marker before
    each simulated monthly visit; they do not claim native scheduler coverage.
    """
    def run(self, body):
        prepared = []
        for key, op, arg in body:
            if key == 'set_variable' and any(k == 'days' for k, _, _ in arg):
                assert ('name', '=', P+'monthly_tick_recent') in arg
                assert ('days', '=', '27') in arg
                arg = [node for node in arg if node[0] != 'days']
            prepared.append((key, op, arg))
        return super().run(prepared)


class BehavioralRegression(unittest.TestCase):
    root = MOD_ROOT
    evidence = {}

    def vm(self, population=10000, buildings=(), holding='city_holding'):
        vm = ProductionVM(self.root)
        vm.holding = holding
        vm.buildings = set(buildings)
        vm.initialize(population)
        return vm

    def ledger(self, vm):
        return {key: value for key, value in vm.vars.items() if key.startswith('aawc_reforging_')}

    def assert_ledger(self, vm):
        self.assertEqual(vm.value(P+'invariant_status'), S)
        self.assertEqual(vm.vars['aawc_population_current'], sum(vm.vars[band] for band in BANDS))
        self.assertTrue(all(vm.vars[band] >= 0 and vm.vars[band] % S == 0 for band in BANDS))
        self.assertTrue(all(0 <= vm.vars.get(key, 0) < S for key in ALL_FRACTIONS))
        self.assertFalse(any(kind == 'error_log' for kind, _ in vm.logs), vm.logs[-3:])

    def month(self, vm, tick):
        # An ordinary monthly visit occurs after the 27-day marker has expired.
        vm.vars.pop(P+'monthly_tick_recent', None)
        before = vm.value(P+'band_sum')
        ledger = self.ledger(vm)
        vm.call(CONDITION+'refresh_effective_effect')
        self.assertEqual(self.ledger(vm), ledger)
        vm.call(P+'apply_production_month_effect')
        self.assertEqual(vm.value(P+'band_sum'), before + vm.vars[P+'last_births'] - vm.vars[P+'last_deaths'])
        self.assert_ledger(vm)
        vm.call(CONDITION+'refresh_effective_effect')

    def test_all_771_contributions_execute_exactly_and_upgrade_chains_do_not_stack(self):
        vm = SourceVM(self.root)
        records = rows()
        chains = defaultdict(list)
        for row in records:
            chains[row['chain']].append(row)
        def evaluate(buildings, expected):
            vm.buildings = set(buildings)
            vm.vars = {CONDITION+'structural_'+dim: 50*S for dim in DIMENSIONS}
            vm.vars[CONDITION+'space_percent'] = 0
            vm.call(CONDITION+'building_contributions_effect')
            actual = [vm.vars[CONDITION+'structural_'+dim]-50*S for dim in DIMENSIONS]
            actual.append(vm.vars[CONDITION+'space_percent'])
            self.assertEqual(actual, [int(Decimal(expected[field])*S) for field in FIELDS], buildings)
        for row in records:
            evaluate([row['building']], row)
        for chain in chains.values():
            evaluate([row['building'] for row in chain], max(chain, key=lambda row: int(row['level'])))
        self.evidence['contribution_execution'] = {'levels': len(records), 'upgrade_chains': len(chains)}

    def test_structural_derivation_and_clamps_have_independent_numeric_oracles(self):
        vm = self.vm(100, ('city_04', 'aawc_cereal_fields_01', 'aawc_infirmaries_01'))
        vm.development = 50
        vm.terrains = {'urban'}
        vm.call(CONDITION+'initialize_conditions_effect')
        # City + main level 4 + development 50 + urban + farm + hospice.
        expected = (51, 72, 67, 52, 50, 56)
        self.assertEqual(tuple(vm.vars[CONDITION+'structural_'+d]//S for d in DIMENSIONS), expected)
        self.assertEqual(tuple(vm.vars[CONDITION+'effective_'+d]//S for d in DIMENSIONS), expected)
        for development, bounded in ((-50, 0), (0, 0), (100, 100), (150, 100)):
            vm.development = development
            self.assertEqual(vm.value(CONDITION+'development'), bounded*S)
        for layer in ('structural', 'effective'):
            for score in (-500, 0, 50, 100, 500):
                for dim in DIMENSIONS:
                    vm.vars[f'{CONDITION}{layer}_{dim}'] = score*S
                    self.assertEqual(vm.value(f'{CONDITION}{layer}_{dim}_value'), min(100,max(0,score))*S)
        self.evidence['independent_structural_oracle'] = dict(zip(DIMENSIONS, expected))

    def test_dimension_sweeps_preserve_bounds_monotonicity_and_age_channels(self):
        vm = self.vm()
        for dim in DIMENSIONS:
            prev_births, prev_deaths = None, None
            for score in range(101):
                set_effective(vm, **{dim: score})
                births, deaths = expected_month(vm)
                if prev_births is not None:
                    self.assertGreaterEqual(births, prev_births, (dim,score))
                    self.assertLessEqual(deaths, prev_deaths, (dim,score))
                    if dim in ('health', 'amenities'):
                        self.assertEqual(births, prev_births)
                    if dim in ('opportunity', 'amenities'):
                        self.assertEqual(deaths, prev_deaths)
                for suffix in BAND_SUFFIXES:
                    multiplier = vm.value('aawc_reforging_stage2_mortality_multiplier_age_'+suffix)
                    self.assertTrue(45000 <= multiplier <= 12*S)
                prev_births, prev_deaths = births, deaths
        set_effective(vm)
        baseline_births, baseline_deaths = expected_month(vm)
        for dim in ('habitation', 'sustenance', 'opportunity'):
            set_effective(vm, **{dim: 40})
            deficiency_cost = baseline_births-expected_month(vm)[0]
            set_effective(vm, **{dim: 60})
            self.assertGreater(deficiency_cost, expected_month(vm)[0]-baseline_births)
        for score in (25, 35, 50, 100):
            set_effective(vm, security=score)
            self.assertEqual(expected_month(vm)[1], baseline_deaths)
        self.evidence['dimension_sweep'] = {'score_vectors': 606, 'mortality_bands_per_vector': 13}

    def test_pressure_onsets_zero_capacity_and_no_resident_clipping(self):
        vm = self.vm(0)
        vm.vars['aawc_population_expected'] = 100000*S
        for dim in DIMENSIONS:
            vm.vars[CONDITION+'structural_'+dim] = 100*S
        prev = (-1, -1)
        for residents in (0, 79999, 80000, 80001, 89999, 90000, 90001, 99999, 100000, 100001, 124999, 125000, 125001, 200000, 1000000):
            vm.vars[BANDS[0]] = residents*S
            ledger = self.ledger(vm)
            housing = vm.value(CONDITION+'housing_pressure_loss')
            health = vm.value(CONDITION+'health_pressure_loss')
            self.assertTrue(prev[0] <= housing <= 100*S)
            self.assertTrue(prev[1] <= health <= 100*S)
            if residents <= 80000: self.assertEqual(housing, 0)
            if residents <= 90000: self.assertEqual(health, 0)
            vm.call(CONDITION+'refresh_effective_effect')
            self.assertEqual(self.ledger(vm), ledger)
            prev = (housing,health)
        vm.vars['aawc_population_expected'] = 0
        self.assertEqual(vm.value(CONDITION+'occupancy'), 0)
        vm.vars.pop('aawc_population_expected')
        self.assertEqual(vm.value(CONDITION+'occupancy'), 0)

    def test_tiny_empty_and_overfull_ledgers_keep_monthly_accounting_and_duplicate_guard(self):
        for initial in (0, 1, 2, 13, 125, 10000):
            vm = self.vm(initial)
            set_structural_and_refresh(vm, max(1, initial//2), **dict.fromkeys(DIMENSIONS,100))
            for tick in range(12):
                self.month(vm,tick)
                before = dict(vm.vars)
                vm.call(P+'apply_production_month_effect')
                self.assertEqual(vm.vars,before)
            if initial == 0: self.assertEqual(vm.value(P+'band_sum'),0)
        self.evidence['ledger_accounting'] = {'initial_populations': [0,1,2,13,125,10000], 'months_each': 12}

    def test_crisis_external_carry_and_ordinary_deaths_remain_separate_during_disruption(self):
        results = {}
        # These factors are the actual three existing completion-hook policies.
        warfare = (self.root/'common/on_action/aawc_population_warfare_on_actions.txt').read_text(encoding='utf-8-sig')
        for event, marker, percent in (('raid_action_completion','raid',15), ('siege_completion','siege',30), ('county_occupied','siege',10)):
            hook = definition_body(warfare, 'aawc_population_on_'+event)
            self.assertEqual(re.findall(r'LOSS_FACTOR = ([\d.]+)',hook), [f'0.{percent:02}'])
            vm = self.vm(101)
            vm.county_vars['aawc_population_'+marker+'_growth_suppressed'] = S
            before = vm.value(P+'band_sum')
            vm.call(P+'death_population_effect', AMOUNT=str(Decimal(101)*percent/100))
            debit = 101*percent//100
            self.assertEqual(vm.value(P+'band_sum'),before-debit*S)
            self.assertEqual(vm.vars[P+'external_deaths_total'],debit*S)
            carry = vm.vars['aawc_reforging_round_population_death_pending']
            self.assertEqual(carry,(101*percent%100)*S//100)
            ordinary_deaths = 0
            for tick in range(12):
                self.month(vm,tick)
                ordinary_deaths += vm.vars[P+'last_deaths']//S
                self.assertEqual(vm.vars[P+'external_deaths_total'],debit*S)
                self.assertEqual(vm.vars['aawc_reforging_round_population_death_pending'],carry)
            results[event] = {'external_deaths':debit,'external_fraction':carry/S,'ordinary_deaths_next_12_months':ordinary_deaths}
        self.evidence['loss_accounting'] = results

    def test_capture_and_occupation_select_disjoint_holding_types(self):
        text = (self.root/'common/on_action/aawc_population_warfare_on_actions.txt').read_text(encoding='utf-8-sig')
        siege = parse(definition_body(text,'aawc_population_on_siege_completion'))
        occupation = parse(definition_body(text,'aawc_population_on_county_occupied'))
        def nodes(tree):
            for key, op, arg in tree:
                yield key,op,arg
                if isinstance(arg,list): yield from nodes(arg)
        # Execute the actual holding predicates; native on_action scope routing is
        # deliberately outside this single-province VM's evidence boundary.
        siege_or = next(arg for key,_,arg in nodes(siege) if key=='OR' and ('has_holding_type','=','castle_holding') in arg)
        occupied = next(
            arg for key,_,arg in nodes(occupation)
            if key == 'every_county_province' and any(node_key == 'limit' for node_key,_,_ in arg)
        )
        occupied_limit = next(arg for key,_,arg in occupied if key=='limit')
        vm = SourceVM(self.root)
        for holding in ('castle','tribal','settlement','city','church','nomad','herder','temple_citadel','pirate_den'):
            vm.holding=holding+'_holding'
            self.assertNotEqual(vm.condition([('OR','=',siege_or)]),vm.condition(occupied_limit),holding)

    def test_epidemic_and_combined_disruption_recover_without_changing_structure_or_capacity(self):
        vm = self.vm(100)
        structure = tuple(vm.vars[CONDITION+'structural_'+d] for d in DIMENSIONS)
        capacity = vm.vars['aawc_population_expected']
        ledger = self.ledger(vm)
        for severity, loss in ((0,0),(1,15),(2,30),(3,45)):
            vm.epidemic = severity
            vm.call(CONDITION+'refresh_effective_effect')
            self.assertEqual(vm.vars[CONDITION+'effective_health'],max(0,structure[3]-loss*S))
            self.assertEqual(self.ledger(vm),ledger)
            self.assertEqual(vm.vars['aawc_population_expected'],capacity)
        vm.epidemic = 0
        vm.control = 0
        vm.county_vars = dict.fromkeys(('aawc_population_raid_growth_suppressed','aawc_population_siege_growth_suppressed'),S)
        vm.call(CONDITION+'refresh_effective_effect')
        self.assertEqual(vm.vars[CONDITION+'effective_sustenance'],structure[0]-5*S)
        self.assertEqual(vm.vars[CONDITION+'effective_opportunity'],structure[2]-2*S)
        self.assertEqual(vm.vars[CONDITION+'effective_security'],max(0,structure[4]-57*S))
        vm.control = 100
        vm.county_vars.clear()
        vm.call(CONDITION+'refresh_effective_effect')
        self.assertEqual(tuple(vm.vars[CONDITION+'effective_'+d] for d in DIMENSIONS),structure)
        self.assertEqual(self.ledger(vm),ledger)

    def test_feedback_evolves_toward_different_balances_and_125_percent_is_unsustainable(self):
        results = {}
        for label,start,score in (('excellent',6000,100),('neutral',6000,50),('poor',6000,20),('excellent_overfull',15000,100)):
            vm = self.vm(start)
            set_structural_and_refresh(vm,10000,**dict.fromkeys(DIMENSIONS,score))
            checkpoints, near_max = [], []
            for tick in range(1200):
                self.month(vm,tick)
                if tick in (0,119,299,599,899,1199):
                    births,deaths=expected_month(vm)
                    total=vm.value(P+'band_sum')
                    checkpoints.append({'month':tick+1,'population':total//S,'birth_demand':births/S,'death_demand':deaths/S})
                    if label == 'excellent':
                        # Keep the actual evolved age ledger, change only capacity.
                        vm.vars['aawc_population_expected']=total*4//5
                        vm.call(CONDITION+'refresh_effective_effect')
                        b,d=expected_month(vm)
                        self.assertLess(b,d,(label,tick,b,d))
                        near_max.append({'month':tick+1,'birth_demand':b/S,'death_demand':d/S})
                        vm.vars['aawc_population_expected']=10000*S
            results[label]={'checkpoints':checkpoints,'bands':[vm.vars[b]//S for b in BANDS]}
            if near_max: results[label]['evolved_age_profiles_at_125_percent']=near_max
        excellent=results['excellent']['checkpoints'][-1]['population']
        neutral=results['neutral']['checkpoints'][-1]['population']
        poor=results['poor']['checkpoints'][-1]['population']
        overfull=results['excellent_overfull']['checkpoints'][-1]['population']
        self.assertTrue(10000 < neutral < excellent < 12500)
        self.assertLess(poor,6000)
        self.assertLess(abs(excellent-overfull),500)
        # Bounded tail convergence, not a claimed final calibration target.
        for label in ('excellent','neutral','excellent_overfull'):
            tail=[row['population'] for row in results[label]['checkpoints'][-3:]]
            self.assertLess(max(tail)-min(tail),500)
        self.evidence['monthly_feedback_100_years']=results

    def test_real_building_upgrade_demolition_changes_balance_without_debiting_residents(self):
        military={'aawc_barracks_08','aawc_watchtowers_08'}
        improved={'aawc_cereal_fields_08','aawc_longhouses_02','aawc_infirmaries_04'}
        self.assertTrue((military|improved)<={row['building'] for row in rows()})
        vm=self.vm(4000,military)
        old_capacity=vm.vars['aawc_population_expected']
        old_balance=expected_month(vm)
        ledger=self.ledger(vm)
        vm.buildings=improved
        vm.call(CONDITION+'initialize_conditions_effect')
        upgraded_capacity=vm.vars['aawc_population_expected']
        upgraded_balance=expected_month(vm)
        self.assertEqual(self.ledger(vm),ledger)
        self.assertGreater(upgraded_capacity,old_capacity)
        self.assertGreater(upgraded_balance[0]-upgraded_balance[1],old_balance[0]-old_balance[1])
        vm.buildings=military
        vm.call(CONDITION+'initialize_conditions_effect')
        self.assertEqual(self.ledger(vm),ledger)
        self.assertEqual(vm.vars['aawc_population_expected'],old_capacity)
        self.assertEqual(expected_month(vm),old_balance)
        self.evidence['real_infrastructure_swap']={
            'population':4000,'military_capacity':old_capacity//S,'improved_capacity':upgraded_capacity//S,
            'military_birth_death_demand':[v/S for v in old_balance],
            'improved_birth_death_demand':[v/S for v in upgraded_balance],
            'improved_buildings':sorted(improved),'resident_ledger_unchanged':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='aawc-stage2-regression-') as temp:
        if args.archive:
            with zipfile.ZipFile(args.archive) as archive:
                names=archive.namelist()
                if len(names)!=len(set(names)) or archive.testzip():
                    raise RuntimeError('Duplicate entries or failed archive CRC')
                root=Path(temp).resolve()
                for name in names:
                    target=(root/name).resolve()
                    if not target.is_relative_to(root): raise RuntimeError('Unsafe archive path')
                archive.extractall(root)
            BehavioralRegression.root=root/MOD_ROOT.name
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BehavioralRegression))
        report={
            'passed':result.wasSuccessful(),'tests':result.testsRun,
            'failures':[{'test':str(test),'traceback':trace} for test,trace in result.failures+result.errors],
            'evidence_class':'SOURCE_VM_NOT_NATIVE_CK3',
            'archive':str(args.archive) if args.archive else None,
            'archive_sha256':digest(args.archive) if args.archive else None,
            'contribution_table_sha256':digest(TABLE),
            'scenarios':BehavioralRegression.evidence,
            'limitations':[
                'Five-decimal SourceVM arithmetic; native environment predicates are supplied by fixtures.',
                'The production monthly wrapper executes, with its known 27-day guard expiry explicitly supplied once per simulated month.',
                '100-year closed-holding scenarios exclude migration and native event dispatch; no final long-term calibration certification.',
                '125% checks cover fresh and six evolved mixed-age populations, not every arbitrary age composition.',
                'No installed payload, launcher, CK3 runtime, save, performance or rendered UI certification.'
            ]}
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
        return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    raise SystemExit(main())
