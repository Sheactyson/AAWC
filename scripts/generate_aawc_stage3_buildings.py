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
RETAINED_LOC = MOD / 'localization/english/aawc_retained_building_presentation_l_english.yml'
METADATA = ROOT / 'catalogue/stage3/runtime_metadata.json'
STANDARD_HOLDINGS = MOD / 'common/holdings/00_holdings.txt'
REGIONAL_HOLDINGS = MOD / 'common/holdings/zz_aawc_regional_blocker_holdings.txt'
HOLDING_TARGETS = {
    STANDARD_HOLDINGS: ('castle_holding', 'tribal_holding', 'city_holding', 'church_holding',
                        'temple_citadel_holding'),
    REGIONAL_HOLDINGS: ('monastery_holding', 'pirate_den_holding', 'settlement_holding'),
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
SETTLED = 'OR = { has_holding_type = castle_holding has_holding_type = tribal_holding has_holding_type = city_holding has_holding_type = church_holding has_holding_type = temple_citadel_holding has_holding_type = monastery_holding has_holding_type = pirate_den_holding has_holding_type = settlement_holding }'
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


def stage3_icon(chain_id):
    """Return the deliberately chain-specific interface icon filename.

    A building chain evolves one underlying structure through its tiers, so those
    tiers share an icon.  Different chains never share an icon: that keeps the
    construction catalogue legible even where their gameplay families overlap.
    """
    require(chain_id.startswith('aawc_'), f'{chain_id}: invalid Stage 3 chain ID')
    return chain_id + '.dds'


# Positive AAWC-to-AAWC construction dependencies. Each schedule entry is
# ``(first target tier, required source tier)``; the last entry at or below the
# current target tier applies. Multiple sources inside one requirement are an
# OR route, while multiple requirements on one target are cumulative (AND).
# Duchy chains depend only on ordinary-slot foundations, never another duchy
# chain that could not coexist in the same capital's single special slot.
REGULAR_8 = ((1, 1), (3, 2), (5, 3), (7, 4))
REGULAR_6 = ((1, 1), (3, 2), (5, 3))
DUCHY_3 = ((1, 3), (2, 5), (3, 7))


def progression(sources, schedule, rationale):
    if isinstance(sources, str):
        sources = (sources,)
    return {'sources': tuple(sources), 'schedule': tuple(schedule), 'rationale': rationale}


PREREQUISITE_PROGRESSIONS = {
    # Professional military institutions grow out of basic drill and supply.
    'archery_yards': (progression('barracks', REGULAR_8, 'Professional archery training requires an established barracks system.'),),
    'cavalry_courses': (progression('barracks', REGULAR_8, 'Mounted specialization requires professional troop organization in addition to an eligible mount supply.'),),
    'mustering_fields': (progression('barracks', REGULAR_6, 'Large civilian musters require an established military administration.'),),
    'regimental_grounds': (progression('barracks', REGULAR_8, 'Regimental drill expands from the barracks hierarchy.'),),
    'warrior_lodges': (progression('barracks', REGULAR_8, 'Permanent martial societies require a supporting barracks system.'),),
    # Processing and specialist production require their material foundations.
    'breweries': (progression('cereal_fields', REGULAR_8, 'Brewing capacity follows the local grain supply.'),),
    'farm_estates': (progression('cereal_fields', REGULAR_8, 'Manorial estates require a developed staple-farming base.'),),
    'plantations': (progression('farm_estates', REGULAR_8, 'Plantation estates grow out of organized landed estates.'),),
    'spice_plantation': (progression('plantations', REGULAR_8, 'Specialist spice estates require mature plantation administration.'),),
    'urban_farms': (progression('waterworks', REGULAR_8, 'Dense urban cultivation depends on progressively stronger water infrastructure.'),),
    'murex_farm': (progression('coastal_fisheries', REGULAR_8, 'Murex cultivation requires an established coastal harvesting base.'),),
    'wind_furnace': (progression('smiths', REGULAR_8, 'Advanced furnace engineering requires mature smithing workshops.'),),
    'powder_magazine': (progression('smiths', ((1, 2), (3, 3), (5, 4), (7, 5)), 'Powder manufacture and storage require progressively stronger metalworking support.'),),
    'leatherworkers': (progression('workshops', REGULAR_6, 'Specialist hide processing requires general craft infrastructure as well as a hide supply.'),),
    'shipwrights': (progression('workshops', ((1, 1), (3, 2)), 'Shipbuilding yards require an established craft district.'),),
    # Civic and commercial specializations depend on basic urban institutions.
    'guild_halls': (progression('workshops', REGULAR_8, 'Guild halls require a progressively developed city craft base.'),),
    'caravanserai': (progression('workshops', REGULAR_8, 'Long-distance caravan services require a local craft and repair base.'),),
    'river_docks': (progression('workshops', REGULAR_6, 'River commerce docks require a supporting craft district.'),),
    'monument_works': (progression('workshops', REGULAR_6, 'Monumental construction requires organized local crafts.'),),
    'urban_tenements': (progression('public_squares', REGULAR_6, 'Dense housing follows the staged development of an urban public realm.'),),
    'sewers': (progression('waterworks', REGULAR_6, 'Engineered sewerage requires progressively developed water infrastructure.'),),
    'irrigation_estates': (progression(('waterworks', 'qanats'), ((1, 1), (3, 2), (5, 3), (7, 4)), 'Agricultural irrigation may advance through either public waterworks or qanat engineering.'),),
    'public_baths': (progression(('waterworks', 'qanats'), REGULAR_6, 'Bathhouse scale follows the available fresh-water infrastructure.'),),
    'scholars_quarters': (progression(('monastic_schools', 'scriptorium'), REGULAR_6, 'Lay scholarly communities require a progressively developed teaching or manuscript institution.'),),
    # Duchy institutions consume ordinary slots as foundations; none require a
    # second duchy building that could not coexist in the same capital.
    'duchy_agricultural_estates': (progression(('cereal_fields', 'farm_estates'), DUCHY_3, 'Regional estates require high-tier local agricultural infrastructure.'),),
    'duchy_civic_court': (progression('capital_bureau', DUCHY_3, 'Duchy courts require a mature local civil service.'),),
    'duchy_grand_harbor': (progression('common_tradeport', DUCHY_3, 'A grand harbor authority requires a high-tier local port.'),),
    'duchy_grand_hospital': (progression('infirmaries', ((1, 3), (2, 4), (3, 6)), 'A regional hospital requires progressively advanced clinical infrastructure.'),),
    'duchy_military_college': (progression('barracks', DUCHY_3, 'A military college requires a mature professional barracks system.'),),
    'duchy_royal_theatre': (progression('public_squares', ((1, 3), (2, 4), (3, 5)), 'A royal theatre requires a mature public cultural realm.'),),
    'archery_ranges': (progression('archery_yards', DUCHY_3, 'Regional ranges require high-tier local archery training grounds.'),),
    'blacksmiths': (progression('smiths', DUCHY_3, 'Duchy blacksmithing requires high-tier local smiths.'),),
    'jousting_lists': (progression('cavalry_courses', ((1, 2), (2, 4), (3, 6)), 'Jousting institutions require developed mounted training.'),),
    'military_academy': (progression('regimental_grounds', DUCHY_3, 'A military academy requires mature regimental drill grounds.'),),
    'royal_armory': (progression('smiths', ((1, 4), (2, 6), (3, 8)), 'A royal armory requires the highest tiers of local metalworking.'),),
    'siege_works': (
        progression('quarries', DUCHY_3, 'Permanent siege works require high-tier stone supply.'),
        progression('smiths', DUCHY_3, 'Permanent siege works require high-tier metalworking.'),
    ),
    'march': (progression('ramparts', DUCHY_3, 'A marcher command requires mature local fortifications.'),),
    'scholastic_guilds': (progression('scholars_quarters', ((1, 2), (2, 4), (3, 6)), 'Duchy scholastic guilds require a mature lay scholarly community.'),),
    'examination_hall': (progression('capital_bureau', DUCHY_3, 'Examination administration requires a mature civil service.'),),
    'tax_assessor': (progression('capital_bureau', DUCHY_3, 'Regional assessment requires a mature civil service.'),),
    'lighthouse': (progression('common_tradeport', DUCHY_3, 'A regional lighthouse authority requires a high-tier port.'),),
    'royal_garden': (progression('public_squares', ((1, 3), (2, 4), (3, 5)), 'Royal gardens require a mature public amenities base.'),),
    'leisure_palace': (progression('public_squares', ((1, 3), (2, 4), (3, 5)), 'A leisure palace requires a mature public amenities base.'),),
    'royal_forest': (progression('hunting_grounds', DUCHY_3, 'A royal preserve requires mature local game management.'),),
    'dragon_kiln': (progression('smiths', DUCHY_3, 'Dragon kiln engineering requires high-tier metalworking.'),),
    'glass_gardens': (progression('waterworks', DUCHY_3, 'Large glass gardens require high-tier water infrastructure.'),),
    'great_megalith': (progression('megalith', ((1, 3), (2, 6)), 'A great megalith requires an established local megalithic tradition.'),),
    'slave_diplomacy': (progression('slave_camps', DUCHY_3, 'Coercive diplomatic administration requires a mature forced-labor apparatus.'),),
    'slave_intrigue': (progression('slave_camps', DUCHY_3, 'Coercive intelligence administration requires a mature forced-labor apparatus.'),),
    'slave_learning': (progression('slave_camps', DUCHY_3, 'Coercive learning administration requires a mature forced-labor apparatus.'),),
    'slave_martial': (progression('slave_camps', DUCHY_3, 'Coercive military administration requires a mature forced-labor apparatus.'),),
    'slave_stewardship': (progression('slave_camps', DUCHY_3, 'Coercive stewardship administration requires a mature forced-labor apparatus.'),),
}


EFFECTS_POLICY = {
    'structural_conditions': {'status': 'implemented', 'scope': 'holding', 'authority': 'Stage 2 six-dimension contribution adapter'},
    'settlement_space': {'status': 'implemented', 'scope': 'holding', 'authority': 'Stage 2 settlement-space contribution adapter'},
    'construction_unlocks': {'status': 'implemented', 'scope': 'holding/culture/faith/title', 'authority': 'Stage 3 construction predicates'},
    'custom_holding_modifiers': {'status': 'deferred_population_scaling', 'scope': 'this holding', 'authority': 'Stage 7 native output policy'},
    'custom_county_modifiers': {'status': 'deferred_population_scaling', 'scope': 'this county', 'authority': 'Stage 7 native output policy'},
    'custom_holder_modifiers': {'status': 'deferred_population_scaling', 'scope': 'holder', 'authority': 'Stage 7 native output policy'},
    'custom_military_modifiers': {'status': 'deferred_military_lifecycle', 'scope': 'holder/army/MAA', 'authority': 'Stage 6 military lifecycle'},
    'neutral_effect_desc_bridge': {'status': 'implemented_non_gameplay', 'scope': 'presentation only', 'authority': 'rendered Stage 3 effect-description compatibility'},
    'retained_main_line_native_modifiers': {'status': 'implemented_preserved', 'scope': 'upstream-defined holding/county/holder semantics', 'authority': 'effective CK3/AGOT definitions'},
    'retained_old_growth_capacity_effect_desc': {'status': 'removed', 'scope': 'retained main-line buildings', 'authority': 'superseded by Stage 2 conditions and settlement space'},
}


# The descriptions deliberately follow CK3/AGOT's compact building-copy shape:
# one material image, one social consequence, and no out-of-character design
# commentary.  The exact structural values remain in effect_desc, not prose.
FAMILY_FLAVOR = {
    'barrack': 'Drill yards, storehouses, and hard-used quarters gather the people who keep a host ready for war.',
    'brew': 'The smell of mash and woodsmoke hangs over vats where grain is turned into drink, wages, and trade.',
    'civic': 'Clerks, petitioners, and sealed records pass through offices that turn custom into durable administration.',
    'dragon': 'Firewise craftsmen work behind thick walls, where one spark may be worth a fortune or a funeral pyre.',
    'duchy culture': 'Patronage draws masters, scholars, and ambitious courtiers from across the realm to this celebrated institution.',
    'duchy econ': 'A regional institution gathers wealth, expertise, and authority that lesser holdings cannot command alone.',
    'duchy faith': 'Pilgrims and dignitaries come to a sacred work whose rites carry weight far beyond the local community.',
    'duchy mil': 'The finest officers and craftsmen of the realm are gathered here to serve a permanent martial establishment.',
    'faith': 'Ritual, memory, and communal duty are given a lasting home within these consecrated bounds.',
    'farm': 'Ordered plots, stores, and labor turn uncertain soil into a dependable foundation for settled life.',
    'field': 'Season after season, cleared earth and patient labor wrest a steadier harvest from the land.',
    'fish': 'Boats, nets, sheds, and curing tables bind the settlement to the living wealth of its waters.',
    'forest': 'Marked stands and disciplined crews harvest the forest without surrendering every path to the wild.',
    'forge': 'Hammer blows ring from dawn to dusk as raw metal becomes tools, fittings, and arms.',
    'garden': 'Open walks and gathering places give common life a stage, lending dignity to both market day and ceremony.',
    'hospice': 'Clean rooms, practiced hands, and stores of remedies offer care where sickness once meant abandonment.',
    'housing': 'Roofs, hearths, and shared yards make room for households to take root and endure.',
    'hunt': 'Wardens, lodges, and managed trails turn the surrounding wilds into a guarded source of meat and prestige.',
    'market': 'Stalls, counting rooms, and sworn measures draw scattered exchange into an institution merchants can trust.',
    'mill': 'Wind or water drives great stones through the day, sparing hands while feeding a growing settlement.',
    'mine': 'Cuttings, shafts, and guarded stores draw buried wealth into the light at a price paid in sweat and danger.',
    'orchard': 'Tended rows flower in their season, promising fruit, sweetness, and patient prosperity.',
    'pasture': 'Fenced grazing and watchful herders turn open land into meat, hides, wool, and breeding stock.',
    'peat': 'Dark sod is cut, stacked, and dried into fuel where timber is scarce and winters bite deeply.',
    'pirate': 'Rough crews and hidden storehouses make violence, contraband, and the sea into instruments of rule.',
    'port': 'Wharves and warehouses meet the river traffic, carrying inland produce toward distant markets.',
    'quarry': 'Stonecutters open the earth in measured faces, supplying the heavy bones of walls and monuments.',
    'road': 'Courtyards, fodder, wells, and guarded rooms keep caravans moving through uncertain country.',
    'school': 'Teachers, copyists, and disputants preserve hard-won knowledge and train those who will carry it onward.',
    'security': 'Earth, timber, and stone are raised against raiders, forcing every attacker to pay for each step forward.',
    'slave': 'Barracks, pens, and overseers organize coerced labor with a cruelty that stains every gain it produces.',
    'stable': 'Pens, paddocks, and skilled handlers keep valuable beasts healthy, trained, and ready for road or war.',
    'training': 'Targets, drill grounds, and stern instructors turn willing bodies into disciplined specialists.',
    'watch': 'Raised platforms and signal posts extend the settlement\'s sight across road, field, and frontier.',
    'water': 'Channels, cisterns, and careful grades carry water where settlement life requires it most.',
    'workshop': 'Kilns, benches, and crowded yards bring specialized hands together to fashion useful goods.',
}

CHAIN_FLAVOR = {
    'amber_collection': 'Golden resin is washed, sorted, and polished until forest relics become ornaments fit for noble halls.',
    'building_moat': 'A broad ditch and controlled approaches turn the castle itself into an obstacle no hurried assault can ignore.',
    'burial_site': 'Stone chambers and solemn processions bind the ruling house to its ancestors and to the land they claimed.',
    'charnel_grounds': 'The dead are exposed according to ancient rite, beneath the watch of priests and circling birds.',
    'coastal_fisheries': 'Shore boats return with the tide to crowded racks and salting sheds, feeding both hearth and market.',
    'common_tradeport': 'A practical harbor of quays, fish stalls, and warehouses keeps coastal traffic moving in every season.',
    'godswood': 'Within a sheltered grove, old trees and older silence offer a place for counsel, prayer, and remembrance.',
    'ironwood': 'Ironwood is felled only with patience; its dense timber rewards that labor in beams, shields, and gates.',
    'kora_kora_yards': 'Long war canoes take shape beneath open sheds, built for swift raids through island waters.',
    'megalith': 'Great stones mark a sacred place where the community gathers beneath the weight of ancestral memory.',
    'murex_farm': 'Shallow pens and reeking workshops turn humble sea snails into purple dye coveted by courts.',
    'oath_faithful_building': 'Those bound by sacred oath gather here to pray, judge disputes, and keep one another steadfast.',
    'oath_poor_building': 'An oath of mercy is made tangible in kitchens, dormitories, and storehouses kept for the destitute.',
    'oath_warriors_building': 'Sworn warriors share discipline, worship, and watch beneath one roof, their brotherhood sharpened for war.',
    'powder_magazine': 'Powder is ground, measured, and locked behind thick walls, guarded as carefully from flame as from thieves.',
    'public_baths': 'Warm pools and clean water give rich and poor alike a place to wash, recover, and exchange the day\'s news.',
    'saltworks': 'Sun, wind, and patient labor leave white pans of salt, preserving food and enriching coastal trade.',
    'sewers': 'Covered drains carry filth away from crowded streets, an unglamorous work on which urban health depends.',
    'slave_diplomacy': 'Coerced attendants and informants are made into instruments of courtly pressure and foreign negotiation.',
    'slave_intrigue': 'Fear and forced service feed a hidden apparatus of watchers, messengers, and whispered accusation.',
    'slave_learning': 'Knowledge is extracted through bondage, forcing scribes and tutors to serve an institution built on cruelty.',
    'slave_martial': 'Coerced labor and captive expertise sustain a military administration whose order rests upon violence.',
    'slave_stewardship': 'Ledgers, workshops, and estates are managed through compulsion, enriching the realm while brutalizing its workers.',
    'tower_of_silence': 'High stone platforms receive the dead beneath open sky, preserving a rite older than the settlement below.',
    'water_temples': 'Flowing water, carved basins, and solemn rites make this temple a place of purification and communal devotion.',
    'wantilan': 'Raised timber halls shelter households above wet ground, joining private hearths to a shared village life.',
}

TIER_MATURITY = (
    'A modest beginning serves the nearest households.',
    'Permanent crews and better fittings broaden its reach.',
    'Established routines make the work reliable in every season.',
    'Expanded grounds support a larger and more specialized community.',
    'Skilled masters now direct work of regional consequence.',
    'Generations of investment have made the institution difficult to rival.',
    'Its reputation draws talent and custom from far beyond the county.',
    'At full maturity, it stands among the foremost works of its kind.',
)

DIMENSION_PRESENTATION = {
    'sustenance': ('@county_fertility_icon!', 'Sustenance'),
    'habitation': ('@building_icon!', 'Habitation'),
    'opportunity': ('@county_icon!', 'Opportunity'),
    'health': ('@county_fertility_icon!', 'Health'),
    'security': ('@soldier_icon!', 'Security'),
    'amenities': ('@opinion_icon!', 'Amenities'),
    'space_percent': ('@building_icon!', 'Settlement Space'),
}

RETAINED_MAIN_LINE = {
    'castle': (5, 'Curtain walls, towers, courts, and storehouses grow into a seat from which the surrounding country can be defended and ruled.'),
    'city': (5, 'Homes, workshops, markets, and civic halls gather behind busy streets, making urban life both crowded and prosperous.'),
    'settlement': (3, 'The first durable streets and common works give a fragile colony the shape of a lasting community.'),
    'temple': (4, 'Shrines, cloisters, and service buildings root public worship in stone and bind the faithful into a settled community.'),
    'temple_citadel': (4, 'Sacred precincts and formidable walls unite worship, learning, and temporal authority in one commanding complex.'),
    'tribe': (2, 'Hearths, halls, and gathering grounds give scattered kin a defensible center for counsel, trade, and common life.'),
}

RETAINED_RUINS = {
    'small_ruined_holding': 'A broken minor holding lies beneath weeds and fallen masonry; every cleared chamber reveals how much work remains.',
    'medium_ruined_holding': 'Collapsed streets and roofless halls mark a substantial settlement whose recovery demands sustained labor and guarded exploration.',
    'large_ruined_holding': 'A once-great center sprawls in dangerous silence, its shattered districts too vast to reclaim in a single effort.',
}


def flavor_description(chain, level):
    short = chain['id'].removeprefix('aawc_')
    opening = CHAIN_FLAVOR.get(short, FAMILY_FLAVOR[chain['family']])
    maturity = TIER_MATURITY[min(level['tier'], len(TIER_MATURITY)) - 1]
    # Native-role identities are proposal-only Stage 6/7 design metadata.  Do
    # not describe them as live output before those systems implement them.
    return (
        f'#F {opening} {maturity}#!\n\n'
        'Its current functional effects are the structural-condition and '
        'settlement-space values shown below.'
    )


def signed_value(value, suffix=''):
    numeric = float(value)
    if numeric > 0:
        return f'#P +{value:g}{suffix}#!'
    if numeric < 0:
        return f'#N {value:g}{suffix}#!'
    return f'#high 0{suffix}#!'


def dimension_lines(conditions, space_percent, include_zero=False):
    rows = []
    for key in ('sustenance', 'habitation', 'opportunity', 'health', 'security', 'amenities'):
        value = conditions[key]
        if value or include_zero:
            icon, label = DIMENSION_PRESENTATION[key]
            rows.append(f'{icon} {signed_value(value)} {label}')
    icon, label = DIMENSION_PRESENTATION['space_percent']
    rows.append(f'{icon} {signed_value(space_percent, "%")} {label}')
    return rows


def prerequisite_lines(rows):
    result = []
    for row in rows:
        names = [f'$building_{bid}$' for bid in row['ids']]
        result.append('$EFFECT_LIST_BULLET$Requires ' + ' or '.join(names))
    return result


def retained_localization():
    loc = ['l_english:']
    for chain, (tiers, flavor) in RETAINED_MAIN_LINE.items():
        for tier in range(1, tiers + 1):
            bid = f'{chain}_{tier:02}'
            conditions = {
                'sustenance': 0,
                'habitation': (tier - 1) * 3,
                'opportunity': tier - 1,
                'health': 0,
                'security': 0,
                'amenities': 0,
            }
            effects = ['#T AAWC Structural Conditions#!', *dimension_lines(conditions, 0, include_zero=True)]
            description = f'#F {flavor} {TIER_MATURITY[tier - 1]}#!'
            for key in (f'building_{bid}_desc', f'building_type_{bid}_desc'):
                loc.append(' ' + key + ':0 ' + json.dumps(description, ensure_ascii=False))
            loc.append(' aawc_retained_' + bid + '_effects:0 ' + json.dumps('\n'.join(effects), ensure_ascii=False))
    for chain, flavor in RETAINED_RUINS.items():
        for tier in range(1, 4):
            bid = f'{chain}_{tier:02}'
            description = f'#F {flavor} Clearance stage {tier} of 3 records the remaining work.#!'
            conditions = {key: 0 for key in ('sustenance', 'habitation', 'opportunity', 'health', 'security', 'amenities')}
            effects = ['#T AAWC Structural Conditions#!',
                       *dimension_lines(conditions, 0, include_zero=True),
                       '#weak Structural conditions remain inactive while this holding is a ruin.#!']
            for key in (f'building_{bid}_desc', f'building_type_{bid}_desc'):
                loc.append(' ' + key + ':0 ' + json.dumps(description, ensure_ascii=False))
            loc.append(' aawc_retained_' + bid + '_effects:0 ' + json.dumps('\n'.join(effects), ensure_ascii=False))
    return ('\n'.join(loc) + '\n').encode('utf-8-sig')


def progression_requirements(short, tier):
    result = []
    for requirement in PREREQUISITE_PROGRESSIONS.get(short, ()):
        applicable = [source_tier for target_tier, source_tier in requirement['schedule'] if target_tier <= tier]
        require(applicable, f'{short}_{tier:02}: progression schedule has no tier-one entry')
        source_tier = applicable[-1]
        ids = tuple(f'aawc_{source}_{source_tier:02}' for source in requirement['sources'])
        text = (f'has_building_or_higher = {ids[0]}' if len(ids) == 1 else
                'OR = { ' + ' '.join(f'has_building_or_higher = {bid}' for bid in ids) + ' }')
        result.append({'ids': ids, 'source_tier': source_tier,
                       'rationale': requirement['rationale'], 'text': text})
    return result

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
    # CK3's doctrine-parameter requirement tooltip resolves this name directly.
    # AGOT supplies the parameter but omits its name in the effective English stack.
    localized('can_build_weirwood_groves_name', 'Permission to Build Weirwood Groves')
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
            progression_rows = progression_requirements(cid.removeprefix('aawc_'), l['tier'])
            if progression_rows:
                gates['can_construct'] += '\n' + '\n'.join(row['text'] for row in progression_rows)
            # AGOT removes vanilla gunpowder and does not define the recovered
            # ``unlock_powder_magazines`` parameter. Its regional Dragon Kiln
            # innovation is the effective-stack specialist firecraft license,
            # so retain restricted cultural access through that valid symbol.
            if cid == 'aawc_powder_magazine':
                unsupported = 'scope:holder.culture = { has_cultural_parameter = unlock_powder_magazines }'
                supported = 'scope:holder.culture = { has_innovation = innovation_dragon_kiln }'
                require(any(unsupported in value for value in gates.values()), f'{bid}: missing Powder Magazine cultural gate source')
                gates = {
                    key: '\n'.join(supported if line.strip() == unsupported else line for line in value.splitlines())
                    for key, value in gates.items()
                }
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
            icon = stage3_icon(cid)
            script += [f' type_icon = "{icon}"', ' show_disabled = yes']
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
            effect_lines = [
                '#T AAWC Structural Conditions#!',
                *dimension_lines(l['conditions'], l['capacity']['space_percent']),
            ]
            requirement_lines = prerequisite_lines(progression_rows)
            if requirement_lines:
                effect_lines += ['', '#T Building Prerequisites#!', *requirement_lines]
            localized(l['player']['name_key'],name)
            localized(l['player']['description_key'], flavor_description(c, l))
            localized(l['player']['effect_description_key'],'\n'.join(effect_lines))
            if l['tier']==1:
                localized('building_type_'+bid,re.sub(r'\s*\([^)]*\)','',c['player']['name']))
                localized('building_type_'+bid+'_desc',flavor_description(c, l))
            metadata.append({'id':bid,'chain':cid,'tier':l['tier'],'ai_value':ai,'native_role':l['native_role'], 'era_innovation':ERAS[era], 'gates':gates, 'prerequisite_progression':[{k:v for k,v in row.items() if k != 'text'} for row in progression_rows], 'provenance':r['provenance'], 'derivation':rule['rationale'], 'icon':icon,'model':'none: optional regular/duchy building asset; existing holding visualization retained'})
    # A holding's ``buildings`` allow-list feeds its ordinary construction
    # slots. Duchy chains are discovered by CK3 through their native
    # ``type = duchy_capital`` classification instead; registering their roots
    # here also leaks them into the ordinary building picker.
    regular_roots = sorted(
        c['levels'][0]['id'] for c in chains.values() if c['kind'] == 'regular'
    )
    artifacts = {
        BUILDINGS: ('\n'.join(script)+'\n').encode('utf-8-sig'),
        LOC: ('\n'.join(loc)+'\n').encode('utf-8-sig'),
        RETAINED_LOC: retained_localization(),
        METADATA: json_bytes({'policy':contract['policy'],'target_definitions':771,'chains':131,'construction_status':'source_activated','rendered_certification':True,'effects_policy':EFFECTS_POLICY,'levels':metadata}),
    }
    for path, holdings in HOLDING_TARGETS.items():
        artifacts[path] = register_stage3_roots(path, holdings, regular_roots)
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
