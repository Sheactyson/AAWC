"""Compile the Stage 3 authoring contract into inert, deterministic review artifacts.

The JSON source is authoritative after import. No CK3 script is emitted, no live
Stage 2 CSV is updated, and no population, military or native-output code runs.
Missing product decisions are explicit nulls/statuses, never inferred defaults.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'catalogue/stage3/catalogue.json'
OUTPUT = ROOT / 'catalogue/stage3/generated'
DIMENSIONS = ('sustenance', 'habitation', 'opportunity', 'health', 'security', 'amenities')
POLICY = {'runtime_activation': False, 'population_owner': 'stage1',
          'demographic_formula_owner': 'stage2', 'military_lifecycle': 'deferred_stage6',
          'native_output_scaling': 'deferred_stage7'}


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def keys(value, expected, context):
    require(isinstance(value, dict) and set(value) == set(expected.split()),
            f'{context}: expected exactly {expected}')


def text(value, context, nullable=False):
    require((nullable and value is None) or (isinstance(value, str) and bool(value.strip())),
            f'{context}: nonempty text required')


def number(value, context, minimum=None, nullable=False):
    if nullable and value is None:
        return
    require(type(value) in (int, float) and math.isfinite(value), f'{context}: finite number required')
    require(minimum is None or value >= minimum, f'{context}: below {minimum}')


def identifier(value, context):
    require(isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9_]*', value),
            f'{context}: invalid identifier')


def validate(data):
    """Strict source schema plus cross-record invariants; usable without game files."""
    keys(data, 'schema_version catalogue_id imports policy chains', 'catalogue')
    require(type(data['schema_version']) is int and data['schema_version'] == 1, 'unsupported schema version')
    require(data['catalogue_id'] == 'aawc_stage3_d7_d8_v2', 'wrong catalogue')
    require(json_bytes(data['policy']) == json_bytes(POLICY), 'Stage ownership/activation policy changed')
    require(isinstance(data['imports'], list) and data['imports'], 'missing import provenance')
    for item in data['imports']:
        keys(item, 'path sha256', 'import')
        text(item['path'], 'import path')
        require(not Path(item['path']).is_absolute() and '..' not in Path(item['path']).parts,
                'import path must be repository-relative')
        require(re.fullmatch(r'[0-9a-f]{64}', item['sha256']) is not None, 'invalid import hash')
    chains = data['chains']
    require(isinstance(chains, list) and len(chains) == 131, 'expected 131 chains')
    chain_ids, building_ids, legacy_ids = set(), set(), set()
    kind_levels = {'regular': 0, 'duchy': 0}
    counts = {'regular': 0, 'duchy': 0, 'legacy': 0, 'new': 0, 'levels': 0}
    for chain in chains:
        keys(chain, 'id kind family lineage gates player ai semantic_review levels', 'chain')
        cid = chain['id']
        identifier(cid, 'chain ID')
        require(cid not in chain_ids, f'duplicate chain {cid}')
        chain_ids.add(cid)
        require(chain['kind'] in ('regular', 'duchy'), f'{cid}: invalid kind')
        counts[chain['kind']] += 1
        text(chain['family'], f'{cid} family')
        keys(chain['lineage'], 'status legacy_chain', f'{cid} lineage')
        lineage = chain['lineage']
        require(lineage['status'] in ('legacy', 'new'), f'{cid}: invalid lineage')
        counts[lineage['status']] += 1
        if lineage['status'] == 'legacy':
            text(lineage['legacy_chain'], f'{cid} legacy chain')
        else:
            require(lineage['legacy_chain'] is None, f'{cid}: new chain has legacy lineage')
        gates = chain['gates']
        keys(gates, 'status proposal source_predicates source_reference', f'{cid} gates')
        require(gates['status'] in ('proposed', 'missing', 'approved'), f'{cid}: invalid gates status')
        text(gates['proposal'], f'{cid} proposed gates')
        text(gates['source_predicates'], f'{cid} source predicates', nullable=True)
        text(gates['source_reference'], f'{cid} source reference', nullable=True)
        if gates['status'] == 'approved':
            text(gates['source_predicates'], f'{cid} approved predicates')
            text(gates['source_reference'], f'{cid} approved reference')
        player = chain['player']
        keys(player, 'status name description icon model effect_description', f'{cid} player')
        require(player['status'] in ('proposed', 'missing', 'approved'), f'{cid}: player status')
        text(player['name'], f'{cid} player name')
        for field in ('description', 'icon', 'model', 'effect_description'):
            text(player[field], f'{cid} player {field}', nullable=player['status'] != 'approved')
        ai = chain['ai']
        keys(ai, 'status value', f'{cid} AI')
        require(ai['status'] in ('missing', 'proposed', 'approved'), f'{cid}: AI status')
        number(ai['value'], f'{cid} AI value', minimum=0, nullable=ai['status'] != 'approved')
        review = chain['semantic_review']
        keys(review, 'status reason', f'{cid} semantic review')
        require(review['status'] in ('pending', 'approved'), f'{cid}: review status')
        text(review['reason'], f'{cid} review reason')
        levels = chain['levels']
        require(isinstance(levels, list) and bool(levels), f'{cid}: empty chain')
        require(sorted(x['tier'] for x in levels) == list(range(1, len(levels) + 1)),
                f'{cid}: tiers must be contiguous from 1')
        ordered = sorted(levels, key=lambda x: x['tier'])
        for index, level in enumerate(ordered):
            keys(level, 'id legacy_id tier upgrades_to costs construction_days conditions capacity tradeoffs gates native_role constructibility player', f'{cid} level')
            bid = level['id']
            identifier(bid, 'building ID')
            require(bid not in building_ids, f'duplicate building {bid}')
            building_ids.add(bid)
            if lineage['status'] == 'legacy':
                # A heritage chain may introduce a tier with no old counterpart.
                if level['legacy_id'] is not None:
                    identifier(level['legacy_id'], f'{bid} legacy ID')
                    require(level['legacy_id'] not in legacy_ids, f'{bid}: duplicate legacy ID')
                    legacy_ids.add(level['legacy_id'])
            else:
                require(level['legacy_id'] is None, f'{bid}: new level has legacy ID')
            require(type(level['tier']) is int, f'{bid}: integer tier required')
            expected_next = ordered[index + 1]['id'] if index + 1 < len(ordered) else None
            require(level['upgrades_to'] == expected_next, f'{bid}: upgrade must be next tier or null terminal')
            keys(level['costs'], 'gold prestige piety', f'{bid} costs')
            for field, value in level['costs'].items():
                number(value, f'{bid} {field}', minimum=0)
            require(level['costs']['gold'] > 0, f'{bid}: gold must be positive')
            number(level['construction_days'], f'{bid} days', minimum=1)
            keys(level['conditions'], ' '.join(DIMENSIONS), f'{bid} conditions')
            for field, value in level['conditions'].items():
                number(value, f'{bid} {field}')
            keys(level['capacity'], 'status space_percent', f'{bid} capacity')
            require(level['capacity']['status'] in ('missing', 'proposed', 'approved'), f'{bid}: capacity status')
            number(level['capacity']['space_percent'], f'{bid} space percent', nullable=level['capacity']['status'] == 'missing')
            keys(level['tradeoffs'], 'negative_conditions notes', f'{bid} tradeoffs')
            require(level['tradeoffs']['negative_conditions'] == {k: v for k, v in level['conditions'].items() if v < 0}, f'{bid}: tradeoffs disagree with conditions')
            text(level['tradeoffs']['notes'], f'{bid} tradeoff notes', nullable=True)
            keys(level['gates'], 'era_innovation_proposal geography_proposal', f'{bid} level gates')
            for field, value in level['gates'].items():
                text(value, f'{bid} {field}')
            keys(level['native_role'], 'status proposal', f'{bid} native role')
            require(level['native_role']['status'] == 'deferred', f'{bid}: native behavior must remain deferred')
            keys(level['native_role']['proposal'],
                 'economic_potential_pct_cumulative workforce_requirement_candidate native_effect_contract chain_role distinct_identity construction_rationale review_status',
                 f'{bid} native proposal')
            for field, value in level['native_role']['proposal'].items():
                text(value, f'{bid} native metadata {field}')
            keys(level['constructibility'], 'status reasons', f'{bid} constructibility')
            require(level['constructibility']['status'] == 'blocked_review', f'{bid}: runtime authoring is not activated by this contract')
            require(isinstance(level['constructibility']['reasons'], list) and level['constructibility']['reasons'], f'{bid}: missing block reasons')
            for reason in level['constructibility']['reasons']:
                text(reason, f'{bid} block reason')
            keys(level['player'], 'name name_key description_key effect_description_key', f'{bid} player')
            for field, value in level['player'].items():
                text(value, f'{bid} {field}', nullable=field == 'name')
            require(level['player']['name_key'] == f'building_{bid}' and
                    level['player']['description_key'] == f'building_{bid}_desc' and
                    level['player']['effect_description_key'] == f'aawc_stage3_{bid}_effects',
                    f'{bid}: localization key contract mismatch')
            counts['levels'] += 1
            kind_levels[chain['kind']] += 1
    require(counts == {'regular': 99, 'duchy': 32, 'legacy': 105, 'new': 26, 'levels': 771}, f'catalogue census mismatch: {counts}')
    require(kind_levels == {'regular': 677, 'duchy': 94}, f'level-kind census mismatch: {kind_levels}')
    require(len(legacy_ids) == 624, f'expected 624 legacy level IDs, got {len(legacy_ids)}')
    return counts


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def load_source(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)


def compile_catalogue(data):
    counts = validate(data)
    expanded = []
    for chain in sorted(data['chains'], key=lambda x: x['id']):
        for level in sorted(chain['levels'], key=lambda x: x['tier']):
            expanded.append({**level, 'chain': chain['id'], 'kind': chain['kind'],
                             'family': chain['family'], 'lineage': chain['lineage'],
                             'gates': {**chain['gates'], **level['gates']}, 'presentation': chain['player'],
                             'ai': chain['ai'], 'semantic_review': chain['semantic_review']})
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=['building', 'chain', 'level', *DIMENSIONS,
                                               'space_percent', 'capacity_status', 'constructibility'], lineterminator='\n')
    writer.writeheader()
    for level in expanded:
        writer.writerow({'building': level['id'], 'chain': level['chain'], 'level': level['tier'],
                         **level['conditions'], 'space_percent': level['capacity']['space_percent'],
                         'capacity_status': level['capacity']['status'], 'constructibility': level['constructibility']['status']})
    report = {'counts': counts, 'policy': POLICY, 'source_sha256': hashlib.sha256(json_bytes(data)).hexdigest(),
              'runtime_ready': False, 'generated_live_building_definitions': 0,
              'blocked_levels': [{'id': row['id'], 'reasons': row['constructibility']['reasons']} for row in expanded]}
    return {'levels.json': json_bytes({'schema_version': 1, 'catalogue_id': data['catalogue_id'],
                                      'imports': data['imports'], 'policy': POLICY, 'levels': expanded}),
            'condition_candidates.csv': stream.getvalue().encode('utf-8'),
            'readiness.json': json_bytes(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true', help='Read-only byte parity check; never repair output.')
    args = parser.parse_args()
    output = args.output.resolve()
    # Never turn inert review artifacts into a live CK3 source by CLI accident.
    require(not any(part.lower() in ('mod', 'common', 'events', 'dependencies') for part in output.parts),
            'output must be outside live mod/dependency trees')
    data = load_source(args.source)
    artifacts = compile_catalogue(data)
    if args.check:
        require(output.is_dir(), 'missing generated directory')
        require({p.name for p in output.iterdir()} == set(artifacts), 'unexpected/missing generated artifacts')
        for name, expected in artifacts.items():
            require((output / name).read_bytes() == expected, f'stale generated artifact: {name}')
    else:
        if output.exists():
            require({p.name for p in output.iterdir()} <= set(artifacts), 'refusing to overwrite unmanaged output directory')
        output.mkdir(parents=True, exist_ok=True)
        for name, content in artifacts.items():
            (output / name).write_bytes(content)
    print('PASS: 131 chains / 771 levels; 3 deterministic review artifacts; runtime activation disabled')


if __name__ == '__main__':
    try:
        main()
    except (ContractError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f'Catalogue validation failed: {exc}') from exc
