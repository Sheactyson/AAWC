"""Audit a native phase-3 checkpoint and its settled/retried phase-5 save.

Reads CK3's saved values, not the script VM. Saves remain local and out of Git.
Exact marginal results are compared with the independent rational oracle.
"""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from aawc_stage5_identity_reference import SCALE, reconcile
from generate_aawc_stage4_transactions import BANDS


def matched_block(text, pattern):
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f'Native save block missing: {pattern}')
    start = match.end() - 1
    depth = 0
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]', text[start:]):
        if token[0] == '{':
            depth += 1
        elif token[0] == '}':
            depth -= 1
            if depth == 0:
                return text[start:start + token.end()]
    raise ValueError('Unclosed save block')


def variables(block):
    result = {}
    for name, kind, raw in re.findall(
        r'flag=(\w+)\s+data=\{\s+type=(\w+)(?:\s+identity=(\d+))?', block
    ):
        value = int(raw or 0)
        if kind == 'value' and value >= 2**63:
            value -= 2**64
        if name in result:
            raise ValueError(f'Duplicate native variable: {name}')
        result[name] = value
    return result


def listing(block, name):
    match = re.search(r'name="' + re.escape(name) + r'"(.*?)duration=', block, re.S)
    return [int(n) for n in re.findall(r'identity=(\d+)', match[1])] if match else []


class Save:
    def __init__(self, path):
        self.path = Path(path)
        with ZipFile(path) as archive:
            self.text = archive.read('gamestate').decode('utf-8-sig')
        self.stories = self.text[self.text.index('\nstories={'):]

    @lru_cache(maxsize=None)
    def story(self, identity):
        return matched_block(self.stories, rf'\n\t\t{identity}=\{{')

    def province(self, identity):
        return matched_block(self.text, rf'\n\t{identity}=\{{')

    def factors(self, province, axis):
        rows = [variables(self.story(n)) for n in listing(province, 'kCAFG_province_' + axis + '_structs')]
        result = {r[axis]: r['factor'] for r in rows}
        assert len(result) == len(rows), 'duplicate CaFG identity structs'
        assert sum(result.values()) == SCALE, 'CaFG factors not normalized'
        return result

    def receipt(self):
        return dict(file=self.path.name, bytes=self.path.stat().st_size,
                    sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())


def audit(midpoint_path, settled_path, source_id, terminal_cleanup=False):
    mid, end = Save(midpoint_path), Save(settled_path)
    source_mid = mid.province(source_id)
    packet_id = variables(source_mid)['aawc_stage5_packet']
    pm = mid.story(packet_id)
    vm = variables(pm)
    assert vm['phase'] == 3 * SCALE
    assert vm['absolute_debited'] == vm['amount']
    if terminal_cleanup:
        assert not re.search(rf'\n\t\t{packet_id}=\{{', end.stories), 'terminal story retained'
        children = []
        for name in ('culture_rows', 'faith_rows', 'destination_culture_rows', 'destination_faith_rows', 'route_candidates'):
            children.extend(listing(pm, name))
        for candidate in listing(pm, 'route_candidates'):
            for axis in ('culture', 'faith'):
                children.extend(listing(mid.story(candidate), axis + '_rows'))
        assert all(not re.search(rf'\n\t\t{n}=\{{', end.stories) for n in children), 'terminal child story retained'
        ve = None
    else:
        ve = variables(end.story(packet_id))
        assert ve['phase'] == 5 * SCALE and ve['finished'] == SCALE
        assert ve['absolute_debited'] == ve['absolute_credited'] == vm['amount']
    assert packet_id in listing(mid.text, 'aawc_stage5_pending_packets')
    assert packet_id not in listing(end.text, 'aawc_stage5_pending_packets')
    assert not listing(end.text, 'aawc_stage5_changed_counties')
    assert 'flag=aawc_stage5_mutating_packet\n' not in mid.text
    assert 'flag=aawc_stage5_mutating_packet\n' not in end.text
    amount = vm['amount'] // SCALE
    assert vm['amount'] == amount * SCALE
    dest_id = vm['destination']
    source_end, dest_mid, dest_end = end.province(source_id), mid.province(dest_id), end.province(dest_id)
    sm, se, dm, de = map(variables, (source_mid, source_end, dest_mid, dest_end))
    assert sm['aawc_stage5_identity_lock'] == dm['aawc_stage5_identity_lock'] == packet_id
    assert 'aawc_stage5_identity_lock' not in se and 'aawc_stage5_identity_lock' not in de
    if terminal_cleanup:
        assert 'aawc_stage5_packet' not in se
        for kind in ('county', 'internal'):
            if 'migration_' + kind in vm:
                assert se['aawc_stage5_' + kind + '_send_remaining'] == sm['aawc_stage5_' + kind + '_send_remaining'] - vm['amount']
                assert de['aawc_stage5_' + kind + '_receive_remaining'] == dm['aawc_stage5_' + kind + '_receive_remaining'] - vm['amount']
    assert sm['aawc_population_current'] == se['aawc_population_current'] == vm['source_population'] - vm['amount']
    assert dm['aawc_population_current'] == vm['destination_population']
    assert de['aawc_population_current'] == vm['destination_population'] + vm['amount']
    for band, _ in BANDS:
        key = 'aawc_reforging_cohort_' + band
        pool = 'aawc_reforging_transfer_' + band
        assert se[key] == sm[key], band
        assert de[key] == dm[key] + vm[pool], band
        if ve is not None:
            assert ve[pool] == 0, 'settled age pool must be consumed'
    assert sum(vm['aawc_reforging_transfer_' + b] for b, _ in BANDS) == vm['amount']
    for p in (sm, se, dm, de):
        assert sum(p['aawc_reforging_cohort_' + b] for b, _ in BANDS) == p['aawc_population_current']
    axes = {}
    for axis in ('culture', 'faith'):
        rows = [variables(mid.story(n)) for n in listing(pm, axis + '_rows')]
        before = {r['identity']: r['original_factor'] for r in rows}
        vector = {r['identity']: r['quantity'] // SCALE for r in rows}
        assert sum(vector.values()) == amount
        assert all(r['quantity'] % SCALE == 0 for r in rows)
        source_expected = reconcile(before, vm['source_population'] // SCALE, vector, debit=True)
        destination_expected = reconcile(mid.factors(dest_mid, axis), vm['destination_population'] // SCALE, vector)
        assert mid.factors(source_mid, axis) == end.factors(source_end, axis) == source_expected
        assert end.factors(dest_end, axis) == destination_expected
        assert vm[axis + '_carries_committed'] == SCALE
        if ve is not None:
            assert ve[axis + '_carries_committed'] == SCALE
        carries = listing(source_mid, 'aawc_stage5_' + axis + '_carries')
        assert carries == listing(source_end, 'aawc_stage5_' + axis + '_carries')
        assert all(variables(mid.story(n)) == variables(end.story(n)) for n in carries)
        axes[axis] = dict(packet_quantities=vector, source_factors_1e5=source_expected,
                          destination_factors_1e5=destination_expected, carries_unchanged_after_reload=True)
    return dict(status='PASS', midpoint=mid.receipt(), settled=end.receipt(), packet=packet_id,
                phases=[3, 'settled_and_cleaned' if terminal_cleanup else 5], amount=amount, source=source_id, destination=dest_id,
                source_population=se['aawc_population_current'] // SCALE,
                destination_population=de['aawc_population_current'] // SCALE,
                exact_thirteen_band_conservation=True, factors_match_rational_oracle=True,
                normalized_sums_1e5=100000, pending_and_refresh_queues_drained=True,
                endpoint_locks_released=True, axes=axes,
                terminal_cleanup=terminal_cleanup,
                limitation='This audit certifies saved transaction arithmetic, not the origin of ranks/candidates or full scheduler behavior. '
                           'Factors have native five-decimal quantization; identity headcounts are not a second absolute ledger.')


def audit_world(path, source_id, destination_id):
    """Audit the separately saved native probe's production-world receipt."""
    save = Save(path)
    global_values = variables(matched_block(save.text, r'(?m)^variables=\{'))
    assert global_values['aawc_s5probe_step'] == 4 * SCALE
    before = global_values['aawc_s5probe_population_before']
    assert before == global_values['aawc_s5probe_population_after']
    source, destination = save.province(source_id), save.province(destination_id)
    sv, dv = variables(source), variables(destination)
    moved = sv['aawc_s5probe_world_before'] - sv['aawc_population_current']
    assert moved > 0 and moved % SCALE == 0
    assert dv['aawc_population_current'] - dv['aawc_s5probe_world_before'] == moved
    for province, values in ((source, sv), (destination, dv)):
        assert sum(values['aawc_reforging_cohort_'+b] for b, _ in BANDS) == values['aawc_population_current']
        assert 'aawc_stage5_packet' not in values and 'aawc_stage5_identity_lock' not in values
        for axis in ('culture', 'faith'):
            save.factors(province, axis)  # Duplicate/normalization checks.
    demographic = {name:sv['aawc_reforging_cohort_last_'+name]//SCALE for name in ('births','deaths','aged')}
    assert all(value > 0 for value in demographic.values())
    assert not listing(save.text, 'aawc_stage5_pending_packets')
    assert not listing(save.text, 'aawc_stage5_changed_counties')
    return dict(status='PASS', save=save.receipt(), whole_world_before=before//SCALE,
                whole_world_after=before//SCALE, moved=moved//SCALE, demographic=demographic,
                normalized_axes=True, exact_cohort_totals=True, no_pending_or_locked_endpoints=True,
                limitation='Disposable fixture uses real production scheduling with pinned test capacity. '
                           'Ratio neutrality is checked at the demographic boundary by native probe assertions; this later save follows migration.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--midpoint', required=True, type=Path)
    parser.add_argument('--settled', required=True, type=Path)
    parser.add_argument('--source', required=True, type=int)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--allow-terminal-cleanup', action='store_true')
    parser.add_argument('--world', type=Path)
    args = parser.parse_args()
    report = audit(args.midpoint, args.settled, args.source, args.allow_terminal_cleanup)
    if args.world:
        report['world'] = audit_world(args.world, args.source, report['destination'])
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
