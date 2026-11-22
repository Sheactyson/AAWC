"""Native packet reconciliation helpers; production routing remains separate.

Ranks must be supplied by the canonical identity registry before fallback or
normalization. Missing/duplicate ranks fail closed, never use list order.
"""

def render_reconciliation():
    return '''
# Packet scope; explicit caller-supplied canonical rank, not a localized name.
aawc_stage5_set_identity_rank_effect = {
    if = {
        limit = { var:phase = 0 $RANK$ > 0 }
        every_in_list = {
            variable = $TYPE$_rows
            limit = { var:identity = $IDENTITY$ }
            set_variable = { name = rank value = $RANK$ }
        }
    }
}

# Packet scope. Require unique positive whole ranks before any tie-breaking.
aawc_stage5_validate_ranks_effect = {
    save_scope_as = aawc_stage5_packet
    every_in_list = {
        variable = $TYPE$_rows
        save_scope_as = aawc_stage5_rank_row
        if = {
            limit = { NOT = { has_variable = rank } }
            scope:aawc_stage5_packet = { set_variable = { name = invalid value = 1 } }
        }
        else = {
            set_variable = { name = whole_rank value = { value = var:rank floor = yes } }
            if = {
                limit = { OR = { var:rank <= 0 NOT = { var:rank = var:whole_rank } } }
                scope:aawc_stage5_packet = { set_variable = { name = invalid value = 1 } }
            }
            scope:aawc_stage5_packet = {
                every_in_list = {
                    variable = $TYPE$_rows
                    limit = {
                        NOT = { this = scope:aawc_stage5_rank_row }
                        has_variable = rank
                        var:rank = scope:aawc_stage5_rank_row.var:rank
                    }
                    scope:aawc_stage5_packet = { set_variable = { name = invalid value = 1 } }
                }
            }
            remove_variable = whole_rank
        }
    }
}

# Packet scope; independently fill only an entirely unspecified axis.
# This never substitutes destination identities or overwrites explicit vectors.
aawc_stage5_resolve_missing_axis_effect = {
    if = {
        limit = { var:phase = 0 NOT = { has_variable = $TYPE$_explicit } }
        aawc_stage5_validate_ranks_effect = { TYPE = $TYPE$ }
        remove_variable = selected_row
        every_in_list = {
            variable = $TYPE$_rows
            set_variable = { name = quantity value = 0 }
            if = {
                limit = { var:original_factor > 0 }
                if = {
                    limit = { NOT = { scope:aawc_stage5_packet = { has_variable = selected_row } } }
                    scope:aawc_stage5_packet = { set_variable = { name = selected_row value = prev } }
                }
                else_if = {
                    limit = {
                        OR = {
                            var:original_factor > scope:aawc_stage5_packet.var:selected_row.var:original_factor
                            AND = {
                                var:original_factor = scope:aawc_stage5_packet.var:selected_row.var:original_factor
                                var:rank < scope:aawc_stage5_packet.var:selected_row.var:rank
                            }
                        }
                    }
                    scope:aawc_stage5_packet = { set_variable = { name = selected_row value = prev } }
                }
            }
        }
        if = {
            limit = { has_variable = selected_row var:invalid = 0 }
            var:selected_row = { set_variable = { name = quantity value = scope:aawc_stage5_packet.var:amount } }
            set_variable = { name = $TYPE$_fallback value = var:selected_row.var:identity }
        }
        else = { set_variable = { name = invalid value = 1 } }
        remove_variable = selected_row
    }
}

# Packet scope; precompute both source axes before permitting absolute debit.
# All intermediate values are persisted on packet rows, never CaFG structs.
aawc_stage5_prepare_source_debit_effect = {
    if = {
        limit = { var:phase = 1 var:invalid = 0 }
        save_scope_as = aawc_stage5_packet
        set_variable = { name = remaining_population value = var:source_population }
        change_variable = { name = remaining_population subtract = var:amount }
        if = {
            limit = { var:remaining_population > 0 }
            aawc_stage5_prepare_source_axis_effect = { TYPE = culture }
            aawc_stage5_prepare_source_axis_effect = { TYPE = faith }
            if = {
                limit = { var:invalid = 0 }
                set_variable = { name = source_prepared value = 1 }
            }
        }
        else = { set_variable = { name = invalid value = 1 } }
    }
}

aawc_stage5_prepare_source_axis_effect = {
    aawc_stage5_validate_ranks_effect = { TYPE = $TYPE$ }
    every_in_list = {
        variable = $TYPE$_rows
        set_variable = { name = mass value = var:original_factor }
        change_variable = { name = mass multiply = scope:aawc_stage5_packet.var:source_population }
        change_variable = { name = mass subtract = var:quantity }
        if = {
            limit = { var:mass < 0 }
            scope:aawc_stage5_packet = { set_variable = { name = invalid value = 1 } }
        }
    }
    if = {
        limit = { var:invalid = 0 }
        aawc_stage5_normalize_rows_effect = { TYPE = $TYPE$ DENOMINATOR = scope:aawc_stage5_packet.var:remaining_population }
    }
}

# Packet scope. Fixed-point Hamilton normalization and deterministic absorption.
# Input mass rows and positive denominator; output factor units sum to 100000.
# At most one remainder award per row. No dependency random conversion path.
aawc_stage5_normalize_rows_effect = {
    save_scope_as = aawc_stage5_packet
    set_variable = { name = units_left value = 100000 }
    every_in_list = {
        variable = $TYPE$_rows
        set_variable = { name = quota value = var:mass }
        change_variable = { name = quota multiply = 100000 }
        change_variable = { name = quota divide = $DENOMINATOR$ }
        set_variable = { name = units value = { value = var:quota floor = yes } }
        set_variable = { name = remainder value = var:quota }
        change_variable = { name = remainder subtract = var:units }
        set_variable = { name = awarded value = 0 }
        scope:aawc_stage5_packet = { change_variable = { name = units_left subtract = prev.var:units } }
    }
    while = {
        limit = { var:units_left > 0 var:invalid = 0 }
        remove_variable = selected_row
        every_in_list = {
            variable = $TYPE$_rows
            limit = { var:awarded = 0 }
            if = {
                limit = { NOT = { scope:aawc_stage5_packet = { has_variable = selected_row } } }
                scope:aawc_stage5_packet = { set_variable = { name = selected_row value = prev } }
            }
            else_if = {
                limit = {
                    OR = {
                        var:remainder > scope:aawc_stage5_packet.var:selected_row.var:remainder
                        AND = {
                            var:remainder = scope:aawc_stage5_packet.var:selected_row.var:remainder
                            OR = {
                                var:quota > scope:aawc_stage5_packet.var:selected_row.var:quota
                                AND = {
                                    var:quota = scope:aawc_stage5_packet.var:selected_row.var:quota
                                    var:rank < scope:aawc_stage5_packet.var:selected_row.var:rank
                                }
                            }
                        }
                    }
                }
                scope:aawc_stage5_packet = { set_variable = { name = selected_row value = prev } }
            }
        }
        if = {
            limit = { has_variable = selected_row }
            var:selected_row = {
                change_variable = { name = units add = 1 }
                set_variable = { name = awarded value = 1 }
            }
            change_variable = { name = units_left subtract = 1 }
        }
        else = { set_variable = { name = invalid value = 1 } }
    }
    remove_variable = selected_row
    every_in_list = {
        variable = $TYPE$_rows
        if = {
            limit = { NOT = { scope:aawc_stage5_packet = { has_variable = selected_row } } }
            scope:aawc_stage5_packet = { set_variable = { name = selected_row value = prev } }
        }
        else_if = {
            limit = {
                OR = {
                    var:units > scope:aawc_stage5_packet.var:selected_row.var:units
                    AND = {
                        var:units = scope:aawc_stage5_packet.var:selected_row.var:units
                        var:rank < scope:aawc_stage5_packet.var:selected_row.var:rank
                    }
                }
            }
            scope:aawc_stage5_packet = { set_variable = { name = selected_row value = prev } }
        }
    }
    set_variable = { name = absorbed_units value = 0 }
    every_in_list = {
        variable = $TYPE$_rows
        limit = { NOT = { this = scope:aawc_stage5_packet.var:selected_row } var:units < 500 }
        scope:aawc_stage5_packet = { change_variable = { name = absorbed_units add = prev.var:units } }
        set_variable = { name = units value = 0 }
    }
    if = {
        limit = { has_variable = selected_row }
        var:selected_row = { change_variable = { name = units add = scope:aawc_stage5_packet.var:absorbed_units } }
    }
    set_variable = { name = normalized_total value = 0 }
    every_in_list = {
        variable = $TYPE$_rows
        set_variable = { name = new_factor value = var:units }
        change_variable = { name = new_factor divide = 100000 }
        scope:aawc_stage5_packet = { change_variable = { name = normalized_total add = prev.var:units } }
    }
    if = {
        limit = { NOT = { var:normalized_total = 100000 } }
        set_variable = { name = invalid value = 1 }
    }
    remove_variable = selected_row
}

# Packet scope. Called ONLY after an exact Stage 4 absolute source receipt.
# Population equality is an additional guard, not a substitute for that receipt.
aawc_stage5_apply_source_debit_effect = {
    save_scope_as = aawc_stage5_packet
    if = {
        limit = {
            var:phase = 2
            var:source_prepared = 1
            var:invalid = 0
            var:source = { var:aawc_population_current = scope:aawc_stage5_packet.var:remaining_population }
        }
        save_scope_as = aawc_stage5_packet
        aawc_stage5_write_source_axis_effect = { TYPE = culture }
        aawc_stage5_write_source_axis_effect = { TYPE = faith }
        aawc_stage5_commit_carries_effect = { TYPE = culture }
        aawc_stage5_commit_carries_effect = { TYPE = faith }
        set_variable = { name = phase value = 3 }
    }
}

aawc_stage5_write_source_axis_effect = {
    every_in_list = {
        variable = $TYPE$_rows
        save_scope_as = aawc_stage5_write_row
        scope:aawc_stage5_packet.var:source = {
            E_kCAFG_set_struct_factor = {
                TYPE = $TYPE$
                SCOPE = scope:aawc_stage5_write_row.var:identity
                FACTOR = scope:aawc_stage5_write_row.var:new_factor
            }
        }
    }
}
'''
