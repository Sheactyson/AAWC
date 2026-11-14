"""Focused source-executing Stage 2 conditions/capacity acceptance (not CK3).

Uses the fail-closed fixedpoint VM and real generated contributions. Oracles test
design invariants and independent arithmetic, not a second demographic simulator.
"""
from decimal import Decimal
from pathlib import Path
import re
import unittest

from generate_aawc_stage2_conditions import DIMENSIONS, FIELDS, OUTPUT, rows, render, effective_buildings
from test_aawc_cohort_bounded_arithmetic import SourceVM, S, P, parse
from validate_aawc_reforging_stage1_cohort_engine import BANDS, MOD_ROOT, definition_body

PREFIX = 'aawc_stage2_'
EXPECTED_UPSTREAM_BUILDINGS = {
    *(f'capital_bureau_{tier:02}' for tier in range(1, 9)),
    *(f'oath_faithful_building_{tier:02}' for tier in range(1, 5)),
    *(f'oath_poor_building_{tier:02}' for tier in range(1, 5)),
    *(f'oath_warriors_building_{tier:02}' for tier in range(1, 5)),
}


def source(rel):
    return (MOD_ROOT / rel).read_text(encoding='utf-8-sig')


def scores(vm, layer):
    return tuple(vm.vars[PREFIX + layer + '_' + dim] / S for dim in DIMENSIONS)


def rebuild(vm):
    vm.call(PREFIX + 'initialize_conditions_effect')


def fixture(holding='city_holding', buildings=(), terrain=(), total=100):
    vm = SourceVM()
    vm.holding, vm.buildings, vm.terrains = holding, set(buildings), set(terrain)
    vm.initialize(total)
    return vm


class ConditionsAcceptance(unittest.TestCase):
    def test_generated_source_and_effective_building_ids(self):
        records = rows()
        self.assertEqual(OUTPUT.read_text(encoding='utf-8-sig'), render(records))
        available = effective_buildings()
        legacy_ids = {r['legacy_building'] for r in records if r['legacy_building']}
        self.assertEqual(legacy_ids - available.keys(), EXPECTED_UPSTREAM_BUILDINGS)
        self.assertEqual(sum(not r['legacy_building'] for r in records), 155)
        self.assertEqual(len(records), 771)
        flags = set(re.findall(r'\bflag\s*=\s*(\w+)', '\n'.join(b for _, b in available.values())))
        used = set(re.findall(r'has_building_with_flag = (\w+)', source('common/scripted_effects/aawc_stage2_condition_effects.txt')))
        self.assertTrue(used <= flags, used - flags)

    def test_every_eligible_holding_initializes_twelve_bounded_scores(self):
        for holding in ('castle', 'tribal', 'city', 'church', 'nomad', 'herder', 'temple_citadel', 'pirate_den', 'settlement'):
            with self.subTest(holding=holding):
                vm = fixture(holding + '_holding')
                for layer in ('structural', 'effective'):
                    self.assertTrue(all(0 <= x <= 100 for x in scores(vm, layer)))
                self.assertTrue(all(40 <= x <= 60 for x in scores(vm, 'structural')))
                self.assertGreater(vm.vars['aawc_population_expected'], 0)
                self.assertEqual(vm.vars['aawc_population_current'], 100*S)

    def test_readonly_inputs_and_neutral_fallback(self):
        vm = SourceVM()
        for dim in DIMENSIONS:
            self.assertEqual(vm.value(f'aawc_reforging_stage2_{dim}_input'), 50*S)
        self.assertEqual(vm.vars, {})
        vm.initialize()
        for i, dim in enumerate(DIMENSIONS):
            vm.vars[PREFIX+'effective_'+dim] = (11+i)*S
            self.assertEqual(vm.value(f'aawc_reforging_stage2_{dim}_input'), (11+i)*S)

    def test_contribution_interface_independence_and_clamping(self):
        vm = fixture()
        before = scores(vm, 'structural')
        params = {field.upper(): 0 for field in FIELDS}
        params['AMENITIES'] = 7
        vm.call(PREFIX+'add_contribution_effect', **params)
        self.assertEqual(scores(vm, 'structural'), (*before[:5], before[5]+7))
        for index, dim in enumerate(DIMENSIONS):
            vm.vars[PREFIX+'structural_'+dim] = (-100 if index%2 else 200)*S
        vm.call(PREFIX+'refresh_effective_effect')
        self.assertTrue(all(0 <= x <= 100 for x in scores(vm, 'effective')))
        vm.buildings = {r['building'] for r in rows()}
        rebuild(vm)
        self.assertTrue(all(0 <= x <= 100 for x in scores(vm, 'structural')))
        self.assertGreater(vm.vars['aawc_population_expected'], 0)

    def test_real_building_purposes_and_tradeoffs(self):
        base = fixture()
        farm, hospice, market, military, mine, homes = [fixture(buildings=(name,)) for name in
            ('aawc_cereal_fields_01', 'aawc_infirmaries_01', 'aawc_trade_guilds_01',
             'aawc_barracks_08', 'aawc_quarries_08', 'aawc_village_cottages_01')]
        neutral = scores(base, 'structural')
        self.assertGreater(scores(farm, 'structural')[0], neutral[0])
        self.assertEqual(scores(farm, 'structural')[3], neutral[3])
        self.assertGreater(scores(hospice, 'structural')[3], neutral[3])
        self.assertEqual(hospice.vars['aawc_population_expected'], base.vars['aawc_population_expected'])
        self.assertGreater(scores(market, 'structural')[2], neutral[2])
        self.assertEqual(market.vars['aawc_population_expected'], base.vars['aawc_population_expected'])
        self.assertGreater(scores(military, 'structural')[4], neutral[4])
        self.assertLess(military.vars['aawc_population_expected'], base.vars['aawc_population_expected'])
        self.assertGreater(scores(mine, 'structural')[2], neutral[2])
        self.assertLess(scores(mine, 'structural')[3], neutral[3])
        self.assertGreater(homes.vars['aawc_population_expected'], farm.vars['aawc_population_expected'])

    def test_highest_building_level_only_and_independent_chains(self):
        vm = fixture(buildings=('aawc_cereal_fields_08', 'aawc_cereal_fields_01'))
        high = fixture(buildings=('aawc_cereal_fields_08',))
        self.assertEqual(scores(vm, 'structural'), scores(high, 'structural'))
        vm.buildings.add('aawc_infirmaries_04')
        rebuild(vm)
        self.assertGreater(scores(vm, 'structural')[3], scores(high, 'structural')[3])
        self.assertEqual(scores(vm, 'structural')[0], scores(high, 'structural')[0])

    def test_duchy_special_and_dependencies_contributions(self):
        plain = fixture()
        for building, dim in [('aawc_glass_gardens_01', 0),
                              ('aawc_duchy_grand_hospital_01', 3),
                              ('aawc_duchy_grand_harbor_01', 2)]:
            vm = fixture(buildings=(building,))
            self.assertGreater(scores(vm, 'structural')[dim], scores(plain, 'structural')[dim])

    def test_capacity_housing_food_only_and_explicit_space(self):
        vm = fixture()
        for dim in DIMENSIONS: vm.vars[PREFIX+'structural_'+dim] = 50*S
        base = vm.value(PREFIX+'physical_capacity')
        self.assertEqual(base, vm.value('aawc_population_holding_main_line_expected_capacity'))
        for dim in ('health', 'opportunity', 'security', 'amenities'):
            vm.vars[PREFIX+'structural_'+dim] = 100*S
            self.assertEqual(vm.value(PREFIX+'physical_capacity'), base)
        vm.vars[PREFIX+'structural_sustenance'] = 60*S
        food = vm.value(PREFIX+'physical_capacity') - base
        vm.vars[PREFIX+'structural_sustenance'] = 50*S
        vm.vars[PREFIX+'structural_habitation'] = 60*S
        homes = vm.value(PREFIX+'physical_capacity') - base
        self.assertEqual(homes, food*4)
        vm.vars[PREFIX+'space_percent'] = -20*S
        self.assertLess(vm.value(PREFIX+'physical_capacity'), base)

    def test_geography_main_building_development_and_blockers(self):
        plain = fixture()
        mountain = fixture(terrain=('mountains',))
        fertile = fixture(terrain=('farmlands',))
        self.assertLess(mountain.vars['aawc_population_expected'], plain.vars['aawc_population_expected'])
        self.assertGreater(fertile.vars['aawc_population_expected'], plain.vars['aawc_population_expected'])
        developed = fixture(buildings=('city_04',))
        developed.development = 50
        rebuild(developed)
        self.assertGreater(developed.vars['aawc_population_expected'], plain.vars['aawc_population_expected'])
        plain.building_flags.add('aawc_blocker_category_blight_famine_barren_wastes')
        before = scores(plain, 'structural')
        rebuild(plain)
        self.assertEqual(scores(plain, 'structural')[0], before[0]-12)
        self.assertEqual(scores(plain, 'structural')[1:], before[1:])

    def test_progressive_pressure_normal_crowded_and_far_over_capacity(self):
        vm = fixture(total=0)
        for dim in DIMENSIONS: vm.vars[PREFIX+'structural_'+dim] = 100*S
        vm.vars['aawc_population_expected'] = 10000*S
        prev_h, prev_health = 101, 101
        for occupancy in (0, .6, .8, .9, 1, 1.1, 1.25, 1.5, 2, 10):
            vm.vars[BANDS[0]] = int(10000*occupancy)*S
            residents = {k: vm.vars[k] for k in BANDS}
            vm.call(PREFIX+'refresh_effective_effect')
            h, health = scores(vm, 'effective')[1], scores(vm, 'effective')[3]
            self.assertLessEqual(h, prev_h)
            self.assertLessEqual(health, prev_health)
            self.assertEqual({k: vm.vars[k] for k in BANDS}, residents)
            self.assertEqual(scores(vm, 'structural'), (100,)*6)
            self.assertEqual(tuple(scores(vm, 'effective')[i] for i in (0,2,4,5)), (100,)*4)
            if occupancy == .6: self.assertEqual((h,health), (100,100))
            if occupancy == 1: self.assertEqual((h,health), (78,96))
            if occupancy == 1.25: self.assertEqual((h,health), (5.5,77.25))
            prev_h, prev_health = h, health
        self.assertEqual(vm.vars[PREFIX+'occupancy_ratio'], 10*S)

    def test_pressure_continuity_around_onset_and_capacity(self):
        vm = fixture(total=0)
        vm.vars['aawc_population_expected'] = 100000*S
        for boundary in (80000, 90000, 100000, 125000):
            vm.vars[BANDS[0]] = (boundary-1)*S
            before = vm.value(PREFIX+'housing_pressure_loss')
            vm.vars[BANDS[0]] = (boundary+1)*S
            after = vm.value(PREFIX+'housing_pressure_loss')
            self.assertGreaterEqual(after, before)
            self.assertLess(after-before, S/50)

    def test_crises_separate_from_structure_recover_and_never_debit(self):
        vm = fixture()
        structure = scores(vm, 'structural')
        ledger = {k:v for k,v in vm.vars.items() if k.startswith('aawc_reforging_')}
        vm.epidemic, vm.control = 3, 0
        vm.county_vars['aawc_population_raid_growth_suppressed'] = S
        vm.call(PREFIX+'refresh_effective_effect')
        self.assertEqual(scores(vm, 'structural'), structure)
        self.assertEqual(scores(vm, 'effective')[3], max(structure[3]-45,0))
        self.assertLess(scores(vm, 'effective')[4], structure[4])
        self.assertEqual(scores(vm, 'effective')[0], structure[0]-2)
        self.assertEqual(scores(vm, 'effective')[2], structure[2]-2)
        self.assertEqual({k:v for k,v in vm.vars.items() if k.startswith('aawc_reforging_')}, ledger)
        vm.epidemic, vm.control = 0, 100
        vm.county_vars.clear()
        vm.call(PREFIX+'refresh_effective_effect')
        self.assertEqual(scores(vm, 'effective'), structure)

    def test_war_and_county_vs_direct_disruptions_are_distinct(self):
        vm = fixture()
        structure = scores(vm, 'structural')
        ledger = {k:v for k,v in vm.vars.items() if k.startswith('aawc_reforging_')}

        vm.at_war = True
        vm.call(PREFIX+'refresh_effective_effect')
        war = scores(vm, 'effective')
        self.assertEqual(war[2], structure[2]-4)
        self.assertEqual(war[4], structure[4]-5)
        self.assertEqual(tuple(war[i] for i in (0,1,3,5)), tuple(structure[i] for i in (0,1,3,5)))

        vm.at_war = False
        vm.county_vars['aawc_population_siege_growth_suppressed'] = S
        vm.call(PREFIX+'refresh_effective_effect')
        county_siege = scores(vm, 'effective')
        self.assertEqual(county_siege[0], structure[0]-3)
        self.assertEqual(county_siege[4], structure[4]-12)
        self.assertEqual(tuple(county_siege[i] for i in (1,2,3,5)), tuple(structure[i] for i in (1,2,3,5)))

        vm.vars['aawc_population_direct_siege_disrupted'] = S
        vm.call(PREFIX+'refresh_effective_effect')
        direct_siege = scores(vm, 'effective')
        self.assertEqual(direct_siege[0], structure[0]-10)
        self.assertEqual(direct_siege[3], structure[3]-5)
        self.assertEqual(direct_siege[4], structure[4]-32)
        self.assertLess(direct_siege[4], county_siege[4])

        vm.county_vars.clear()
        vm.vars.pop('aawc_population_direct_siege_disrupted')
        vm.county_vars['aawc_population_raid_growth_suppressed'] = S
        vm.call(PREFIX+'refresh_effective_effect')
        county_raid = scores(vm, 'effective')
        self.assertEqual((county_raid[0], county_raid[2], county_raid[4]),
                         (structure[0]-2, structure[2]-2, structure[4]-10))

        vm.vars['aawc_population_direct_raid_disrupted'] = S
        vm.call(PREFIX+'refresh_effective_effect')
        direct_raid = scores(vm, 'effective')
        self.assertEqual((direct_raid[0], direct_raid[2], direct_raid[4]),
                         (structure[0]-7, structure[2]-5, structure[4]-28))
        self.assertLess(direct_raid[4], county_raid[4])
        self.assertEqual({k:v for k,v in vm.vars.items() if k.startswith('aawc_reforging_')}, ledger)

    def test_rebuild_after_building_loss_and_repeat_refresh_is_idempotent(self):
        vm = fixture(buildings=('longhouses_02', 'hospices_08'))
        old_capacity = vm.vars['aawc_population_expected']
        before = dict(vm.vars)
        rebuild(vm)
        self.assertEqual(vm.vars, before)
        vm.buildings.clear()
        rebuild(vm)
        self.assertLess(vm.vars['aawc_population_expected'], old_capacity)
        self.assertEqual(vm.vars['aawc_population_current'], 100*S)

    def test_ineligible_lifecycle_clears_condition_mirrors(self):
        vm = fixture()
        vm.valid_settlement = False
        vm.call(P+'clear_ineligible_settlement_effect')
        self.assertFalse(any(k.startswith(PREFIX) for k in vm.vars))
        self.assertEqual(vm.value(PREFIX+'physical_capacity'), 0)

    def test_source_lifecycle_order_and_no_second_crowding_penalty(self):
        pop = source('common/scripted_effects/aawc_population_effects.txt')
        monthly = definition_body(pop, 'aawc_population_apply_holding_monthly_growth_effect')
        self.assertLess(monthly.index('mark_holding_static_dirty_effect'), monthly.index('update_holding_dynamic_effect'))
        self.assertLess(monthly.index('update_holding_dynamic_effect'), monthly.index('apply_production_month_effect'))
        self.assertGreater(monthly.index('aawc_stage2_refresh_effective_effect'), monthly.index('apply_production_month_effect'))
        recovery = definition_body(pop, 'aawc_population_apply_county_holding_cadence_recovery_effect')
        self.assertLess(recovery.index('update_holding_dynamic_effect'), recovery.index('apply_production_month_effect'))
        dynamic = definition_body(pop, 'aawc_population_update_holding_dynamic_effect')
        self.assertNotIn('aawc_population_expected_pressure_percent <', dynamic)
        self.assertIn('name = aawc_population_expected_pressure_multiplier value = 1', dynamic)
        cache = source('common/scripted_effects/zz_aawc_population_cache_effects.txt')
        self.assertLess(cache.index('aawc_stage2_refresh_structural_effect'), cache.index('name = aawc_population_expected'))
        conditions = source('common/scripted_effects/aawc_stage2_condition_effects.txt')
        self.assertNotRegex(conditions, r'(?:set|change)_variable\s*=\s*\{\s*name\s*=\s*aawc_(?:population_current|reforging_cohort_age_)')
        self.assertNotIn('set_population_target_effect', conditions)

    def test_legacy_capacity_contract_and_integrated_rate_boundary(self):
        vm = fixture(buildings=('barracks_08',), terrain=('mountains',))
        capacity = vm.value('aawc_population_holding_expected')
        self.assertEqual(capacity, vm.vars['aawc_population_expected'])
        self.assertEqual(capacity, vm.value('aawc_population_holding_main_line_expected_capacity') + vm.value('aawc_population_holding_building_expected_capacity'))
        self.assertLess(vm.value('aawc_population_holding_building_expected_capacity'), 0)
        self.assertEqual(
            vm.value('aawc_reforging_stage2_birth_rate_multiplier'),
            vm.value('aawc_reforging_stage2_birth_habitation_factor')
            * vm.value('aawc_reforging_stage2_birth_sustenance_factor') // S
            * vm.value('aawc_reforging_stage2_birth_opportunity_factor') // S
            * vm.value('aawc_reforging_stage2_birth_security_factor') // S,
        )
        self.assertNotEqual(vm.value('aawc_reforging_stage2_birth_rate_multiplier'), S)
        self.assertEqual(vm.value('aawc_reforging_stage2_mortality_rate_multiplier'), S)
        self.assertNotEqual(vm.value('aawc_reforging_stage2_mortality_multiplier_age_00_04'), S)

    def test_environment_signature_detects_conversion_and_terrain_change(self):
        vm = fixture()
        before = vm.value(PREFIX+'environment_signature')
        vm.holding = 'castle_holding'
        self.assertNotEqual(vm.value(PREFIX+'environment_signature'), before)
        before = vm.value(PREFIX+'environment_signature')
        vm.buildings.add('castle_04')
        self.assertNotEqual(vm.value(PREFIX+'environment_signature'), before)
        vm.terrains = {'farmlands'}
        before = vm.value(PREFIX+'environment_signature')
        vm.terrains = {'floodplains'}
        self.assertNotEqual(vm.value(PREFIX+'environment_signature'), before)
        dynamic = definition_body(source('common/scripted_effects/aawc_population_effects.txt'), 'aawc_population_update_holding_dynamic_effect')
        self.assertIn('NOT = { var:aawc_stage2_environment_snapshot = var:aawc_stage2_environment_current }', dynamic)

    def test_conversion_uses_new_capacity_only_with_explicit_conversion_marker(self):
        vm = fixture(holding='castle_holding', total=20000)
        name = 'aawc_population_cap_tribal_to_feudal_conversion_effect'
        vm.effects[name] = parse(definition_body(source('common/scripted_effects/aawc_population_effects.txt'), name))
        vm.call(name)
        self.assertEqual(vm.vars['aawc_population_current'], 20000*S)
        capacity = vm.vars['aawc_population_expected']
        vm.vars['aawc_population_preconversion_tribal'] = S
        vm.call(name)
        self.assertEqual(vm.vars['aawc_population_current'], (capacity//(2*S))*S)
        self.assertEqual(vm.vars['aawc_population_last_transaction_class'], 7*S)


if __name__ == '__main__':
    unittest.main(verbosity=2)
