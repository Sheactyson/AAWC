"""One-time, hash-verified D7/D8 bootstrap. Refuses to overwrite authored source.

After import, catalogue/stage3/catalogue.json is the only editable authority.
This utility is retained to audit the import, not as a second generation path.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import generate_aawc_stage3_catalogue as gen

IMPORTED = gen.ROOT / 'evidence/stage3/imported'
CHAINS = 'AAWC_Reforging_Proposed_Building_Chains_v2.csv'
LEVELS = 'AAWC_Reforging_Proposed_Building_Levels_v2.csv'


def table(name):
    with (IMPORTED / name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def build_source():
    provenance = json.loads((IMPORTED / 'provenance.json').read_text(encoding='utf-8'))
    imports = []
    for entry in provenance['files']:
        path = IMPORTED / Path(entry['path']).name
        gen.require(path.stat().st_size == entry['bytes'] and
                    hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'],
                    f'historical source hash mismatch: {path.name}')
        imports.append({'path': path.relative_to(gen.ROOT).as_posix(), 'sha256': entry['sha256']})
    chains = table(CHAINS)
    levels = table(LEVELS)
    eligibility = {x['chain_id']: x for x in table('AAWC_REFORGING_M1_V2_ELIGIBILITY_REVIEW.csv')}
    lineage = {x['v2_chain_id']: x for x in table('AAWC_REFORGING_M1_V2_LEGACY_LINEAGE.csv')}
    flagged = {x['v2_chain_id']: x for x in table('AAWC_REFORGING_M1_V2_SPECIAL_IDENTITY_REVIEW.csv')}
    gen.require(len(chains) == len(eligibility) == 131 and len(lineage) == 105 and len(flagged) == 40,
                'historical review census mismatch')
    gen.require({r['chain_id'] for r in levels} == {r['chain_id'] for r in chains}, 'orphan/missing level chains')
    result = []
    for row in sorted(chains, key=lambda x: x['chain_id']):
        cid = row['chain_id']
        gate = eligibility[cid]
        tier_rows = sorted((x for x in levels if x['chain_id'] == cid), key=lambda x: int(x['level']))
        gen.require(len(tier_rows) == int(row['levels']), f'{cid}: source tier count')
        legacy = lineage.get(cid)
        old_by_tier = {}
        if legacy:
            gen.require(row['legacy_chain'] == legacy['legacy_chain'], f'{cid}: legacy chain mismatch')
            for bid in legacy['legacy_ids'].split(' | '):
                match = re.search(r'_(\d+)$', bid)
                gen.require(match is not None, f'{bid}: legacy tier cannot be inferred safely')
                tier = int(match.group(1))
                gen.require(tier not in old_by_tier, f'{cid}: ambiguous legacy tier')
                old_by_tier[tier] = bid
            gen.require(sorted(old_by_tier) == list(range(1, int(row['legacy_level_count']) + 1)), f'{cid}: legacy tier mapping differs')
            gen.require(len(old_by_tier) <= len(tier_rows), f'{cid}: legacy tiers would be lost')
        else:
            gen.require(not row['legacy_chain'], f'{cid}: missing legacy review')
        authored_levels = []
        for index, item in enumerate(tier_rows):
            bid, tier = item['level_id'], int(item['level'])
            gen.require(item['slot_class'] == row['slot_class'] and int(item['level_count']) == len(tier_rows), f'{bid}: source classification drift')
            scores = dict.fromkeys(gen.DIMENSIONS, 0)
            dimensions = [item[f'{role}_dimension'].lower() for role in ('primary', 'secondary', 'tradeoff')]
            gen.require(len(set(dimensions)) == 3, f'{bid}: overlapping authored dimensions require review')
            for role, dimension in zip(('primary', 'secondary', 'tradeoff'), dimensions):
                gen.require(dimension in scores, f'{bid}: unknown dimension')
                scores[dimension] = int(item[f'{role}_score_cumulative'])
            reasons = ['candidate_semantics_and_balance_unapproved',
                       'construction_predicate_composition_unapproved' if legacy else 'new_chain_predicate_missing',
                       'capacity_space_mapping_unspecified', 'player_localization_and_assets_missing', 'ai_contract_missing']
            if cid in flagged:
                reasons.append('flagged_identity_requires_review')
            authored_levels.append({
                'id': bid, 'legacy_id': old_by_tier.get(tier), 'tier': tier,
                'upgrades_to': tier_rows[index + 1]['level_id'] if index + 1 < len(tier_rows) else None,
                'costs': {currency: int(item[f'{currency}_cost']) for currency in ('gold', 'prestige', 'piety')},
                'construction_days': int(item['construction_days']), 'conditions': scores,
                'capacity': {'status': 'missing', 'space_percent': None},
                'tradeoffs': {'negative_conditions': {k: v for k, v in scores.items() if v < 0}, 'notes': None},
                'gates': {'era_innovation_proposal': item['era_innovation_gate_candidate'],
                          'geography_proposal': item['geography_contract']},
                'native_role': {'status': 'deferred', 'proposal': {
                    'economic_potential_pct_cumulative': item['economic_potential_pct_cumulative'],
                    'workforce_requirement_candidate': item['workforce_requirement_candidate'],
                    'native_effect_contract': item['native_effect_contract'],
                    'chain_role': row['ck3_role'], 'distinct_identity': row['distinct_identity'],
                    'construction_rationale': row['construction_rationale'], 'review_status': item['review_status']}},
                'constructibility': {'status': 'blocked_review', 'reasons': reasons},
                'player': {'name': None, 'name_key': f'building_{bid}',
                           'description_key': f'building_{bid}_desc',
                           'effect_description_key': f'aawc_stage3_{bid}_effects'}})
        for role in ('primary', 'secondary', 'tradeoff'):
            gen.require(authored_levels[-1]['conditions'][row[f'{role}_dimension'].lower()] == int(row[f'{role}_score']), f'{cid}: final cumulative score differs')
        result.append({'id': cid, 'kind': row['slot_class'], 'family': row['category'],
                       'lineage': {'status': 'legacy' if legacy else 'new', 'legacy_chain': row['legacy_chain'] or None},
                       'gates': {'status': 'proposed' if legacy else 'missing', 'proposal': row['geography'],
                                 'source_predicates': gate['extracted_predicate_citations'] or None,
                                 'source_reference': gate['source_definition_path_line'] or None},
                       'player': {'status': 'missing', 'name': row['display_name'], 'description': None,
                                  'icon': None, 'model': None, 'effect_description': None},
                       'ai': {'status': 'missing', 'value': None},
                       'semantic_review': {'status': 'pending',
                                           'reason': flagged[cid]['human_review_issue'] if cid in flagged else row['status'] + ': ' + row['mapping_risk']},
                       'levels': authored_levels})
    data = {'schema_version': 1, 'catalogue_id': 'aawc_stage3_d7_d8_v2',
            'imports': sorted(imports, key=lambda x: x['path']), 'policy': dict(gen.POLICY), 'chains': result}
    gen.validate(data)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=gen.SOURCE)
    parser.add_argument('--check-import', action='store_true', help='Compare original bootstrap with current source without writing. Intended for initial import audit only.')
    args = parser.parse_args()
    content = gen.json_bytes(build_source())
    if args.check_import:
        gen.require(args.output.read_bytes() == content, 'source differs from historical bootstrap (may be an intentional authored revision)')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as stream:
            stream.write(content)
    print('PASS: exact historical 131-chain / 771-level import; no product decisions approved')


if __name__ == '__main__':
    main()
