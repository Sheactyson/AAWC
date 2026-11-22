"""Persistent candidate eligibility and deterministic Stage 5 route selection.

The assembler supplies adjacent/war/rating/capacity/province-id snapshots and
positive destination marginal rows. This layer never reserves population.
"""


def render_routing():
    text = '''
# Packet scope. Inputs are frozen candidate stories, never mutable live scores.
# A route receipt survives retries. Empty search changes no population or carries.
aawc_stage5_select_route_effect = {
    if = {
        limit = { var:phase = 0 var:invalid = 0 NOT = { has_variable = route_prepared } }
        save_scope_as = aawc_stage5_packet
        remove_variable = selected_candidate
        every_in_list = {
            variable = route_candidates
            save_scope_as = aawc_stage5_candidate
            set_variable = { name = eligible value = 0 }
            set_variable = { name = identity_match value = 0 }
            aawc_stage5_match_candidate_axis_effect = { TYPE = culture }
            aawc_stage5_match_candidate_axis_effect = { TYPE = faith }
            if = {
                limit = { var:adjacent = 1 var:receive_capacity >= scope:aawc_stage5_packet.var:amount }
                if = {
                    limit = { scope:aawc_stage5_packet.var:source_war = 0 var:war = 0 var:identity_match = 1 }
                    set_variable = { name = eligible value = 1 }
                    set_variable = { name = tier value = 1 }
                }
                else_if = {
                    limit = { scope:aawc_stage5_packet.var:source_war = 1 }
                    set_variable = { name = eligible value = 1 }
                    set_variable = { name = tier value = 4 }
                    if = {
                        limit = { var:war = 0 }
                        set_variable = { name = tier value = 2 }
                    }
                    if = {
                        limit = { var:identity_match = 1 }
                        change_variable = { name = tier subtract = 1 }
                    }
                }
            }
            if = {
                limit = { var:eligible = 1 }
                if = {
                    limit = { NOT = { scope:aawc_stage5_packet = { has_variable = selected_candidate } } }
                    scope:aawc_stage5_packet = { set_variable = { name = selected_candidate value = prev } }
                }
                else = { aawc_stage5_compare_candidate_effect = yes }
            }
        }
        if = {
            limit = { has_variable = selected_candidate }
            set_variable = { name = destination value = var:selected_candidate.var:destination }
            set_variable = { name = route_prepared value = 1 }
        }
    }
}

# Candidate scope: OR across independent axes, positive packet quantities only.
aawc_stage5_match_candidate_axis_effect = {
    every_in_list = {
        variable = $TYPE$_rows
        limit = { var:original_factor >= 0.005 }
        save_scope_as = aawc_stage5_destination_identity
        scope:aawc_stage5_packet = {
            every_in_list = {
                variable = $TYPE$_rows
                limit = { var:quantity > 0 var:identity = scope:aawc_stage5_destination_identity.var:identity }
                scope:aawc_stage5_candidate = { set_variable = { name = identity_match value = 1 } }
            }
        }
    }
}
'''
    # Lexicographic ordering, explicit equals for all preceding keys.
    keys = [('tier', '<'), ('rating_delta', '>'), ('receive_capacity', '>'), ('province_id', '<')]
    clauses = []
    for index, (key, op) in enumerate(keys):
        prefix = ' '.join(f'var:{k} = scope:aawc_stage5_packet.var:selected_candidate.var:{k}' for k, _ in keys[:index])
        clauses.append(f'AND = {{ {prefix} var:{key} {op} scope:aawc_stage5_packet.var:selected_candidate.var:{key} }}')
    text += '''
aawc_stage5_compare_candidate_effect = {
    if = {
        limit = { OR = { ''' + '\n'.join(clauses) + ''' } }
        scope:aawc_stage5_packet = { set_variable = { name = selected_candidate value = prev } }
    }
}
'''
    return text
