"""Destination reconciliation and guarded rollback for persistent packets.

Destination union rows are supplied by the registry/snapshot caller. This module
validates their correspondence to the frozen packet before accepting them.
No absolute transaction or production routing is performed here.
"""


def render_settlement():
    return '''
# Packet scope; destination_{culture,faith}_rows contain the union of existing
# destination identities and packet identities (including zero-factor entries).
# The caller snapshots destination_population before its absolute receipt.
aawc_stage5_prepare_destination_credit_effect = {
    if = {
        limit = { OR = { var:phase = 1 var:phase = 3 } var:invalid = 0 }
        save_scope_as = aawc_stage5_packet
        remove_variable = destination_prepared
        set_variable = { name = whole_destination_population value = { value = var:destination_population floor = yes } }
        if = {
            limit = {
                OR = {
                    var:destination_population < 0
                    NOT = { var:destination_population = var:whole_destination_population }
                }
            }
            set_variable = { name = invalid value = 1 }
        }
        set_variable = { name = credited_population value = var:destination_population }
        change_variable = { name = credited_population add = var:amount }
        aawc_stage5_prepare_destination_axis_effect = { TYPE = culture }
        aawc_stage5_prepare_destination_axis_effect = { TYPE = faith }
        if = {
            limit = { var:invalid = 0 }
            set_variable = { name = destination_prepared value = 1 }
        }
    }
}

aawc_stage5_prepare_destination_axis_effect = {
    aawc_stage5_validate_ranks_effect = { TYPE = destination_$TYPE$ }
    set_variable = { name = destination_factor_total value = 0 }
    set_variable = { name = destination_quantity_total value = 0 }
    every_in_list = {
        variable = destination_$TYPE$_rows
        save_scope_as = aawc_stage5_destination_row
        set_variable = { name = matched_quantity value = 0 }
        set_variable = { name = matches value = 0 }
        scope:aawc_stage5_packet = {
            every_in_list = {
                variable = $TYPE$_rows
                limit = { var:identity = scope:aawc_stage5_destination_row.var:identity }
                scope:aawc_stage5_destination_row = {
                    set_variable = { name = matched_quantity value = prev.var:quantity }
                    change_variable = { name = matches add = 1 }
                }
            }
        }
        if = {
            limit = {
                OR = {
                    var:matches > 1
                    var:original_factor < 0
                    var:quantity < 0
                    NOT = { var:quantity = var:matched_quantity }
                }
            }
            scope:aawc_stage5_packet = { set_variable = { name = invalid value = 1 } }
        }
        # Duplicate identities invalidate even if ranks differ.
        scope:aawc_stage5_packet = {
            every_in_list = {
                variable = destination_$TYPE$_rows
                limit = {
                    NOT = { this = scope:aawc_stage5_destination_row }
                    var:identity = scope:aawc_stage5_destination_row.var:identity
                }
                scope:aawc_stage5_packet = { set_variable = { name = invalid value = 1 } }
            }
        }
        set_variable = { name = mass value = var:original_factor }
        change_variable = { name = mass multiply = scope:aawc_stage5_packet.var:destination_population }
        change_variable = { name = mass add = var:quantity }
        scope:aawc_stage5_packet = {
            change_variable = { name = destination_factor_total add = prev.var:original_factor }
            change_variable = { name = destination_quantity_total add = prev.var:quantity }
        }
        remove_variable = matched_quantity
        remove_variable = matches
    }
    if = {
        limit = {
            OR = {
                NOT = { var:destination_quantity_total = var:amount }
                AND = { var:destination_population > 0 NOT = { var:destination_factor_total = 1 } }
                AND = {
                    var:destination_population = 0
                    NOT = { var:destination_factor_total = 0 }
                    NOT = { var:destination_factor_total = 1 }
                }
            }
        }
        set_variable = { name = invalid value = 1 }
    }
    if = {
        limit = { var:invalid = 0 }
        aawc_stage5_normalize_rows_effect = {
            TYPE = destination_$TYPE$
            DENOMINATOR = scope:aawc_stage5_packet.var:credited_population
        }
    }
}

# Phase 4 is set ONLY by a successful exact absolute credit receipt.
aawc_stage5_apply_destination_credit_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = {
            var:phase = 4 var:invalid = 0 var:destination_prepared = 1
            var:destination = { var:aawc_population_current = scope:aawc_stage5_packet.var:credited_population }
        }
        aawc_stage5_write_destination_axis_effect = { TYPE = culture }
        aawc_stage5_write_destination_axis_effect = { TYPE = faith }
        set_variable = { name = phase value = 5 }
    }
}

aawc_stage5_write_destination_axis_effect = {
    every_in_list = {
        variable = destination_$TYPE$_rows
        save_scope_as = aawc_stage5_write_row
        scope:aawc_stage5_packet.var:destination = {
            E_kCAFG_set_struct_factor = {
                TYPE = $TYPE$
                SCOPE = scope:aawc_stage5_write_row.var:identity
                FACTOR = scope:aawc_stage5_write_row.var:new_factor
            }
        }
    }
}

# Caller holds source identity/absolute lock throughout an unsettled packet.
# Prepare rollback only while source population AND both applied axes still
# match the post-debit state. A divergent source requires recovery, not overwrite.
aawc_stage5_prepare_refund_effect = {
    save_scope_as = aawc_stage5_packet
    remove_variable = refund_prepared
    if = {
        limit = {
            var:phase = 3
            var:source = { var:aawc_population_current = scope:aawc_stage5_packet.var:remaining_population }
        }
        set_variable = { name = refund_stale value = 0 }
        aawc_stage5_check_refund_axis_effect = { TYPE = culture }
        aawc_stage5_check_refund_axis_effect = { TYPE = faith }
        if = {
            limit = { var:refund_stale = 0 }
            set_variable = { name = refund_prepared value = 1 }
        }
    }
}

aawc_stage5_check_refund_axis_effect = {
    set_variable = { name = refund_factor_total value = 0 }
    # Check both directions: otherwise duplicate live structs could conceal a
    # missing identity while still presenting a normalized total.
    every_in_list = {
        variable = $TYPE$_rows
        save_scope_as = aawc_stage5_refund_row
        set_variable = { name = live_matches value = 0 }
        scope:aawc_stage5_packet.var:source = {
            every_in_list = {
                variable = kCAFG_province_$TYPE$_structs
                limit = { var:$TYPE$ = scope:aawc_stage5_refund_row.var:identity }
                scope:aawc_stage5_refund_row = { change_variable = { name = live_matches add = 1 } }
            }
        }
        if = {
            limit = {
                OR = {
                    var:live_matches > 1
                    AND = { var:new_factor > 0 NOT = { var:live_matches = 1 } }
                }
            }
            scope:aawc_stage5_packet = { set_variable = { name = refund_stale value = 1 } }
        }
        remove_variable = live_matches
    }
    var:source = {
        every_in_list = {
            variable = kCAFG_province_$TYPE$_structs
            save_scope_as = aawc_stage5_live_struct
            scope:aawc_stage5_packet = {
                change_variable = { name = refund_factor_total add = prev.var:factor }
                set_variable = { name = refund_matches value = 0 }
                every_in_list = {
                    variable = $TYPE$_rows
                    limit = {
                        var:identity = scope:aawc_stage5_live_struct.var:$TYPE$
                        var:new_factor = scope:aawc_stage5_live_struct.var:factor
                    }
                    scope:aawc_stage5_packet = { change_variable = { name = refund_matches add = 1 } }
                }
                if = {
                    limit = { NOT = { var:refund_matches = 1 } }
                    set_variable = { name = refund_stale value = 1 }
                }
            }
        }
    }
    if = {
        limit = { NOT = { var:refund_factor_total = 1 } }
        set_variable = { name = refund_stale value = 1 }
    }
}

# Phase 6 is set ONLY by an exact AAWC absolute refund receipt after preparation.
# Restoring snapshots also restores any units absorbed during normalization.
# Destination failure must not prevent refund: invalid is intentionally ignored.
aawc_stage5_apply_refund_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = {
            var:phase = 6 var:refund_prepared = 1
            var:source = { var:aawc_population_current = scope:aawc_stage5_packet.var:source_population }
        }
        aawc_stage5_restore_source_axis_effect = { TYPE = culture }
        aawc_stage5_restore_source_axis_effect = { TYPE = faith }
        set_variable = { name = phase value = 7 }
    }
}

aawc_stage5_restore_source_axis_effect = {
    every_in_list = {
        variable = $TYPE$_rows
        save_scope_as = aawc_stage5_write_row
        scope:aawc_stage5_packet.var:source = {
            E_kCAFG_set_struct_factor = {
                TYPE = $TYPE$
                SCOPE = scope:aawc_stage5_write_row.var:identity
                FACTOR = scope:aawc_stage5_write_row.var:original_factor
            }
        }
    }
}
'''
