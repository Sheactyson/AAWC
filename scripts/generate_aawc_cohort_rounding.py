"""Generate all-flow demographic rounding adapters for the existing ledger.

Hamilton allocations use the independently tested bounded apportionment core.
This module generates source; it is not runtime certification. Existing public
effect IDs remain in their owning files and delegate to these implementations.
"""
from pathlib import Path
import argparse

from generate_aawc_cohort_apportionment import P as A, N
from validate_aawc_reforging_stage1_cohort_engine import (
    BANDS, MILITARY, MORTALITY_FRACTIONS, AGING_FRACTIONS,
    MILITARY_AGING_FRACTIONS, BAND_SUFFIXES, MOD_ROOT,
)

P = 'aawc_reforging_round_'
C = 'aawc_reforging_cohort_'
OUTPUT = MOD_ROOT / 'common/scripted_effects/aawc_reforging_cohort_rounding_effects.txt'
VALUES = MOD_ROOT / 'common/script_values/aawc_reforging_cohort_rounding_values.txt'


def av(name):
    return A + name + '_value'


def rv(name):
    return P + name + '_value'


def read(name):
    """Zero-safe expression, including parameterized variable names."""
    return '{ value = 0 if = { limit = { has_variable = ' + name + ' } add = var:' + name + ' } }'


def setv(name, value):
    return f'set_variable = {{ name = {name} value = {value} }}'


def change(name, amount):
    return setv(name, '{ value = ' + read(name) + ' add = ' + str(amount) + ' }')


def neg(expr):
    return '{ value = ' + expr + ' multiply = -1 }'


def block(name, lines):
    return name + ' = {\n' + '\n'.join('\t' + line for line in lines) + '\n}\n'


def slots(capacities, weights):
    result = [A + 'cleanup_effect = yes']
    for i in range(N):
        result += [setv(A + f'capacity_{i:02}', capacities[i] if i < len(capacities) else '0'),
                   setv(A + f'weight_{i:02}', weights[i] if i < len(weights) else '0')]
    return result


def pending_flow():
    # Slot weights are current expected demand plus legacy per-band carry.
    # PENDING is a distinct explicit unserved whole-demand store, not a person.
    lines = [setv(P + 'due', read('$PENDING$'))]
    for i in range(N):
        lines.append(change(P + 'due', av(f'weight_{i:02}')))
    lines += [setv(A + 'requested', '{ value = ' + rv('due') + ' floor = yes }'),
              A + 'allocate_effect = yes',
              setv(P + 'remainder', rv('due'))]
    for i in range(N):
        lines.append(change(P + 'remainder', neg(av(f'allocation_{i:02}'))))
    # If the core rejected input, caller must leave both residents and carries
    # untouched. No silent partial application or lost pending request.
    return block(P + 'allocate_flow_effect', lines)


def settle_carries(carries, pending):
    """Retain all demand, splitting whole backlog from fractional carry.

    Fractional demand is redistributed in proportion to this transaction's
    weights. The final positive slot receives exact fixedpoint residue. No
    negative error carries and no disappearing demand on pool exhaustion.
    """
    lines = [setv(pending, '{ value = ' + rv('remainder') + ' floor = yes }'),
             setv(P + 'fraction_left', '{ value = ' + rv('remainder') + ' subtract = ' + read(pending) + ' }'),
             setv(P + 'fraction_total', rv('fraction_left')),
             setv(P + 'sum_weights', '0'), setv(P + 'last_weight', '-1')]
    for i in range(len(carries)):
        lines += [change(P + 'sum_weights', av(f'weight_{i:02}')),
                  f'if = {{ limit = {{ {av(f"weight_{i:02}")} > 0 }} {setv(P + "last_weight", str(i))} }}']
    for i, carry in enumerate(carries):
        lines += [setv(carry, '0'),
                  f'if = {{ limit = {{ {av(f"weight_{i:02}")} > 0 {rv("sum_weights")} > 0 }}',
                  f'\tif = {{ limit = {{ {rv("last_weight")} = {i} }} {setv(carry, rv("fraction_left"))} }}',
                  '\telse = { ' + setv(carry, '{ value = ' + rv('fraction_total') + ' multiply = 100000 multiply = ' + av(f'weight_{i:02}') + ' divide = ' + rv('sum_weights') + ' floor = yes divide = 100000 max = ' + rv('fraction_left') + ' }') + ' }',
                  '\t' + change(P + 'fraction_left', neg(read(carry))), '}']
    # Zero-weight pending is retained, even if no band can currently serve it.
    lines += [change(pending, rv('fraction_left'))]
    return lines


def natural(kind):
    mortality = kind == 'mortality'
    carries = MORTALITY_FRACTIONS if mortality else AGING_FRACTIONS
    count = len(carries)
    pending = P + kind + '_pending'
    caps = [read(b) for b in BANDS[:count]]
    rates = ([C + 'candidate_monthly_mortality_age_' + b for b in BAND_SUFFIXES]
             if mortality else ['{ value = ' + read(b) + ' divide = 60 }' for b in BANDS[:count]])
    weights = ['{ value = ' + rate + ' add = ' + read(carry) + ' }' for rate, carry in zip(rates, carries)]
    lines = slots(caps, weights)
    lines += [P + 'allocate_flow_effect = { PENDING = ' + pending + ' }',
              'if = {', '\tlimit = { ' + av('valid') + ' = 1 }']
    apply = []
    # Save all allocations before the overlay selection reuses the allocator.
    for i in range(count):
        apply += [setv(P + f'parent_before_{i:02}', read(BANDS[i])),
                  setv(P + f'parent_movers_{i:02}', av(f'allocation_{i:02}'))]
    apply += settle_carries(carries, pending)
    for i in reversed(range(count)):
        moved = rv(f'parent_movers_{i:02}')
        apply += [change(BANDS[i], neg(moved))]
        if not mortality:
            apply += [change(BANDS[i + 1], moved)]
        apply += [change(C + ('last_deaths' if mortality else 'last_aged'), moved)]
    # Coupled military selection uses the exact parent movers, never an
    # independent membership clock. Mortality loss and age-60 retirement differ.
    apply += [P + ('military_mortality_effect' if mortality else 'military_aging_effect') + ' = yes']
    lines += ['\t' + line for line in apply] + ['}', A + 'cleanup_effect = yes', P + 'cleanup_effect = yes']
    lines = ['if = { limit = { ' + rv('counts_valid') + ' = 1 }', *['\t' + x for x in lines], '}',
             'else = { ' + change(P + 'invalid_rejections_total', '1') + ' }']
    return block(P + kind + '_effect', lines)


def military(kind):
    mortality = kind == 'mortality'
    if not mortality:
        return military_aging()
    # Preserve established mortality reconciliation: only the subset in excess
    # of its surviving parent is removed. These operands are already integer
    # counts; proportional military mortality would change the class mechanic.
    lines = []
    for j, m in enumerate(MILITARY):
        excess = '{ value = ' + read(m) + ' subtract = ' + read(BANDS[j + 3]) + ' min = 0 }'
        lines += [setv(P + 'military_excess', excess),
                  change(P + 'military_deaths_total', rv('military_excess')),
                  change(m, neg(rv('military_excess')))]
    return block(P + 'military_mortality_effect', lines)


def military_aging():
    # Forced movers are the integer lower bound needed by the surviving
    # parent. Allocate remaining expected military demand across all nine
    # adult bands, capped by both their military residents and parent movers.
    # This retains the existing nine selection carries rather than resetting
    # valid save state or selecting from a newly arrived destination member.
    lines = [A + 'cleanup_effect = yes']
    for j, m in enumerate(MILITARY):
        i = j + 3
        before, movers = rv(f'parent_before_{i:02}'), rv(f'parent_movers_{i:02}')
        lower = rv(f'military_forced_{j:02}')
        lines += [setv(P + f'military_forced_{j:02}',
                       '{ value = ' + read(m) + ' subtract = ' + before + ' add = ' + movers + ' min = 0 }'),
                  setv(A + f'capacity_{j:02}',
                       '{ value = ' + read(m) + ' max = ' + movers + ' subtract = ' + lower + ' min = 0 }'),
                  setv(A + f'weight_{j:02}', read(MILITARY_AGING_FRACTIONS[j])),
                  f'if = {{ limit = {{ {before} > 0 }} ' + change(A + f'weight_{j:02}',
                       '{ value = ' + movers + ' multiply = ' + read(m) + ' divide = ' + before + ' }') + ' }',
                  change(A + f'weight_{j:02}', neg(lower))]
    lines += [P + 'allocate_flow_effect = { PENDING = ' + P + 'military_aging_pending }',
              'if = {', '\tlimit = { ' + av('valid') + ' = 1 }']
    sub = settle_carries(MILITARY_AGING_FRACTIONS, P + 'military_aging_pending')
    for j in reversed(range(9)):
        moved = '{ value = ' + av(f'allocation_{j:02}') + ' add = ' + rv(f'military_forced_{j:02}') + ' }'
        sub += [change(MILITARY[j], neg(moved))]
        if j == 8:
            sub += [change(C + 'last_military_retired', moved)]
        else:
            sub += [change(MILITARY[j + 1], moved), change(C + 'last_military_aged', moved)]
    lines += ['\t' + line for line in sub] + ['}']
    return block(P + 'military_aging_effect', lines)


def single_flow():
    # A specified destination is Hamilton's one-bin case. Preserve only the
    # subperson carry; whole demand rejected by the existing capacity bound is
    # reported explicitly, not resurrected as debt against future residents.
    body = [
        setv(P + 'single_due', '{ value = $AMOUNT$ min = 0 add = ' + read('$CARRY$') + ' }'),
        setv(P + 'single_whole', '{ value = ' + rv('single_due') + ' floor = yes }'),
        setv(P + 'last_applied', '{ value = ' + rv('single_whole') + ' max = $CAPACITY$ min = 0 floor = yes }'),
        setv(P + 'last_unserved', '{ value = ' + rv('single_whole') + ' subtract = ' + rv('last_applied') + ' }'),
        setv('$CARRY$', '{ value = ' + rv('single_due') + ' subtract = ' + rv('single_whole') + ' }'),
        change(P + 'rejected_whole_total', rv('last_unserved')),
        'remove_variable = ' + P + 'single_due', 'remove_variable = ' + P + 'single_whole',
    ]
    return block(P + 'single_flow_effect', [setv(P + 'last_applied', '0'), setv(P + 'last_unserved', '0'),
                 *whole_input_guard([], body, nonnegative=[read('$CARRY$')])])


def band_transaction(kind):
    military = kind in ('classify', 'release')
    subject = '$MILITARY$' if military else '$BAND$'
    carry = subject + '_' + kind + '_pending'
    if kind == 'credit':
        capacity = '{ value = $AMOUNT$ min = 0 add = ' + read(carry) + ' floor = yes }'
    elif kind == 'classify':
        capacity = '{ value = ' + read('$BAND$') + ' subtract = ' + read('$MILITARY$') + ' min = 0 }'
    else:
        capacity = read(subject)
    # CK3 macro arguments must be scalar tokens. Snapshot the identical inline
    # expression in effect context instead of passing its block as an argument.
    lines = [setv(P + 'single_capacity', capacity),
             P + 'single_flow_effect = { AMOUNT = $AMOUNT$ CARRY = ' + carry + ' CAPACITY = ' + rv('single_capacity') + ' }',
             'remove_variable = ' + P + 'single_capacity',
             change(subject, rv('last_applied') if kind in ('credit', 'classify') else neg(rv('last_applied')))]
    if kind == 'death':
        lines += [setv(C + 'last_external_deaths', rv('last_applied')),
                  change(C + 'external_deaths_total', rv('last_applied'))]
    lines += [C + 'reconcile_effect = yes', C + 'refresh_mirrors_effect = yes']
    return block(P + kind + '_band_effect', [setv(P + 'last_applied', '0'),
                 'if = { limit = { ' + rv('counts_valid') + ' = 1 }', *['\t' + x for x in lines], '}',
                 'else = { ' + change(P + 'invalid_rejections_total', '1') + ' }'])


def initial_allocation():
    # Initial population is an absolute import, not a repeated credit. Its
    # fractional remainder is retained separately and never rounded into a
    # fractional resident or repeatedly added by a refresh.
    initial = [9, 8, 8, 8, 8, 8, 8, 8, 7, 7, 6, 5, 10]
    whole = '{ value = ' + read(C + 'work_population') + ' floor = yes }'
    lines = slots([whole] * 13, list(map(str, initial)))
    lines += [setv(A + 'requested', whole), A + 'allocate_effect = yes',
              'if = {', '\tlimit = { ' + av('valid') + ' = 1 }']
    for i, band in enumerate(BANDS):
        lines += ['\t' + setv(band, av(f'allocation_{i:02}'))]
    lines += ['\t' + setv(P + 'resident_import_fraction',
               '{ value = ' + read(C + 'work_population') + ' subtract = ' + av('requested') + ' }'),
              '}', A + 'cleanup_effect = yes']
    return block(P + 'initialize_bands_effect', lines)


def whole_input_guard(slots_to_check, body, extra=(), nonnegative=()):
    """Reject corrupt historical headcounts without repairing or consuming them.

    A rejected invocation accrues no new demand. Existing carries, counts and
    backlog remain raw evidence; the additive counter records the rejection.
    """
    lines = [setv(P + 'input_valid', '1')]
    for slot in slots_to_check:
        lines += [setv(P + 'checked_value', read(slot)),
                  setv(P + 'checked_whole', '{ value = ' + rv('checked_value') + ' floor = yes }'),
                  'if = { limit = { OR = { ' + rv('checked_value') + ' < 0 ' + rv('checked_value') + ' != ' + rv('checked_whole') + ' } } ' + setv(P + 'input_valid', '0') + ' }']
    for expr in nonnegative:
        lines += [setv(P + 'checked_value', expr),
                  'if = { limit = { ' + rv('checked_value') + ' < 0 } ' + setv(P + 'input_valid', '0') + ' }']
    lines += ['if = { limit = { ' + rv('input_valid') + ' = 1 ' + ' '.join(extra) + ' }']
    lines += ['\t' + line for line in body] + ['}',
              'else = { ' + change(P + 'invalid_rejections_total', '1') + ' }',
              'remove_variable = ' + P + 'checked_value',
              'remove_variable = ' + P + 'checked_whole',
              'remove_variable = ' + P + 'input_valid']
    return lines


def compatibility_flow(kind):
    """Retain public single-band helper semantics with normalized backlog."""
    mortality = kind == 'mortality'
    source = '$BAND$' if mortality else '$SOURCE$'
    amount = '$RATE$' if mortality else '{ value = ' + read(source) + ' divide = 60 }'
    fraction, backlog = '$FRACTION$', '$FRACTION$_backlog'
    body = [setv(P + 'compat_due', '{ value = ' + amount + ' add = ' + read(fraction) + ' add = ' + read(backlog) + ' }'),
            setv(P + 'compat_applied', '{ value = ' + rv('compat_due') + ' floor = yes max = ' + read(source) + ' min = 0 }'),
            setv(P + 'compat_left', '{ value = ' + rv('compat_due') + ' subtract = ' + rv('compat_applied') + ' }'),
            setv(backlog, '{ value = ' + rv('compat_left') + ' floor = yes }'),
            setv(fraction, '{ value = ' + rv('compat_left') + ' subtract = ' + read(backlog) + ' }'),
            change(source, neg(rv('compat_applied'))),
            change(C + ('last_deaths' if mortality else 'last_aged'), rv('compat_applied'))]
    if not mortality:
        body += [change('$DESTINATION$', rv('compat_applied')), setv(C + 'work_aged', rv('compat_applied'))]
    checks = [source] + ([] if mortality else ['$DESTINATION$'])
    lines = ([] if mortality else [setv(C + 'work_aged', '0')])
    lines += whole_input_guard(checks, body, nonnegative=[read(fraction), read(backlog), amount])
    lines += ['remove_variable = ' + P + k for k in ('compat_due', 'compat_applied', 'compat_left')]
    return block(P + 'compat_' + kind + '_effect', lines)


def compatibility_military():
    # One-bin subordinate selection. Forced movers are a lower bound, while
    # both the parent move and membership are upper bounds. Demand consumed by
    # that lower bound is saturated at zero rather than made negative.
    body = [setv(P + 'compat_before', '{ value = ' + read('$PARENT_SOURCE$') + ' add = ' + read(C + 'work_aged') + ' }'),
            setv(P + 'compat_due', '{ value = ' + read('$FRACTION$') + ' add = ' + read('$FRACTION$_backlog') + ' }'),
            'if = { limit = { ' + rv('compat_before') + ' > 0 } ' + change(P + 'compat_due', '{ value = ' + read(C + 'work_aged') + ' multiply = ' + read('$SOURCE$') + ' divide = ' + rv('compat_before') + ' }') + ' }',
            setv(P + 'compat_applied', '{ value = ' + rv('compat_due') + ' floor = yes min = { value = ' + read('$SOURCE$') + ' subtract = ' + read('$PARENT_SOURCE$') + ' min = 0 } max = ' + read('$SOURCE$') + ' max = ' + read(C + 'work_aged') + ' }'),
            setv(P + 'compat_left', '{ value = ' + rv('compat_due') + ' subtract = ' + rv('compat_applied') + ' min = 0 }'),
            setv('$FRACTION$_backlog', '{ value = ' + rv('compat_left') + ' floor = yes }'),
            setv('$FRACTION$', '{ value = ' + rv('compat_left') + ' subtract = ' + read('$FRACTION$_backlog') + ' }'),
            change('$SOURCE$', neg(rv('compat_applied'))),
            '$DESTINATION_ACTION$ = { AMOUNT = ' + rv('compat_applied') + ' DESTINATION = $DESTINATION$ }']
    lines = whole_input_guard(['$SOURCE$', '$DESTINATION$', '$PARENT_SOURCE$', C + 'work_aged'], body,
                              nonnegative=[read('$FRACTION$'), read('$FRACTION$_backlog')])
    lines += ['remove_variable = ' + P + k for k in ('compat_before', 'compat_due', 'compat_applied', 'compat_left')]
    lines += ['remove_variable = ' + C + 'work_aged']
    result = block(P + 'compat_military_effect', lines)
    result += block(P + 'compat_military_move_effect', [change('$DESTINATION$', '$AMOUNT$'), change(C + 'last_military_aged', '$AMOUNT$')])
    # The shared dispatcher supplies DESTINATION for both move and retire.
    # Bind it through the same nonnegative destination precondition already
    # enforced by compat_military_effect; retirement never credits residents.
    result += block(P + 'compat_military_retire_effect', [
        'if = { limit = { OR = { NOT = { has_variable = $DESTINATION$ } var:$DESTINATION$ >= 0 } } '
        + change(C + 'last_military_retired', '$AMOUNT$') + ' }'])
    return result


SCRATCH = ['due', 'remainder', 'fraction_left', 'fraction_total', 'sum_weights', 'last_weight', 'military_excess']
SCRATCH += [f'{field}_{i:02}' for field in ('parent_before', 'parent_movers') for i in range(13)]
SCRATCH += [f'military_forced_{j:02}' for j in range(9)]
DURABLE = ['mortality_pending', 'aging_pending', 'military_aging_pending', 'military_deaths_total',
           'resident_import_fraction', 'last_applied', 'last_unserved', 'rejected_whole_total']

# Pending transaction amounts are separate per operation and recipient band.
# They are zero-default additive state, not replacements for existing save IDs.
PENDING = [P + k for k in ('mortality_pending', 'aging_pending', 'military_aging_pending',
                           'resident_import_fraction', 'population_debit_pending', 'population_death_pending', 'target_fraction')]
PENDING += [band + '_' + kind + '_pending' for band in BANDS for kind in ('credit', 'debit', 'death')]
PENDING += [m + '_' + kind + '_pending' for m in MILITARY for kind in ('classify', 'release')]
PENDING += [f + '_backlog' for f in MORTALITY_FRACTIONS + AGING_FRACTIONS + MILITARY_AGING_FRACTIONS]
FRACTION_PENDING = [k for k in PENDING if not k.endswith('_backlog') and k not in [P + n + '_pending' for n in ('mortality', 'aging', 'military_aging')]]
BACKLOG_PENDING = [k for k in PENDING if k not in FRACTION_PENDING]
PERSISTENT = PENDING + [P + name for name in ('last_applied', 'last_unserved', 'military_deaths_total',
                                             'rejected_whole_total', 'invalid_rejections_total')]


def generate():
    header = ('# Generated by scripts/generate_aawc_cohort_rounding.py.\n'
              '# All-demographic-flows Hamilton policy: bounded whole-person allocations.\n'
              '# Current implementation is staged; do not deploy before integration acceptance.\n\n')
    effects = header + pending_flow() + '\n' + natural('mortality') + '\n' + natural('aging')
    effects += '\n' + military('mortality') + '\n' + military('aging')
    effects += '\n' + single_flow() + '\n' + initial_allocation()
    effects += '\n' + compatibility_flow('mortality') + '\n' + compatibility_flow('aging') + '\n' + compatibility_military()
    effects += '\n'.join(band_transaction(kind) for kind in ('credit', 'debit', 'death', 'classify', 'release'))
    effects += '\n' + block(P + 'cleanup_effect', ['remove_variable = ' + P + n for n in SCRATCH])
    effects += '\n' + block(P + 'snapshot_effect', [setv(P + f'checkpoint_{i:03}', read(k)) for i, k in enumerate(PERSISTENT)] + [setv(P + 'checkpoint_version', '1')])
    values = header + '\n'.join(block(rv(name), ['value = ' + read(P + name)]) for name in SCRATCH + DURABLE + ['single_due', 'single_whole', 'single_capacity', 'input_valid', 'checked_value', 'checked_whole', 'compat_due', 'compat_applied', 'compat_left', 'compat_before'])
    valid = ['value = 1']
    for slot in BANDS + MILITARY:
        valid += ['if = { limit = { has_variable = ' + slot + ' var:' + slot + ' < 0 } value = 0 }']
    valid += ['if = { limit = { aawc_reforging_diag_fractional_status > 0 } value = 0 }']
    values += '\n' + block(rv('counts_valid'), valid)
    pending_valid = ['value = 1']
    for slot in PENDING:
        check = 'var:' + slot + ' < 0'
        if slot in FRACTION_PENDING:
            check = 'OR = { ' + check + ' var:' + slot + ' >= 1 }'
        pending_valid += ['if = { limit = { has_variable = ' + slot + ' ' + check + ' } value = 0 }']
    backlog_fraction = ['value = 0']
    for slot in PENDING:
        if slot.endswith('_backlog'):
            backlog_fraction += ['add = { value = ' + read(slot) + ' subtract = { value = ' + read(slot) + ' floor = yes } }']
    values += '\n' + block(rv('backlog_fraction'), backlog_fraction)
    pending_valid += ['if = { limit = { ' + rv('backlog_fraction') + ' > 0 } value = 0 }']
    values += '\n' + block(rv('pending_valid'), pending_valid)
    persistence = ['value = 1', 'if = { limit = { NOT = { has_variable = ' + P + 'checkpoint_version } } value = 0 }']
    for i, key in enumerate(PERSISTENT):
        values += '\n' + block(rv(f'state_{i:03}'), ['value = ' + read(key)])
        values += '\n' + block(rv(f'checkpoint_{i:03}'), ['value = ' + read(P + f'checkpoint_{i:03}')])
        persistence += ['if = { limit = { ' + rv(f'state_{i:03}') + ' != ' + rv(f'checkpoint_{i:03}') + ' } value = 0 }']
    values += '\n' + block(rv('persistence_status'), persistence)
    return {OUTPUT: effects, VALUES: values}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, content in generate().items():
        if args.check:
            assert path.read_bytes() == content.encode('utf-8-sig'), path
        else:
            path.write_bytes(content.encode('utf-8-sig'))
        print(('Verified: ' if args.check else 'Generated: ') + str(path.relative_to(MOD_ROOT)))
