"""Identity preparation and source-owned residual persistence; no population writes."""


def render_lifecycle():
    return '''
# Packet scope; assembler supplies canonical ranks and frozen candidates first.
# ORDINARY=1 creates weighted provenance. ORDINARY=0 preserves known quantities
# and independently resolves missing axes from the source majority.
aawc_stage5_prepare_identity_route_effect = {
    if = {
        limit = { var:phase = 0 var:invalid = 0 }
        save_scope_as = aawc_stage5_packet
        if = {
            limit = { $ORDINARY$ = 1 }
            aawc_stage5_weight_departures_effect = { TYPE = culture }
            aawc_stage5_weight_departures_effect = { TYPE = faith }
        }
        aawc_stage5_resolve_missing_axis_effect = { TYPE = culture }
        aawc_stage5_resolve_missing_axis_effect = { TYPE = faith }
        aawc_stage5_validate_axis_effect = { TYPE = culture }
        aawc_stage5_validate_axis_effect = { TYPE = faith }
        if = {
            limit = { var:invalid = 0 var:culture_total = var:amount var:faith_total = var:amount }
            aawc_stage5_select_route_effect = yes
            if = {
                limit = { has_variable = route_prepared }
                aawc_stage5_seal_packet_effect = yes
                aawc_stage5_prepare_source_debit_effect = yes
            }
        }
    }
}

# Packet scope, called inside the successful exact source-debit receipt guard.
# The source lock belongs to the transaction caller. Weighted axes alone advance
# residuals; explicit/fallback packets must not consume ordinary-stream carries.
aawc_stage5_commit_carries_effect = {
    if = {
        limit = { has_variable = $TYPE$_weighted NOT = { has_variable = $TYPE$_carries_committed } }
        every_in_list = {
            variable = $TYPE$_rows
            save_scope_as = aawc_stage5_carry_row
            aawc_stage5_store_carry_effect = { TYPE = $TYPE$ VALUE = scope:aawc_stage5_carry_row.var:next_carry }
        }
        set_variable = { name = $TYPE$_carries_committed value = 1 }
    }
}

# Row scope. Source-owned stories outlive the packet and the CaFG structs.
# Snapshot validation rejects duplicate identity records before reservation.
aawc_stage5_store_carry_effect = {
    remove_variable = carry_record
    scope:aawc_stage5_packet.var:source = {
        every_in_list = {
            variable = aawc_stage5_$TYPE$_carries
            limit = { var:identity = scope:aawc_stage5_carry_row.var:identity }
            scope:aawc_stage5_carry_row = { set_variable = { name = carry_record value = prev } }
        }
    }
    if = {
        limit = { NOT = { has_variable = carry_record } }
        dummy_male = { create_story = { type = aawc_stage5_packet_record save_scope_as = aawc_stage5_new_carry } }
        scope:aawc_stage5_new_carry = { set_variable = { name = identity value = scope:aawc_stage5_carry_row.var:identity } }
        scope:aawc_stage5_packet.var:source = {
            add_to_variable_list = { name = aawc_stage5_$TYPE$_carries target = scope:aawc_stage5_new_carry }
        }
        set_variable = { name = carry_record value = scope:aawc_stage5_new_carry }
    }
    var:carry_record = { set_variable = { name = value value = $VALUE$ } }
    remove_variable = carry_record
}
'''
