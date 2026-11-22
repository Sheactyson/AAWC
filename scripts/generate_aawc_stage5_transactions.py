"""Generate physical cohort/identity transaction coordination.

Packet stories own the exact Stage-1 transfer pool. No scalar population writes,
synthetic age credits, county pooling, or CaFG random conversion are permitted.
"""
from generate_aawc_stage4_transactions import BANDS


def render_transactions():
    text = '''
# Packet scope. Canonical registry ranks must already exist on source rows and
# destination-only identities. Snapshot the UNION, never discard destination
# minorities or manufacture an identity from destination ownership.
aawc_stage5_snapshot_destination_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = { NOT = { has_variable = destination_snapshot } exists = var:destination }
        set_variable = { name = destination_population value = var:destination.var:aawc_population_current }
        aawc_stage5_snapshot_destination_axis_effect = { TYPE = culture }
        aawc_stage5_snapshot_destination_axis_effect = { TYPE = faith }
        set_variable = { name = destination_snapshot value = 1 }
    }
}

aawc_stage5_snapshot_destination_axis_effect = {
    every_in_list = {
        variable = $TYPE$_rows
        save_scope_as = aawc_stage5_origin_row
        dummy_male = { create_story = { type = aawc_stage5_packet_record save_scope_as = aawc_stage5_row } }
        scope:aawc_stage5_row = {
            set_variable = { name = identity value = scope:aawc_stage5_origin_row.var:identity }
            set_variable = { name = rank value = scope:aawc_stage5_origin_row.var:rank }
            set_variable = { name = quantity value = scope:aawc_stage5_origin_row.var:quantity }
            set_variable = { name = original_factor value = 0 }
        }
        scope:aawc_stage5_packet = { add_to_variable_list = { name = destination_$TYPE$_rows target = scope:aawc_stage5_row } }
    }
    var:destination = {
        every_in_list = {
            variable = kCAFG_province_$TYPE$_structs
            save_scope_as = aawc_stage5_live_struct
            scope:aawc_stage5_packet = {
                remove_variable = union_match
                every_in_list = {
                    variable = destination_$TYPE$_rows
                    limit = { var:identity = scope:aawc_stage5_live_struct.var:$TYPE$ }
                    scope:aawc_stage5_packet = { set_variable = { name = union_match value = prev } }
                }
                if = {
                    limit = { NOT = { has_variable = union_match } }
                    dummy_male = { create_story = { type = aawc_stage5_packet_record save_scope_as = aawc_stage5_row } }
                    scope:aawc_stage5_row = {
                        set_variable = { name = identity value = scope:aawc_stage5_live_struct.var:$TYPE$ }
                        set_variable = { name = quantity value = 0 }
                        set_variable = { name = original_factor value = 0 }
                        if = {
                            limit = { var:identity = { has_variable = aawc_stage5_identity_rank } }
                            set_variable = { name = rank value = var:identity.var:aawc_stage5_identity_rank }
                        }
                    }
                    add_to_variable_list = { name = destination_$TYPE$_rows target = scope:aawc_stage5_row }
                    set_variable = { name = union_match value = scope:aawc_stage5_row }
                }
                var:union_match = {
                    if = {
                        limit = { has_variable = live_seen }
                        scope:aawc_stage5_packet = { set_variable = { name = invalid value = 1 } }
                    }
                    set_variable = { name = original_factor value = scope:aawc_stage5_live_struct.var:factor }
                    set_variable = { name = live_seen value = 1 }
                }
                remove_variable = union_match
            }
        }
    }
}

# Generic bidirectional stale-state guard. Extra/duplicate live structs and
# vanished positive rows are rejected. Empty-source repairs are accepted only
# while that live axis is still empty; they are written on commit, not staging.
aawc_stage5_check_live_axis_effect = {
    set_variable = { name = live_count value = 0 }
    $PROVINCE$ = {
        every_in_list = {
            variable = kCAFG_province_$TYPE$_structs
            save_scope_as = aawc_stage5_live_struct
            scope:aawc_stage5_packet = {
                change_variable = { name = live_count add = 1 }
                set_variable = { name = live_matches value = 0 }
                every_in_list = {
                    variable = $ROWS$_rows
                    limit = {
                        var:identity = scope:aawc_stage5_live_struct.var:$TYPE$
                        var:$FACTOR$ = scope:aawc_stage5_live_struct.var:factor
                    }
                    scope:aawc_stage5_packet = { change_variable = { name = live_matches add = 1 } }
                }
                if = {
                    limit = { NOT = { var:live_matches = 1 } }
                    set_variable = { name = stale value = 1 }
                }
            }
        }
    }
    if = {
        limit = { NOT = { AND = { $REPAIR$ = 1 var:live_count = 0 } } }
        every_in_list = {
            variable = $ROWS$_rows
            save_scope_as = aawc_stage5_checked_row
            set_variable = { name = live_matches value = 0 }
            $PROVINCE$ = {
                every_in_list = {
                    variable = kCAFG_province_$TYPE$_structs
                    limit = { var:$TYPE$ = scope:aawc_stage5_checked_row.var:identity }
                    scope:aawc_stage5_checked_row = { change_variable = { name = live_matches add = 1 } }
                }
            }
            if = {
                limit = { OR = {
                    var:live_matches > 1
                    AND = { var:$FACTOR$ > 0 NOT = { var:live_matches = 1 } }
                } }
                scope:aawc_stage5_packet = { set_variable = { name = stale value = 1 } }
            }
        }
    }
}

# Packet scope. Both endpoints are locked before any absolute debit. A packet
# story IS the persistent transaction identifier; no date/amount pseudo-ID.
aawc_stage5_reserve_transaction_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = {
            var:phase = 1 var:invalid = 0 var:source_prepared = 1
            has_variable = route_prepared
            NOT = { has_variable = transaction_reserved }
            exists = var:source exists = var:destination
            NOT = { var:source = var:destination }
            var:source = {
                NOT = { has_variable = aawc_stage5_identity_lock }
                var:aawc_population_current = scope:aawc_stage5_packet.var:source_population
                aawc_population_valid_settlement_for_cohort_trigger = yes
                aawc_reforging_round_counts_valid_value = 1
                aawc_stage4_unreserved_civilian_total >= scope:aawc_stage5_packet.var:amount
                has_variable = aawc_migration_holding_protective_floor
                var:aawc_migration_holding_protective_floor <= scope:aawc_stage5_packet.var:remaining_population
            }
            var:destination = {
                NOT = { has_variable = aawc_stage5_identity_lock }
                aawc_population_valid_settlement_for_cohort_trigger = yes
                aawc_reforging_round_counts_valid_value = 1
            }
        }
        aawc_stage5_snapshot_destination_effect = yes
        aawc_stage5_prepare_destination_credit_effect = yes
        set_variable = { name = stale value = 0 }
        aawc_stage5_check_source_snapshot_effect = yes
        if = {
            limit = { var:invalid = 0 var:stale = 0 has_variable = destination_prepared }
            var:source = { set_variable = { name = aawc_stage5_identity_lock value = scope:aawc_stage5_packet } }
            var:destination = { set_variable = { name = aawc_stage5_identity_lock value = scope:aawc_stage5_packet } }
            set_variable = { name = transaction_reserved value = 1 }
            add_to_global_variable_list = { name = aawc_stage5_pending_packets target = this }
        }
    }
}

aawc_stage5_check_source_snapshot_effect = {
    set_variable = { name = repair_allowed value = 0 }
    if = { limit = { has_variable = culture_repair } set_variable = { name = repair_allowed value = 1 } }
    aawc_stage5_check_live_axis_effect = { TYPE = culture ROWS = culture FACTOR = original_factor PROVINCE = scope:aawc_stage5_packet.var:source REPAIR = var:repair_allowed }
    set_variable = { name = repair_allowed value = 0 }
    if = { limit = { has_variable = faith_repair } set_variable = { name = repair_allowed value = 1 } }
    aawc_stage5_check_live_axis_effect = { TYPE = faith ROWS = faith FACTOR = original_factor PROVINCE = scope:aawc_stage5_packet.var:source REPAIR = var:repair_allowed }
}

# Exact AAWC age-band debit. The pool belongs to THIS packet, not a county.
# Phase is changed in the same synchronous effect as its absolute receipt.
aawc_stage5_commit_absolute_source_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = { var:phase = 1 var:invalid = 0 has_variable = transaction_reserved }
        set_variable = { name = stale value = 0 }
        aawc_stage5_check_source_snapshot_effect = yes
        if = {
            limit = {
                var:stale = 0
                var:source = {
                    var:aawc_stage5_identity_lock = scope:aawc_stage5_packet
                    var:aawc_population_current = scope:aawc_stage5_packet.var:source_population
                    aawc_reforging_round_counts_valid_value = 1
                    aawc_population_valid_settlement_for_cohort_trigger = yes
                    aawc_stage4_unreserved_civilian_total >= scope:aawc_stage5_packet.var:amount
                }
            }
            save_scope_as = aawc_reforging_transfer_pool_owner
            aawc_reforging_cohort_reset_transfer_pool_effect = yes
            var:source = {
                aawc_reforging_cohort_capture_transfer_packet_effect = { AMOUNT = scope:aawc_stage5_packet.var:amount }
            }
            set_variable = { name = absolute_debited value = var:source.var:aawc_reforging_cohort_last_transfer_debit }
            if = {
                limit = { var:absolute_debited = var:amount var:source = { var:aawc_population_current = scope:aawc_stage5_packet.var:remaining_population } }
                set_variable = { name = phase value = 2 }
            }
            else = {
                # An unexpected partial debit has no identity debt. Restore the
                # actual captured bands immediately; never credit a destination.
                var:source = { aawc_reforging_cohort_apply_transfer_packet_effect = { AMOUNT = scope:aawc_stage5_packet.var:absolute_debited } }
                if = {
                    limit = { var:source = { var:aawc_population_current = scope:aawc_stage5_packet.var:source_population } }
                    set_variable = { name = phase value = 7 }
                }
                else = { set_variable = { name = phase value = 8 } }
                set_variable = { name = invalid value = 1 }
            }
        }
        else = { set_variable = { name = invalid value = 1 } }
    }
}

# Packet scope. Check the frozen destination before using the exact age pool.
# Failure after source debt requests the existing guarded inverse, never a new
# packet or freshly recomputed provenance.
aawc_stage5_commit_absolute_destination_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = { var:phase = 3 var:invalid = 0 NOT = { has_variable = abort_requested } }
        set_variable = { name = stale value = 0 }
        aawc_stage5_check_live_axis_effect = { TYPE = culture ROWS = destination_culture FACTOR = original_factor PROVINCE = scope:aawc_stage5_packet.var:destination REPAIR = 0 }
        aawc_stage5_check_live_axis_effect = { TYPE = faith ROWS = destination_faith FACTOR = original_factor PROVINCE = scope:aawc_stage5_packet.var:destination REPAIR = 0 }
        aawc_stage5_check_pool_effect = yes
        if = {
            limit = {
                var:stale = 0 var:pool_total = var:amount
                var:destination = {
                    var:aawc_stage5_identity_lock = scope:aawc_stage5_packet
                    var:aawc_population_current = scope:aawc_stage5_packet.var:destination_population
                    aawc_population_valid_settlement_for_cohort_trigger = yes
                    aawc_reforging_round_counts_valid_value = 1
                }
            }
            save_scope_as = aawc_reforging_transfer_pool_owner
            var:destination = { aawc_reforging_cohort_apply_transfer_packet_effect = { AMOUNT = scope:aawc_stage5_packet.var:amount } }
            set_variable = { name = absolute_credited value = var:destination.var:aawc_reforging_cohort_last_transfer_credit }
            if = {
                limit = { var:absolute_credited = var:amount var:destination = { var:aawc_population_current = scope:aawc_stage5_packet.var:credited_population } }
                set_variable = { name = phase value = 4 }
            }
            else = {
                # Preserve payload and receipts for repair; never replay a
                # partial absolute credit or refund residents already delivered.
                set_variable = { name = phase value = 8 }
            }
        }
        else = { set_variable = { name = abort_requested value = 1 } }
    }
}

aawc_stage5_commit_absolute_refund_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = { var:phase = 3 OR = { var:invalid = 1 has_variable = abort_requested } }
        aawc_stage5_prepare_refund_effect = yes
        aawc_stage5_check_pool_effect = yes
        if = {
            limit = {
                has_variable = refund_prepared var:pool_total = var:amount
                var:source = {
                    var:aawc_stage5_identity_lock = scope:aawc_stage5_packet
                    aawc_population_valid_settlement_for_cohort_trigger = yes
                    aawc_reforging_round_counts_valid_value = 1
                }
            }
            save_scope_as = aawc_reforging_transfer_pool_owner
            var:source = { aawc_reforging_cohort_apply_transfer_packet_effect = { AMOUNT = scope:aawc_stage5_packet.var:amount } }
            set_variable = { name = absolute_refunded value = var:source.var:aawc_reforging_cohort_last_transfer_credit }
            if = {
                limit = { var:absolute_refunded = var:amount var:source = { var:aawc_population_current = scope:aawc_stage5_packet.var:source_population } }
                set_variable = { name = phase value = 6 }
            }
            else = { set_variable = { name = phase value = 8 } }
        }
    }
}

# Receipt replay is safe at each persisted boundary; terminal packets no-op.
aawc_stage5_execute_transaction_effect = {
    save_scope_as = aawc_stage5_packet
    aawc_stage5_reserve_transaction_effect = yes
    aawc_stage5_commit_absolute_source_effect = yes
    if = {
        limit = { var:phase = 2 has_variable = transaction_reserved }
        set_variable = { name = stale value = 0 }
        aawc_stage5_check_source_snapshot_effect = yes
        if = { limit = { var:stale = 0 } aawc_stage5_apply_source_debit_effect = yes }
    }
    aawc_stage5_commit_absolute_destination_effect = yes
    if = {
        limit = { var:phase = 4 has_variable = transaction_reserved }
        set_variable = { name = stale value = 0 }
        aawc_stage5_check_live_axis_effect = { TYPE = culture ROWS = destination_culture FACTOR = original_factor PROVINCE = scope:aawc_stage5_packet.var:destination REPAIR = 0 }
        aawc_stage5_check_live_axis_effect = { TYPE = faith ROWS = destination_faith FACTOR = original_factor PROVINCE = scope:aawc_stage5_packet.var:destination REPAIR = 0 }
        if = { limit = { var:stale = 0 } aawc_stage5_apply_destination_credit_effect = yes }
    }
    aawc_stage5_commit_absolute_refund_effect = yes
    aawc_stage5_apply_refund_effect = yes
    aawc_stage5_finish_transaction_effect = yes
}

# Queue once, after terminal reconciliation. Refunds also require a refresh
# because source setters may have repaired an empty axis.
aawc_stage5_finish_transaction_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = { OR = { var:phase = 5 var:phase = 7 } NOT = { has_variable = finished } }
        if = {
            limit = { var:phase = 5 }
            var:destination.county = { aawc_stage5_queue_county_effect = yes }
        }
        if = {
            limit = { OR = { var:phase = 5 has_variable = refund_prepared } }
            var:source.county = { aawc_stage5_queue_county_effect = yes }
        }
        aawc_stage5_unlock_transaction_effect = yes
        set_variable = { name = finished value = 1 }
    }
    if = {
        limit = { var:phase = 1 var:invalid = 1 has_variable = transaction_reserved }
        aawc_stage5_unlock_transaction_effect = yes
    }
}

aawc_stage5_unlock_transaction_effect = {
    var:source = {
        if = { limit = { var:aawc_stage5_identity_lock ?= scope:aawc_stage5_packet } remove_variable = aawc_stage5_identity_lock }
    }
    var:destination = {
        if = { limit = { var:aawc_stage5_identity_lock ?= scope:aawc_stage5_packet } remove_variable = aawc_stage5_identity_lock }
    }
    remove_list_global_variable = { name = aawc_stage5_pending_packets target = this }
}

aawc_stage5_queue_county_effect = {
    if = {
        limit = { NOT = { has_variable = aawc_stage5_refresh_queued } }
        set_variable = { name = aawc_stage5_refresh_queued value = 1 }
        add_to_global_variable_list = { name = aawc_stage5_changed_counties target = this }
    }
}

# End of the demographic/migration batch. The list is sparse and persistent;
# no every_county/every_province fallback, no per-transfer refresh.
aawc_stage5_flush_counties_effect = {
    every_in_global_list = {
        variable = aawc_stage5_changed_counties
        aawc_population_reaggregate_county_cached_effect = yes
        E_kCAFG_update_county_cultures_list = yes
        E_kCAFG_update_county_faiths_list = yes
        E_kCAFG_update_county_culture = { REASON = flag:migration }
        E_kCAFG_update_county_faith = { REASON = flag:migration }
        remove_variable = aawc_stage5_refresh_queued
    }
    every_in_global_list = {
        variable = aawc_stage5_changed_counties
        holder = { aawc_population_reaggregate_character_cached_effect = yes }
    }
    clear_global_variable_list = aawc_stage5_changed_counties
}

aawc_stage5_recover_pending_effect = {
    every_in_global_list = {
        variable = aawc_stage5_pending_packets
        aawc_stage5_execute_transaction_effect = yes
        if = { limit = { has_variable = migration_receipt } aawc_stage5_account_migration_receipt_effect = yes }
        var:source = { aawc_stage5_cleanup_packet_effect = yes }
    }
}

# Source province scope. The scheduler consumes the terminal receipt/budgets
# BEFORE cleanup. Unsettled phases, exact age pools and locks are never erased.
aawc_stage5_cleanup_packet_effect = {
    if = {
        limit = {
            has_variable = aawc_stage5_packet
            var:aawc_stage5_packet = { OR = { var:phase < 2 has_variable = finished } }
        }
        var:aawc_stage5_packet = {
            save_scope_as = aawc_stage5_packet
            if = { limit = { has_variable = transaction_reserved } aawc_stage5_unlock_transaction_effect = yes }
            every_in_list = { variable = culture_rows end_story = yes }
            every_in_list = { variable = faith_rows end_story = yes }
            every_in_list = { variable = destination_culture_rows end_story = yes }
            every_in_list = { variable = destination_faith_rows end_story = yes }
            every_in_list = {
                variable = route_candidates
                every_in_list = { variable = culture_rows end_story = yes }
                every_in_list = { variable = faith_rows end_story = yes }
                end_story = yes
            }
            end_story = yes
        }
        remove_variable = aawc_stage5_packet
    }
}
'''
    text += '\naawc_stage5_check_pool_effect = {\n    set_variable = { name = pool_total value = 0 }\n'
    for band, _ in BANDS:
        text += f'    change_variable = {{ name = pool_total add = var:aawc_reforging_transfer_{band} }}\n'
    text += '}\n'
    return text
