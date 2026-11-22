"""Build a separate, disposable native probe addon. Never ship it in AAWC."""
import argparse
from pathlib import Path


def build(out):
    files = {}
    effects = '''# Disposable probe; no packaged gameplay definitions overridden.
aawc_s5probe_seed_effect = {
    aawc_stage5_ensure_registry_effect = yes
    set_global_variable = { name = aawc_stage5_migration_batch value = 100 }
    province:4485 = { barony.holder = { set_culture = culture:andal set_character_faith = faith:fots_seven } }
    province:4485 = {
        aawc_s5probe_holding_effect = { POP = 1000 SEND = 100 RECEIVE = 0 }
        E_kCAFG_set_struct_factor = { TYPE = culture SCOPE = culture:andal FACTOR = 0.6 }
        E_kCAFG_set_struct_factor = { TYPE = culture SCOPE = culture:reachman FACTOR = 0.4 }
        E_kCAFG_set_struct_factor = { TYPE = faith SCOPE = faith:fots_seven FACTOR = 0.6 }
        E_kCAFG_set_struct_factor = { TYPE = faith SCOPE = faith:fots_blessed FACTOR = 0.4 }
    }
    province:4486 = {
        aawc_s5probe_holding_effect = { POP = 500 SEND = 0 RECEIVE = 200 }
        E_kCAFG_set_struct_factor = { TYPE = culture SCOPE = culture:andal FACTOR = 1 }
        E_kCAFG_set_struct_factor = { TYPE = faith SCOPE = faith:fots_seven FACTOR = 1 }
    }
}
aawc_s5probe_holding_effect = {
    if = { limit = { NOT = { has_holding_type = castle_holding } } set_holding_type = castle_holding }
    aawc_reforging_cohort_initialize_production_ledger_effect = { POPULATION = $POP$ }
    set_variable = { name = aawc_migration_holding_protective_floor value = 250 }
    set_variable = { name = aawc_migration_holding_county_give_cap value = 0 }
    set_variable = { name = aawc_migration_holding_county_receive_cap value = 0 }
    set_variable = { name = aawc_migration_holding_internal_give_cap value = $SEND$ }
    set_variable = { name = aawc_migration_holding_internal_receive_cap value = $RECEIVE$ }
    set_variable = { name = aawc_reforging_tx_migration_plan value = 0 }
    set_variable = { name = aawc_reforging_tx_migration_county_plan value = 0 }
    set_variable = { name = aawc_reforging_tx_migration_internal_plan value = 0 }
    remove_variable = aawc_stage5_internal_send_carry
    aawc_stage5_prepare_migration_node_effect = yes
    county = {
        set_variable = { name = aawc_migration_county_rating value = 100 }
        set_variable = { name = aawc_migration_county_actual_net value = 0 }
        remove_variable = aawc_population_warfare_growth_suppressed
        remove_variable = aawc_population_siege_growth_suppressed
        remove_variable = aawc_population_raid_growth_suppressed
    }
    E_kCAFG_clear_all_province_cultures = yes
    E_kCAFG_clear_all_province_faiths = yes
}
# Pause the real proposal/transaction path at a persistable source-debt boundary.
aawc_s5probe_midpoint_effect = {
    province:4485 = {
        save_scope_as = aawc_stage5_routing_source
        every_neighboring_province = {
            limit = { this = province:4486 }
            save_scope_as = aawc_stage5_routing_destination
            scope:aawc_stage5_routing_source = { aawc_stage5_propose_migration_effect = { KIND = internal } }
        }
        if = {
            limit = { has_variable = aawc_stage5_best_packet }
            set_variable = { name = aawc_stage5_packet value = var:aawc_stage5_best_packet }
            remove_variable = aawc_stage5_best_packet
            var:aawc_stage5_packet = {
                aawc_stage5_reserve_transaction_effect = yes
                aawc_stage5_commit_absolute_source_effect = yes
                aawc_stage5_apply_source_debit_effect = yes
            }
        }
    }
}
aawc_s5probe_prepare_effect = {
    aawc_s5probe_seed_effect = yes
    aawc_s5probe_midpoint_effect = yes
    if = {
        limit = { province:4485 = { has_variable = aawc_stage5_packet var:aawc_stage5_packet = { var:phase = 3 } var:aawc_population_current = 900 } province:4486 = { var:aawc_population_current = 500 } }
        error_log = "AAWC S5 LIVE native registry adjacency phase3 PASS"
        set_global_variable = { name = aawc_s5probe_step value = 1 }
        province:4485 = {
            every_in_list = { variable = kCAFG_province_culture_structs set_variable = { name = probe_before value = var:factor } }
            every_in_list = { variable = kCAFG_province_faith_structs set_variable = { name = probe_before value = var:factor } }
            remove_variable = aawc_reforging_cohort_monthly_tick_recent
            aawc_reforging_cohort_apply_production_month_effect = yes
            E_kCAFG_set_struct_factor = { TYPE = culture SCOPE = culture:andal FACTOR = 0.2 }
            E_kCAFG_set_struct_factor = { TYPE = faith SCOPE = faith:fots_seven FACTOR = 0.2 }
            if = {
                limit = { var:aawc_population_current = 900 NOT = { any_in_list = { variable = kCAFG_province_culture_structs NOT = { var:factor = var:probe_before } } } NOT = { any_in_list = { variable = kCAFG_province_faith_structs NOT = { var:factor = var:probe_before } } } }
                error_log = "AAWC S5 LIVE locked demographic and CaFG guard PASS"
            }
            else = { error_log = "AAWC S5 LIVE locked guard FAIL" }
        }
    }
    else = { error_log = "AAWC S5 LIVE native registry adjacency phase3 FAIL" }
}
aawc_s5probe_finish_effect = {
    aawc_stage5_recover_pending_effect = yes
    aawc_stage5_recover_pending_effect = yes
    if = {
        limit = {
            province:4485 = { var:aawc_population_current = 900 var:aawc_stage5_internal_send_remaining = 0 NOT = { has_variable = aawc_stage5_packet } NOT = { has_variable = aawc_stage5_identity_lock } }
            province:4486 = { var:aawc_population_current = 600 var:aawc_stage5_internal_receive_remaining = 100 NOT = { has_variable = aawc_stage5_identity_lock } }
        }
        error_log = "AAWC S5 LIVE persisted global recovery budget retry PASS"
        set_global_variable = { name = aawc_s5probe_step value = 2 }
    }
    else = { error_log = "AAWC S5 LIVE persisted recovery FAIL" }
    set_global_variable = { name = aawc_s5probe_queue_count value = 0 }
    every_in_global_list = { variable = aawc_stage5_changed_counties change_global_variable = { name = aawc_s5probe_queue_count add = 1 } }
    if = { limit = { global_var:aawc_s5probe_queue_count = 1 } error_log = "AAWC S5 LIVE sparse shared county dedup PASS" }
    else = { error_log = "AAWC S5 LIVE sparse shared county dedup FAIL" }
    aawc_stage5_flush_counties_effect = yes
}
aawc_s5probe_scenarios_effect = {
    # Same production entry called twice; the second call has no budget to spend.
    aawc_s5probe_seed_effect = yes
    province:4485 = { aawc_stage5_route_migration_source_effect = { KIND = internal } aawc_stage5_route_migration_source_effect = { KIND = internal } }
    if = { limit = { province:4485 = { var:aawc_population_current = 900 var:aawc_stage5_internal_send_remaining = 0 } province:4486 = { var:aawc_population_current = 600 } } error_log = "AAWC S5 LIVE full native route retry PASS" }
    else = { error_log = "AAWC S5 LIVE full native route retry FAIL" }
    aawc_stage5_flush_counties_effect = yes
    # A mismatched peaceful destination cannot receive either identity packet.
    aawc_s5probe_seed_effect = yes
    province:4486 = {
        E_kCAFG_clear_all_province_cultures = yes E_kCAFG_clear_all_province_faiths = yes
        E_kCAFG_set_struct_factor = { TYPE = culture SCOPE = culture:high_valyrian FACTOR = 1 }
        E_kCAFG_set_struct_factor = { TYPE = faith SCOPE = faith:drowned_god FACTOR = 1 }
    }
    province:4485 = { aawc_stage5_route_migration_source_effect = { KIND = internal } }
    if = { limit = { province:4485 = { var:aawc_population_current = 1000 var:aawc_stage5_internal_send_remaining = 100 NOT = { has_variable = aawc_stage5_packet } } province:4486 = { var:aawc_population_current = 500 } } error_log = "AAWC S5 LIVE peaceful mismatch no-op PASS" }
    else = { error_log = "AAWC S5 LIVE peaceful mismatch no-op FAIL" }
    # Both endpoints war affected: fourth-tier fallback is allowed.
    province:4485 = { county = { set_variable = { name = aawc_population_siege_growth_suppressed value = 1 } } aawc_stage5_route_migration_source_effect = { KIND = internal } }
    if = { limit = { province:4485 = { var:aawc_population_current = 900 } province:4486 = { var:aawc_population_current = 600 } } error_log = "AAWC S5 LIVE war mismatch route PASS" }
    else = { error_log = "AAWC S5 LIVE war mismatch route FAIL" }
    aawc_stage5_flush_counties_effect = yes
    # Abort after debt, retry refund twice. It must not consume physical budgets.
    aawc_s5probe_seed_effect = yes
    aawc_s5probe_midpoint_effect = yes
    province:4485 = {
        if = { limit = { has_variable = aawc_stage5_packet }
            var:aawc_stage5_packet = { set_variable = { name = abort_requested value = 1 } }
        }
    }
    aawc_stage5_recover_pending_effect = yes aawc_stage5_recover_pending_effect = yes
    if = { limit = { province:4485 = { var:aawc_population_current = 1000 var:aawc_stage5_internal_send_remaining = 100 NOT = { has_variable = aawc_stage5_packet } NOT = { has_variable = aawc_stage5_identity_lock } } province:4486 = { var:aawc_population_current = 500 var:aawc_stage5_internal_receive_remaining = 200 } } error_log = "AAWC S5 LIVE guarded refund retry PASS" }
    else = { error_log = "AAWC S5 LIVE guarded refund retry FAIL" }
    aawc_stage5_flush_counties_effect = yes
    # Run actual monthly births/deaths/aging, with both identity surfaces frozen.
    province:4485 = {
        aawc_reforging_cohort_initialize_production_ledger_effect = { POPULATION = 100000 }
        every_in_list = { variable = kCAFG_province_culture_structs set_variable = { name = probe_before value = var:factor } }
        every_in_list = { variable = kCAFG_province_faith_structs set_variable = { name = probe_before value = var:factor } }
        remove_variable = aawc_reforging_cohort_monthly_tick_recent
        aawc_reforging_cohort_apply_production_month_effect = yes
        if = { limit = { var:aawc_reforging_cohort_last_births > 0 var:aawc_reforging_cohort_last_deaths > 0 var:aawc_reforging_cohort_last_aged > 0 } error_log = "AAWC S5 LIVE positive births deaths aging PASS" }
        else = { error_log = "AAWC S5 LIVE positive births deaths aging FAIL" }
        if = { limit = { has_variable = aawc_reforging_cohort_monthly_tick_recent NOT = { any_in_list = { variable = kCAFG_province_culture_structs NOT = { var:factor = var:probe_before } } } NOT = { any_in_list = { variable = kCAFG_province_faith_structs NOT = { var:factor = var:probe_before } } } } error_log = "AAWC S5 LIVE demographic ratios neutral PASS" }
        else = { error_log = "AAWC S5 LIVE demographic ratios neutral FAIL" }
    }
    set_global_variable = { name = aawc_s5probe_step value = 3 }
}
aawc_s5probe_world_effect = {
    # Pin capacity only in this disposable fixture, so the real diagnostics
    # produce a nonzero outward/receiving pair rather than a vacuous no-op.
    province:4485 = { set_variable = { name = aawc_population_expected value = 1000 } }
    province:4486 = { set_variable = { name = aawc_population_expected value = 10000 } }
    province:4485 = { county = { aawc_population_reaggregate_county_cached_effect = yes } }
    province:4485 = { set_variable = { name = aawc_s5probe_world_before value = var:aawc_population_current } }
    province:4486 = { set_variable = { name = aawc_s5probe_world_before value = var:aawc_population_current } }
    error_log = "AAWC S5 LIVE production world BEGIN"
    set_global_variable = { name = aawc_s5probe_population_before value = 0 }
    every_county = { every_county_province = { limit = { has_variable = aawc_population_current } change_global_variable = { name = aawc_s5probe_population_before add = var:aawc_population_current } } }
    aawc_migration_update_world_effect = yes
    set_global_variable = { name = aawc_s5probe_population_after value = 0 }
    every_county = { every_county_province = { limit = { has_variable = aawc_population_current } change_global_variable = { name = aawc_s5probe_population_after add = var:aawc_population_current } } }
    if = { limit = { global_var:aawc_s5probe_population_before = global_var:aawc_s5probe_population_after } error_log = "AAWC S5 LIVE production world conservation PASS" }
    else = { error_log = "AAWC S5 LIVE production world conservation FAIL" }
    if = { limit = { province:4485 = { var:aawc_population_current < var:aawc_s5probe_world_before } province:4486 = { var:aawc_population_current > var:aawc_s5probe_world_before } } error_log = "AAWC S5 LIVE production world moved residents PASS" }
    else = { error_log = "AAWC S5 LIVE production world moved residents FAIL" }
    set_global_variable = { name = aawc_s5probe_step value = 4 }
    error_log = "AAWC S5 LIVE production world END"
}
'''
    files['common/scripted_effects/aawc_s5probe_effects.txt'] = effects
    decisions, events, loc = [], ['namespace = aawc_s5probe'], ['l_english:']
    for index, (name, label) in enumerate((('prepare', 'Prepare native midpoint'), ('finish', 'Recover saved midpoint'), ('scenarios', 'Run native scenarios'), ('world', 'Run production world')), 1):
        stage = 'NOT = { has_global_variable = aawc_s5probe_step }' if index == 1 else f'global_var:aawc_s5probe_step ?= {index-1}'
        decisions.append(f'''aawc_s5probe_{name}_decision = {{
 picture = {{ reference = "gfx/interface/illustrations/decisions/decision_realm.dds" }}
 desc = aawc_s5probe_desc selection_tooltip = aawc_s5probe_desc confirm_text = aawc_s5probe_confirm
 ai_check_interval = 0
 is_shown = {{ is_ai = no {stage} }} is_valid = {{ is_ai = no }}
 effect = {{ hidden_effect = {{ trigger_event = {{ id = aawc_s5probe.{index} }} }} }}
 ai_potential = {{ always = no }} ai_will_do = {{ base = 0 }}
}}''')
        events.append(f'aawc_s5probe.{index} = {{ type = character_event hidden = yes immediate = {{ aawc_s5probe_{name}_effect = yes }} }}')
        loc.append(f' aawc_s5probe_{name}_decision:0 "Stage 5: {label}"')
    loc += [' aawc_s5probe_desc:0 "Disposable native Stage 5 acceptance probe. Save and reload the midpoint before recovery. This changes only this isolated campaign."', ' aawc_s5probe_confirm:0 "Run probe"']
    files['common/decisions/aawc_s5probe_decisions.txt'] = '\n'.join(decisions)+'\n'
    files['events/aawc_s5probe_events.txt'] = '\n'.join(events)+'\n'
    files['localization/english/aawc_s5probe_l_english.yml'] = '\n'.join(loc)+'\n'
    files['descriptor.mod'] = 'name="AAWC Stage 5 Native Probe"\nversion="1"\nsupported_version="1.19.0.6"\n'
    for relative, text in files.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8-sig', newline='\n')
    print(f'Wrote {len(files)} disposable addon files to {out}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    build(parser.parse_args().out)
