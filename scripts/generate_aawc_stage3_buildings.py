"""Compile the authorized Stage 3 construction overlay; no demographic/native outputs.

--derive refreshes a reviewable predicate snapshot from the effective CK3 stack.
Normal generation uses only repository authorities, never the installed game.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

from generate_aawc_stage3_catalogue import ROOT, SOURCE, load_source, validate, require, json_bytes
from validate_aawc_reforging_stage1_cohort_engine import definition_body, top_level_definitions

MOD = ROOT / 'mod/AGOT_Alternate_World_Compatch'
CONSTRUCTION = ROOT / 'catalogue/stage3/construction.json'
BUILDINGS = MOD / 'common/buildings/zz_aawc_stage3_catalogue.txt'
LOC = MOD / 'localization/english/aawc_stage3_buildings_l_english.yml'
METADATA = ROOT / 'catalogue/stage3/runtime_metadata.json'
STANDARD_HOLDINGS = MOD / 'common/holdings/00_holdings.txt'
REGIONAL_HOLDINGS = MOD / 'common/holdings/zz_aawc_regional_blocker_holdings.txt'
HOLDING_TARGETS = {
    STANDARD_HOLDINGS: ('castle_holding', 'tribal_holding', 'city_holding', 'church_holding',
                        'temple_citadel_holding'),
    REGIONAL_HOLDINGS: ('pirate_den_holding', 'settlement_holding'),
}
HOLDING_MARKER_START = '# BEGIN AAWC STAGE 3 CONSTRUCTIBLE ROOTS (generated)'
HOLDING_MARKER_END = '# END AAWC STAGE 3 CONSTRUCTIBLE ROOTS (generated)'
GATE_KEYS = ('can_construct_potential', 'can_construct', 'can_construct_showing_failures_only', 'is_enabled')
# Building predicates execute in province scope.  The population settlement
# trigger executes in landed-title scope, so injecting it here hides every
# generated building even in a valid holding.  Keep the same authoritative
# holding whitelist, expressed with province-scope predicates.
# Nomad and herder holdings explicitly declare the native ``no_buildings``
# parameter and expose no construction allow-list.  They are populated holding
# forms, but they are not valid Stage 3 construction surfaces.
SETTLED = 'OR = { has_holding_type = castle_holding has_holding_type = tribal_holding has_holding_type = city_holding has_holding_type = church_holding has_holding_type = temple_citadel_holding has_holding_type = pirate_den_holding has_holding_type = settlement_holding }'
URBAN = 'OR = { has_holding_type = city_holding has_holding_type = castle_holding }'
MILITARY = 'OR = { has_holding_type = castle_holding has_holding_type = tribal_holding }'
WATER = 'OR = { is_coastal = yes is_riverside_province = yes }'
ERAS = {'starting_or_culture_gated': None, 'early_medieval_candidate': 'innovation_manorialism',
        'high_medieval_candidate': 'innovation_windmills', 'late_medieval_candidate': 'innovation_cranes'}
NATIVE_GATE_KEYS = set('AND OR NOT NOR NAND LEVEL any_county_province capital_province count county county.faith county.holder county.holder.culture culture custom_description custom_tooltip development_level faith geographical_region government_has_flag has_building_or_higher has_building has_character_flag has_county_modifier has_cultural_parameter has_cultural_tradition has_dlc has_dlc_feature has_doctrine_parameter has_holding_type has_innovation has_province_modifier has_title has_variable highest_held_title_tier is_coastal is_county_capital is_independent_ruler is_riverside_province limit scope:holder scope:holder.culture scope:holder.faith scope:holder.liege terrain text trigger_if trigger_else trigger_else_if'.split())

def gate_keys(text):
    return set(re.findall(r'(?<![\w:])([A-Za-z_][A-Za-z0-9_.:]*)\s*(?:\?=|=|>=|<=|>|<)',text))

def validate_gate_syntax(text):
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|>=|<=|!=|\?=|[{}=<>]|[^\s{}=<>!?]+',text)
    pos=0
    def block(nested=False):
        nonlocal pos
        while pos<len(tokens) and tokens[pos]!='}':
            require(pos+2<len(tokens),'incomplete gate expression')
            key,op,value=tokens[pos:pos+3];pos+=3
            require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.:]*',key) and op in ('=','!=','>=','<=','>','<','?='),'malformed gate assignment')
            if value=='{':
                block(True)
                require(pos<len(tokens) and tokens[pos]=='}','unterminated gate')
                pos+=1
            else: require(value not in ('}','=','>','<'),'invalid gate value')
        require(nested or pos==len(tokens),'unexpected closing brace')
    block()

def terrains(*names):
    return 'OR = { ' + ' '.join('agot_is_'+n+'_terrain = yes' for n in names) + ' }'

def building(chain, tier=1):
    return f'has_building_or_higher = aawc_{chain}_{tier:02}'

# Explicit, exhaustive new-chain derivations. No keyword/default eligibility fallback.
# Each tuple is potential, construction, rationale; catalogue geography is retained too.
NEW = {
 'archery_yards': (MILITARY, 'culture = { has_innovation = innovation_barracks }', 'Military holding and professional barracks innovation establish archery training access.'),
 'cavalry_courses': (MILITARY, 'OR = { '+building('stables')+' '+building('horse_pastures')+' '+building('camel_farms')+' '+building('elephant_pens')+' }', 'Require a military holding and an established mount supply chain.'),
 'coastal_fisheries': ('is_coastal = yes', '', 'Sea coast is the fishing-access proxy.'),
 'duchy_agricultural_estates': (terrains('plains','farmlands','floodplains'), 'OR = { '+building('cereal_fields')+' '+building('farm_estates')+' }', 'Arable hinterland plus an installed agricultural supply chain.'),
 'duchy_civic_court': ('', 'county = { development_level >= 10 }', 'Development 10 is the settled administrative threshold.'),
 'duchy_grand_harbor': ('is_coastal = yes', building('common_tradeport'), 'Sea coast and a functioning trade port.'),
 'duchy_grand_hospital': ('', building('infirmaries',3), 'Tier-three infirmary is advanced healthcare.'),
 'duchy_military_college': ('', building('barracks',3), 'Tier-three barracks establishes a professional military institution.'),
 'duchy_royal_theatre': (URBAN, building('public_squares',3), 'Urban capital and tier-three public amenities.'),
 'infirmaries': ('OR = { '+URBAN+' has_holding_type = church_holding }', 'county = { development_level >= 5 }', 'Settled healthcare becomes available at development 5.'),
 'irrigation_estates': (terrains('drylands','desert','oasis'), 'OR = { is_riverside_province = yes '+building('qanats')+' '+building('waterworks')+' }', 'Arid cultivation requires river water or built groundwater/waterworks infrastructure.'),
 'leatherworkers': ('', 'OR = { '+building('pastures')+' '+building('hunting_grounds')+' '+building('common_tradeport')+' '+building('market_villages')+' }', 'Livestock, hunting or established trade supplies hides.'),
 'monument_works': ('OR = { '+URBAN+' has_holding_type = church_holding }', 'county = { development_level >= 10 }', 'Development 10 supports organized monumental work.'),
 'mustering_fields': (MILITARY, 'NOT = { '+terrains('mountains','desert_mountains','glacier')+' }', 'Military holding with open drill ground; exclude extreme mountain/ice sites.'),
 'public_baths': ('', 'OR = { is_riverside_province = yes '+building('waterworks')+' '+building('qanats')+' }', 'Baths require fresh water infrastructure or river access; sea coast alone is insufficient.'),
 'public_squares': (URBAN, '', 'A built city or castle supplies the populated settlement prerequisite.'),
 'river_docks': ('is_riverside_province = yes', '', 'Engine riverside predicate is the available river-bank proxy; it does not distinguish navigability.'),
 'river_fisheries': ('is_riverside_province = yes', '', 'Riverside access is the supported freshwater proxy; no invented lake/navigability predicate.'),
 'saltworks': ('is_coastal = yes '+terrains('drylands','desert','oasis'), '', 'Arid coastal evaporation route; no unverified salt-deposit modifier invented.'),
 'scholars_quarters': ('OR = { '+URBAN+' has_holding_type = church_holding }', 'OR = { '+building('monastic_schools')+' '+building('scriptorium')+' }', 'Existing school or scriptorium establishes institutional training.'),
 'sewers': (URBAN, 'county = { development_level >= 10 } OR = { has_building_or_higher = city_02 has_building_or_higher = castle_02 }', 'Urban holding tier two and development 10 establish sufficient settlement scale; engineered disposal need not require a river.'),
 'shipwrights': (WATER, '', 'Coast or riverside is the engine-supported shipyard reach proxy.'),
 'terraced_farms': (terrains('hills','mountains'), '', 'Temperate hill/mountain terraces; excludes desert mountains and frozen terrain.'),
 'trade_guilds': ('', 'OR = { has_holding_type = city_holding AND = { county = { development_level >= 10 } '+building('market_villages')+' } }', 'Cities or developed market settlements establish a trade hub.'),
 'urban_tenements': (URBAN, 'OR = { has_holding_type = city_holding has_building_or_higher = castle_02 }', 'Cities or tier-two castles provide urban housing scale.'),
 'village_cottages': ('OR = { has_holding_type = castle_holding has_holding_type = church_holding has_holding_type = tribal_holding }', '', 'Rural castle, temple or tribal settlement provides cottage habitation.'),
}

def clean(text):
    return '\n'.join(l.split('#',1)[0].strip() for l in text.splitlines() if l.split('#',1)[0].strip())

def fields(body):
    result = {}
    for key in GATE_KEYS:
        try: result[key] = clean(definition_body(body, key))
        except ValueError: result[key] = ''
    return result

def effective_sources(roots, wanted):
    # File replacement precedes ordered duplicate-definition overrides.
    files = {}
    for label, root in roots:
        for p in sorted((root / 'common/buildings').glob('*.txt')):
            if p.name != BUILDINGS.name:
                files[p.name] = (label, root, p)
    result = {}
    for _, (label, root, path) in sorted(files.items()):
        text = path.read_text(encoding='utf-8-sig')
        for bid in top_level_definitions(text) & wanted:
            result[bid] = (definition_body(text,bid), label+'/'+path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
    return result

def derive(data, roots):
    sources = effective_sources(roots, {l["legacy_id"] for c in data["chains"] for l in c["levels"] if l["legacy_id"]})
    # A few documented CK3 lineages are absent from AGOT's same-name replacement
    # files. Recover their cited base predicates explicitly, never assume unrestricted.
    for chain in data['chains']:
        missing = [l['legacy_id'] for l in chain['levels'] if l['legacy_id'] and l['legacy_id'] not in sources]
        if missing:
            reference = chain['gates']['source_reference'].rsplit(':',1)[0]
            label, relative = reference.split('/',1)
            root = dict(roots)[label]
            path = root / relative
            text = path.read_text(encoding='utf-8-sig')
            for bid in missing:
                sources[bid] = (definition_body(text,bid),label+' (cited base fallback)/'+relative,hashlib.sha256(path.read_bytes()).hexdigest())
    symbols = {}
    for category in ('scripted_triggers', 'culture/innovations'):
        found = set()
        for _, root in roots:
            for path in (root/'common'/category).glob('*.txt'):
                found |= top_level_definitions(path.read_text(encoding='utf-8-sig'))
        symbols[category] = sorted(found)
    # Used for direct new-definition reference closure. Missing legacy adapter
    # symbols are separately reported; never presented as effective definitions.
    # Collect all effective IDs without extracting thousands of unused bodies.
    files={}
    for _,root in roots:
        for path in (root/'common/buildings').glob('*.txt'):
            if path.name != BUILDINGS.name: files[path.name]=path
    symbols['buildings']=sorted(set().union(*(top_level_definitions(p.read_text(encoding='utf-8-sig')) for p in files.values())))
    result = {'schema_version': 1, 'policy': 'authorized_identity_ecology_v1', 'symbols':symbols, 'chains': {}}
    for chain in data['chains']:
        cid = chain['id']; short = cid.removeprefix('aawc_')
        row = {'catalogue_geography': chain['gates']['proposal'], 'rationale': '', 'levels': {}}
        if chain['lineage']['status'] == 'new':
            potential, construction, rationale = NEW[short]
            row['rationale'] = rationale
            base = dict.fromkeys(GATE_KEYS,'')
            base['can_construct_potential'] = potential
            base['can_construct'] = construction
        else:
            original, _, _ = sources[chain['levels'][0]['legacy_id']]
            base = fields(original)
            row['rationale'] = 'Preserve effective lineage geography, culture, faith, law and prerequisites at every tier; add the catalogue era schedule. Retain construction restrictions without copying native outputs.'
        for level in chain['levels']:
            legacy = level['legacy_id']
            if legacy:
                body, source, digest = sources[legacy]
                gates = fields(body)
                for key in GATE_KEYS:
                    gates[key] = '\n'.join(dict.fromkeys(x for x in (base[key],gates[key]) if x))
                provenance = {'path':source, 'sha256':digest, 'building':legacy}
            else:
                gates = dict(base)
                provenance = {'path':'catalogue/stage3/catalogue.json', 'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'building':level['id']}
            # These source lineages are main holdings. Catalogue versions are annexes,
            # never alternative main holdings or a way around the native holding cost.
            if short == 'tribe':
                gates = dict.fromkeys(GATE_KEYS,'')
                gates['can_construct_potential'] = 'has_holding_type = tribal_holding'
                row['rationale'] = 'Tribal housing annex: preserve tribal identity; replace source main-holding always=no and main-holding upgrade requirements. Do not replace tribe_01 or create a holding.'
            if short == 'temple_citadel':
                gates = dict.fromkeys(GATE_KEYS,'')
                gates['can_construct_potential'] = 'has_holding_type = temple_citadel_holding scope:holder = { government_has_flag = government_is_mandala }'
                row['rationale'] = 'Temple-citadel annex inside an existing temple-citadel holding; retain Mandala institution, remove empty-barony/main-holding creation rules.'
            if short == 'city_walls':
                gates['can_construct_potential'] += '\nhas_holding_type = city_holding'
                row['rationale'] += ' Catalogue city identity additionally requires a city holding.'
            if short == 'dragon_kiln':
                row['rationale'] += ' Proven source cultural kiln access is the eligible-lore route; no unsupported Dragonstone-only restriction is invented.'
            if short == 'hospices':
                row['rationale'] += ' Healthcare identity and effective hospice source override the imported crop/moisture boilerplate.'
            row['levels'][level['id']] = {'gates':gates, 'provenance':provenance}
        result['chains'][cid] = row
    return result

def remap_reads(text, mapping):
    # Preserve external/legacy callers and target prerequisites during transition.
    def replace(m):
        key, old = m.groups()
        if old not in mapping: return m.group(0)
        return f'OR = {{ {key} = {old} {key} = {mapping[old]} }}'
    return re.sub(r'\b(has_building_or_higher|has_building)\s*=\s*([a-zA-Z0-9_]+)',replace,text)

def matching_brace(text, opening):
    """Return the closing brace while ignoring comments and quoted text."""
    require(text[opening] == '{', 'brace scan must start at an opening brace')
    depth = 0; quoted = False; escaped = False; comment = False
    for pos in range(opening, len(text)):
        char = text[pos]
        if comment:
            if char == '\n': comment = False
            continue
        if quoted:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == '"': quoted = False
            continue
        if char == '#': comment = True
        elif char == '"': quoted = True
        elif char == '{': depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0: return pos
    raise ValueError('unterminated brace block')

def holding_buildings(text, holding):
    """Read a holding's registered first-tier building IDs."""
    match = re.search(r'(?m)^'+re.escape(holding)+r'\s*=\s*\{', text)
    require(match is not None, f'missing holding definition {holding}')
    holding_open = text.find('{', match.start())
    holding_close = matching_brace(text, holding_open)
    body = text[holding_open + 1:holding_close]
    buildings = re.search(r'(?m)^\s*buildings\s*=\s*\{', body)
    require(buildings is not None, f'{holding}: missing buildings block')
    buildings_open = holding_open + 1 + body.find('{', buildings.start())
    buildings_close = matching_brace(text, buildings_open)
    registered = []
    for line in text[buildings_open + 1:buildings_close].splitlines():
        value = line.split('#', 1)[0].strip()
        if re.fullmatch(r'[A-Za-z0-9_]+', value): registered.append(value)
    return registered, buildings_close

def register_stage3_roots(path, holdings, roots):
    """Add generated construction roots to the effective holding allow-lists."""
    raw = path.read_bytes(); had_bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    marker = re.compile(r'(?m)^\s*'+re.escape(HOLDING_MARKER_START)+r'\s*$.*?^\s*'+re.escape(HOLDING_MARKER_END)+r'\s*$\n?', re.S)
    text = marker.sub('', text)
    block = ('\t\t'+HOLDING_MARKER_START+'\n'
             + ''.join('\t\t'+root+'\n' for root in roots)
             + '\t\t'+HOLDING_MARKER_END+'\n')
    for holding in holdings:
        existing, closing = holding_buildings(text, holding)
        require(not (set(existing) & set(roots)), f'{holding}: unmanaged Stage 3 registration')
        line_start = text.rfind('\n', 0, closing) + 1
        text = text[:line_start] + block + text[line_start:]
    payload = text.encode('utf-8-sig' if had_bom else 'utf-8')
    # Reparse the emitted payload so a malformed insertion cannot be packaged.
    emitted = payload.decode('utf-8-sig')
    for holding in holdings:
        registered, _ = holding_buildings(emitted, holding)
        require(set(roots) <= set(registered), f'{holding}: incomplete Stage 3 registration')
    return payload

def compile_buildings(data, contract):
    validate(data)
    require(set(contract)=={'schema_version','policy','symbols','chains'} and contract['schema_version']==1 and contract['policy']=='authorized_identity_ecology_v1', 'construction schema/policy mismatch')
    require(set(contract['symbols'])=={'scripted_triggers','culture/innovations','buildings'},'engine symbol schema')
    chains = {c['id']:c for c in data['chains']}
    require(set(contract['chains'])==set(chains),'construction chain coverage mismatch')
    mapping = {l['legacy_id']:l['id'] for c in chains.values() for l in c['levels'] if l['legacy_id']}
    # Main holdings stay main holdings; an annex is not a substitute holding tier.
    for c in chains.values():
        if c['id'] in ('aawc_tribe','aawc_temple_citadel'):
            for l in c['levels']: mapping.pop(l['legacy_id'],None)
    script = ['# Generated from catalogue.json + construction.json. Native outputs remain deferred.']
    loc = ['l_english:']; metadata = []
    def localized(key, value):
        loc.append(' '+key+':0 '+json.dumps(value,ensure_ascii=False))
    for cid,c in sorted(chains.items()):
        rule = contract['chains'][cid]
        require(set(rule)=={'catalogue_geography','rationale','levels'} and rule['rationale'] and rule['catalogue_geography']==c['gates']['proposal'],f'{cid}: missing/stale derivation')
        require(set(rule['levels'])=={l['id'] for l in c['levels']},f'{cid}: level coverage mismatch')
        for l in sorted(c['levels'],key=lambda x:x['tier']):
            bid=l['id']; r=rule['levels'][bid]
            require(set(r)=={'gates','provenance'} and set(r['gates'])==set(GATE_KEYS),f'{bid}: gate schema')
            require(set(r['provenance'])=={'path','sha256','building'} and re.fullmatch('[0-9a-f]{64}',r['provenance']['sha256']) is not None,f'{bid}: provenance')
            for gate in r['gates'].values():
                require(isinstance(gate,str) and gate.count('{')==gate.count('}') and not re.search(r'\balways\s*=\s*no\b',gate),f'{bid}: malformed or disabled gate')
                validate_gate_syntax(gate)
                require(not (gate_keys(gate)-NATIVE_GATE_KEYS-set(contract['symbols']['scripted_triggers'])),f'{bid}: unknown gate trigger {gate_keys(gate)-NATIVE_GATE_KEYS-set(contract["symbols"]["scripted_triggers"])}')
            gates={k:remap_reads(v,mapping) for k,v in r['gates'].items()}
            gates['can_construct_potential'] = SETTLED+'\n'+gates['can_construct_potential']
            era=l['gates']['era_innovation_proposal']
            require(era in ERAS,f'{bid}: unknown era')
            if ERAS[era]: gates['can_construct_showing_failures_only']+='\nculture = { has_innovation = '+ERAS[era]+' }'
            if c['kind']=='duchy':
                gates['can_construct']+='\ncounty.holder = { has_title = prev.duchy }'
                gates['is_enabled']+='\ncounty.holder = { has_title = prev.duchy }'
            joined='\n'.join(gates.values())
            refs=set(re.findall(r'\bhas_building(?:_or_higher)?\s*=\s*(\w+)',joined))
            require(not (refs-set(mapping.values())-{l['id'] for ch in chains.values() for l in ch['levels']}-set(contract['symbols']['buildings'])),f'{bid}: unresolved building prerequisite')
            innovations=set(re.findall(r'has_innovation\s*=\s*(\w+)',joined))
            require(not (innovations-set(contract['symbols']['culture/innovations'])),f'{bid}: unresolved innovation')
            positive=sum(max(v,0) for v in l['conditions'].values())
            negative=-sum(min(v,0) for v in l['conditions'].values())
            ai=max(1,10+positive-negative)
            script += ['',bid+' = {',f' construction_time = {l["construction_days"]}', ' cost = { '+' '.join(f'{k} = {v}' for k,v in l['costs'].items())+' }']
            # CK3 regular buildings omit ``type``.  ``regular`` is not an engine
            # building class and causes otherwise valid catalogue entries to be
            # excluded from the construction menu.  Only duchy buildings carry
            # the explicit native class.
            if c['kind']=='duchy': script.append(' type = duchy_capital')
            script += [' type_icon = "icon_building_market_villages.dds"', ' show_disabled = yes']
            for key,value in gates.items():
                if value.strip(): script.append(' '+key+' = {\n  '+value.strip().replace('\n','\n  ')+'\n }')
            if l['upgrades_to']: script.append(' next_building = '+l['upgrades_to'])
            # CK3 suppresses ``effect_desc`` in the construction UI when a
            # building has no native modifier block.  A rendered 1.11.3.6
            # probe established that an exactly-zero modifier is sufficient
            # to expose the custom description while adding no gameplay
            # output and no visible "+0" modifier line.
            script += [
                ' county_modifier = { development_growth_factor = 0 }',
                ' effect_desc = '+l['player']['effect_description_key'],
                f' ai_value = {{ base = {ai} }}',
                '}',
            ]
            name=re.sub(r'\s*\([^)]*\)','',c['player']['name'])+' '+str(l['tier'])
            scores='; '.join(f'{d.title()} {v:+g}' for d,v in l['conditions'].items() if v)
            effects=(scores+'; ' if scores else '')+f'Settlement space {l["capacity"]["space_percent"]:+g}%.'
            localized(l['player']['name_key'],name)
            localized(l['player']['description_key'],c['levels'][0]['native_role']['proposal']['distinct_identity'].capitalize()+'.')
            localized(l['player']['effect_description_key'],'Structural conditions: '+effects+' Cumulative installed-tier values; replaces the preceding tier. Native economic and military outputs are deferred.')
            if l['tier']==1:
                localized('building_type_'+bid,re.sub(r'\s*\([^)]*\)','',c['player']['name']))
                localized('building_type_'+bid+'_desc',c['levels'][0]['native_role']['proposal']['distinct_identity'].capitalize()+'.')
            metadata.append({'id':bid,'chain':cid,'tier':l['tier'],'ai_value':ai,'native_role':l['native_role'], 'era_innovation':ERAS[era], 'gates':gates, 'provenance':r['provenance'], 'derivation':rule['rationale'], 'icon':'icon_building_market_villages.dds','model':'none: optional regular/duchy building asset; existing holding visualization retained'})
    roots = sorted(c['levels'][0]['id'] for c in chains.values())
    artifacts = {
        BUILDINGS: ('\n'.join(script)+'\n').encode('utf-8-sig'),
        LOC: ('\n'.join(loc)+'\n').encode('utf-8-sig'),
        METADATA: json_bytes({'policy':contract['policy'],'target_definitions':771,'chains':131,'construction_status':'source_activated','rendered_certification':False,'levels':metadata}),
    }
    for path, holdings in HOLDING_TARGETS.items():
        artifacts[path] = register_stage3_roots(path, holdings, roots)
    return artifacts

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check',action='store_true'); p.add_argument('--derive',action='store_true')
    p.add_argument('--game',type=Path);p.add_argument('--agot',type=Path)
    args=p.parse_args();data=load_source(SOURCE)
    if args.derive:
        require(not args.check and args.game and args.agot,'derive requires game and AGOT roots')
        require(not CONSTRUCTION.exists(),'refusing to overwrite authored construction policy')
        contract=derive(data,[('CK3',args.game),('AGOT',args.agot),('dependencies/AAWC_Dependencies_Modpack',ROOT/'dependencies/AAWC_Dependencies_Modpack'),('mod/AGOT_Alternate_World_Compatch',MOD)])
        # Validate before writing the authoritative snapshot.
        compile_buildings(data,contract)
        CONSTRUCTION.write_bytes(json_bytes(contract))
    artifacts=compile_buildings(data,load_source(CONSTRUCTION))
    for path,payload in artifacts.items():
        if args.check: require(path.is_file() and path.read_bytes()==payload,f'stale {path}')
        else: path.write_bytes(payload)
    print('Stage 3 construction: 131 chains / 771 definitions; '+('parity verified' if args.check else 'generated'))

if __name__=='__main__': main()
