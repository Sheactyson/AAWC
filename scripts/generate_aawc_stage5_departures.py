"""Emit capped independent marginal departure allocation on persistent packet rows.

Input: canonical ranks, frozen owner_<axis>, optional departure_carry per row.
Output: quantities and next_carry, staged only; transaction integration owns
committing carries back to source after successful reservation.
"""


def render_departures():
    text = '''
# Packet scope. Explicit/fallback provenance must never be reweighted.
# Owner identities and carries are snapshot inputs, never live reads on retry.
aawc_stage5_weight_departures_effect = {
    if = {
        limit = {
            var:phase = 0 var:invalid = 0
            NOT = { has_variable = $TYPE$_explicit }
            NOT = { has_variable = $TYPE$_fallback }
            NOT = { has_variable = $TYPE$_weighted }
        }
        save_scope_as = aawc_stage5_packet
        aawc_stage5_validate_ranks_effect = { TYPE = $TYPE$ }
        aawc_stage5_validate_axis_effect = { TYPE = $TYPE$ }
        set_variable = { name = departure_capacity value = 0 }
        every_in_list = {
            variable = $TYPE$_rows
            set_variable = { name = capacity value = var:original_factor }
            change_variable = { name = capacity multiply = scope:aawc_stage5_packet.var:source_population }
            set_variable = { name = score value = var:capacity }
            set_variable = { name = capacity value = { value = var:capacity floor = yes } }
            if = {
                limit = { scope:aawc_stage5_packet = { has_variable = owner_$TYPE$ } }
                if = {
                    limit = { var:identity = scope:aawc_stage5_packet.var:owner_$TYPE$ }
                    change_variable = { name = score multiply = 0.5 }
                }
                else = { change_variable = { name = score multiply = 2 } }
            }
            if = {
                limit = { NOT = { has_variable = departure_carry } }
                set_variable = { name = departure_carry value = 0 }
            }
            set_variable = { name = quantity value = 0 }
            set_variable = { name = next_carry value = 0 }
            set_variable = { name = active value = 0 }
            if = {
                limit = { var:capacity > 0 }
                set_variable = { name = active value = 1 }
            }
            scope:aawc_stage5_packet = { change_variable = { name = departure_capacity add = prev.var:capacity } }
        }
        if = {
            limit = { var:departure_capacity < var:amount }
            set_variable = { name = invalid value = 1 }
        }
        set_variable = { name = departure_left value = var:amount }
        while = {
            limit = { var:departure_left > 0 var:invalid = 0 }
            set_variable = { name = score_total value = 0 }
            every_in_list = {
                variable = $TYPE$_rows
                limit = { var:active = 1 }
                scope:aawc_stage5_packet = { change_variable = { name = score_total add = prev.var:score } }
            }
            if = {
                limit = { var:score_total <= 0 }
                set_variable = { name = invalid value = 1 }
            }
            else = {
                set_variable = { name = saturated value = 0 }
                # Compute ALL quotas before reducing remaining demand.
                every_in_list = {
                    variable = $TYPE$_rows
                    limit = { var:active = 1 }
                    set_variable = { name = departure_quota value = var:score }
                    change_variable = { name = departure_quota multiply = scope:aawc_stage5_packet.var:departure_left }
                    change_variable = { name = departure_quota divide = scope:aawc_stage5_packet.var:score_total }
                    change_variable = { name = departure_quota add = var:departure_carry }
                }
                every_in_list = {
                    variable = $TYPE$_rows
                    limit = { var:active = 1 var:departure_quota >= var:capacity }
                    set_variable = { name = quantity value = var:capacity }
                    set_variable = { name = active value = 0 }
                    scope:aawc_stage5_packet = {
                        set_variable = { name = saturated value = 1 }
                        change_variable = { name = departure_left subtract = prev.var:quantity }
                    }
                }
                if = {
                    limit = { var:saturated = 0 }
                    set_variable = { name = allocated value = 0 }
                    every_in_list = {
                        variable = $TYPE$_rows
                        limit = { var:active = 1 }
                        set_variable = { name = quantity value = { value = var:departure_quota floor = yes } }
                        if = {
                            limit = { var:quantity < 0 }
                            set_variable = { name = quantity value = 0 }
                        }
                        scope:aawc_stage5_packet = { change_variable = { name = allocated add = prev.var:quantity } }
                    }
                    aawc_stage5_correct_departures_up_effect = { TYPE = $TYPE$ }
                    aawc_stage5_correct_departures_down_effect = { TYPE = $TYPE$ }
                    every_in_list = {
                        variable = $TYPE$_rows
                        limit = { var:active = 1 }
                        set_variable = { name = next_carry value = var:departure_quota }
                        change_variable = { name = next_carry subtract = var:quantity }
                    }
                    set_variable = { name = departure_left value = 0 }
                }
            }
        }
        if = {
            limit = { var:invalid = 0 }
            set_variable = { name = $TYPE$_weighted value = 1 }
            # A fully prepared vector is now explicit provenance for fallback.
            set_variable = { name = $TYPE$_explicit value = 1 }
        }
        remove_variable = selected_row
    }
}
'''
    for direction, cmp, bound, operation in (
        ('up', '<', 'var:quantity < var:capacity', 'add'),
        ('down', '>', 'var:quantity > 0', 'subtract'),
    ):
        better = '>' if direction == 'up' else '<'
        text += f'''
aawc_stage5_correct_departures_{direction}_effect = {{
    while = {{
        limit = {{ var:allocated {cmp} var:departure_left var:invalid = 0 }}
        remove_variable = selected_row
        every_in_list = {{
            variable = $TYPE$_rows
            limit = {{ var:active = 1 {bound} }}
            set_variable = {{ name = entitlement value = var:departure_quota }}
            change_variable = {{ name = entitlement subtract = var:quantity }}
            if = {{
                limit = {{ NOT = {{ scope:aawc_stage5_packet = {{ has_variable = selected_row }} }} }}
                scope:aawc_stage5_packet = {{ set_variable = {{ name = selected_row value = prev }} }}
            }}
            else_if = {{
                limit = {{
                    OR = {{
                        var:entitlement {better} scope:aawc_stage5_packet.var:selected_row.var:entitlement
                        AND = {{
                            var:entitlement = scope:aawc_stage5_packet.var:selected_row.var:entitlement
                            var:rank < scope:aawc_stage5_packet.var:selected_row.var:rank
                        }}
                    }}
                }}
                scope:aawc_stage5_packet = {{ set_variable = {{ name = selected_row value = prev }} }}
            }}
        }}
        if = {{
            limit = {{ has_variable = selected_row }}
            var:selected_row = {{ change_variable = {{ name = quantity {operation} = 1 }} }}
            change_variable = {{ name = allocated {operation} = 1 }}
        }}
        else = {{ set_variable = {{ name = invalid value = 1 }} }}
    }}
}}
'''
    return text
