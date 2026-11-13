# AAWC Reforging 1.11 — Revised Standard and Duchy Building Catalogue (D7/D8)
**Status: authored design proposal / Codex review input, not CK3-validated definitions and not permission to silently install.**

## Directive and correction of the Stage-0 proposal
Preserve the distinct identity of existing ordinary and duchy building chains rather than collapse 105 legacy chains into 31 generalized buildings. The attached revision contains **131 chains (99 regular, 32 duchy)** and **771 proposed levels**. It preserves 105 audited legacy identities, while offering 26 new concepts (20 regular / 6 duchy). The main holding chains and special landmark/ruin/restoration/blocker chains are outside the replacement surface; adapt their future six-dimension hooks later without deleting them.

**Currency correction:** Construction consumes CK3/AAWC currencies only: primarily **gold**, often **prestige as a secondary requirement**, especially in earlier martial, administrative, prestigious or institution-building tiers, and **piety only for genuinely faith-related or sacred/funerary chains**. Never invent timber, stone, metal, tools, food or other physical material inventories/costs. Physical materials may inform *why gold costs differ*, but must not become costs.

## Deliverables and precedence
1. `AAWC_Reforging_Proposed_Building_Chains_v2.csv` — unique chain ID, heritage lineage, concept, ecological restrictions, demographic specialization, potential output, CK3 role and compatibility flags.
2. `AAWC_Reforging_Proposed_Building_Levels_v2.csv` — per-tier cumulative dimension scores and potential, workforce requirement candidates, separately authored **gold/prestige/piety** prices and build durations. Numbers are preliminary *reviewable proposals*, not certified production balance.
3. This document — design contract, review exceptions, migration instructions, testing and handoff acceptance gates.
The CSVs deliberately specify **design-level eligibility prose**, not fake CK3 script triggers. Codex must map them to real current 1.19.0.6/AGOT/Dependencies/AAWC surfaces and identify missing engine-supported geography tests. `required_era` and innovation details must be pinned to real names from the stack before final authoring.

## Required product principles
1. **Distinct ecological, cultural, functional or institutional role.** Two chains may both raise Sustenance, but a flooded paddy, hill terrace, orchard, hunting ground and coastal fishery do it in different places with different secondary effects, workforce and costs. A plain farming county must not gain forest hunting unless there is a source-backed local forest/game flag; a landlocked mountain county without viable water access must not construct a fishery.
2. **Geography uses meaningful OR/AND predicates.** Coast OR navigable river for specific ports, deposit AND suitable extraction site for named mines, faith AND cultural/regional source predicates for religious chains. Terrain alone does not imply every resource; explicitly audit named deposits and regional AGOT mechanics.
3. **Limited slots, abundant choices.** Players generally have 7–8 regular slots, sometimes ~11; many possible chains need not all be present in every county. No duplicates of the same chain. Apply mutually-exclusive replacements/role gates only where real design redundancy or land use demands it, not as a universal one-of-category prohibition.
4. **Population coherence.** Buildings change six *living-condition scores* (Sustenance, Habitation, Opportunity, Health, Security, Amenities), capacity chiefly through Sustenance/Habitation, and specialized military capacity/recruitment/support-efficiency according to their role. Avoid universal all-six bonuses and avoid double counting capacity/health effects.
5. **Output potential versus realization.** Main holding line determines baseline economic capacity. Catalogue adds *cumulative potential percentages*, not automatic realized gold/month. Eligible civilian adults, reduced by age-specific military membership and deployment, determine utilization under the later Stage-7 adapter. Workforce requirements are abstract reference quantities, never employed-person inventories. Separate curves for taxes, levy participation/reinforcement, garrisons, development and institutional prestige/piety.
6. **Heritage fidelity.** Godswood is not generic sacred precinct; orchards are not ornamental gardens; windmills are food-processing; pirate logistics are not fisheries; funerary duchy sites are not hospitals; slave institutions are not generic workshops. Distinct legacy chains keep their gameplay identities even where their main dimension overlaps.
7. **No fixed global gold/time progression.** Per-chain values and per-level increments vary by functional construction difficulty and expected payoff. The v2 CSV contains distinct preview prices and durations. Final values must be hand-balanced, not blindly accepted because they vary numerically. Tier increases must generally become costlier in absolute terms; occasional deviations need a justified transition.
8. **Source ownership.** Modify AAWC only; never bulk-edit CK3, AGOT or Dependencies source. Keep exact-ID legacy wrappers for referenced IDs, but keep them out of player/AI build menus. Recheck all 4,823 caller relationships (2,617 AAWC) from the audit with no invisible duplicate effects.
9. **Fresh campaign only.** No old-save compatibility development; still preserve upstream scripted IDs, fresh-campaign history/spawn and normal gameplay lifecycle.
10. **Colony integration deferred.** Current special blockers and restoration lines must remain functional. The later colony-blocker dimensional calibration and 250/500-population costs are a separate approved future workstream, not grounds for prematurely rewriting them during the catalogue stage.

## Dimensions and level-value semantics
Numeric `primary_score`, `secondary_score`, and `tradeoff_score` in the chain CSV describe **cumulative end-tier structural score deltas** for one building chain, before total score clamping and environmental effects. The level CSV specifies its tier-specific cumulative delta. Upgrading replaces the old tier; **never sum all lower tiers**. Positive Opportunity does not automatically create jobs; a negative Health for industrial/mining/tenements is a direct condition tradeoff, and Health does not directly add physical capacity. Separate the later native CK3 output adapter from these scores. `economic_potential_pct_cumulative` is a candidate *relative infrastructure multiplier* for the specific chain; do not add it to an independent flat building tax. No numerical fixture is a calibrated Stage-2 demographic formula.

## Cost convention and economic model
The rows have explicit integer gold/prestige/piety costs; zero means that currency is not required. Gold is the primary investment. Prestige serves as a secondary political/institutional commitment on chosen earlier stages, especially martial/civic/prestige projects; it is not a substitute for cash. Piety is confined to devotional/funerary chains where the institution genuinely represents religion. Cost values are static per authored level, not rerolled at runtime. Construction time is also authored per level. The automated draft first used domain baselines, structural price variation and monotonic checks to eliminate repeated cost tables; **Codex must review each anomalous chain**, compare source-era economy, early colony affordability, region availability, payoff and whether prestige gating is actually fun. Variability alone is not a design reason. Prestige demands must never trap low-prestige starts from constructing basic farms or housing.

### Example proposed prices (gold / prestige / piety; days)
| Chain | Level 1 | Mid-tier | Final tier | Identity |
|---|---|---|---|---|
| Cereal Fields | 95g/0pr/0pi; 270d | 395g/0pr/0pi; 825d | 690g/0pr/0pi; 1370d | cereal fields |
| Orchards | 120g/0pr/0pi; 215d | 430g/0pr/0pi; 575d | 880g/0pr/0pi; 1000d | tree fruit agriculture |
| Hunting Grounds | 90g/0pr/0pi; 245d | 405g/0pr/0pi; 680d | 795g/0pr/0pi; 1205d | managed hunting grounds |
| Paddy Fields | 110g/0pr/0pi; 255d | 475g/0pr/0pi; 740d | 855g/0pr/0pi; 1295d | paddy rice cultivation |
| Gold Mines (AGOT Heritage) | 295g/0pr/0pi; 235d | 1300g/0pr/0pi; 585d | 2100g/0pr/0pi; 985d | precious gold extraction |
| City Walls | 260g/0pr/0pi; 220d | 500g/0pr/0pi; 430d | 745g/0pr/0pi; 555d | urban walls |
| Powder Magazine | 290g/0pr/0pi; 240d | 1350g/0pr/0pi; 600d | 2395g/0pr/0pi; 1145d | powder arsenal and logistics |
| Godswood | 165g/13pr/0pi; 300d | 595g/0pr/0pi; 830d | 1095g/0pr/0pi; 1320d | godswood |
| Royal Garden | 460g/47pr/0pi; 600d | 655g/63pr/0pi; 915d | 875g/75pr/0pi; 1065d | court gardens and patronage |
| Coastal Catch And Processing | 175g/26pr/0pi; 310d | 355g/44pr/0pi; 555d | 435g/64pr/0pi; 665d | coastal fishing versus river fishing |
| Dense Urban Housing | 145g/0pr/0pi; 255d | 480g/0pr/0pi; 590d | 795g/0pr/0pi; 770d | greater housing capacity with higher health pressure |
| Royal Theatre And Cultural Academy | 425g/26pr/0pi; 705d | 620g/92pr/0pi; 880d | 995g/0pr/0pi; 1170d | arts patronage and prestige identity |

## Catalogue overview by role
| Domain | Chains | Why the distinct lines exist |
|---|---:|---|
| barrack | 4 | Barracks; Military Camps; War Camps; Civilian Levy Muster Organization |
| brew | 1 | Breweries |
| civic | 1 | Capital Bureau |
| dragon | 2 | Dragon Kiln; Powder Magazine |
| duchy culture | 8 | Scholastic Guilds; Slave Learning; Examination Hall; Leisure Palace; Royal Forest; +3 more |
| duchy econ | 10 | Glass Gardens; Lighthouse; Slave Diplomacy; Slave Intrigue; Slave Stewardship; +5 more |
| duchy faith | 4 | Burial Site; Charnel Grounds; Great Megalith; Tower Of Silence |
| duchy mil | 9 | Slave Martial; Archery Ranges; Blacksmiths; Jousting Lists; March; +4 more |
| faith | 7 | Citadel Shrine; Godswood; Megalith; Oath Faithful Building; Sacred Pool; +2 more |
| farm | 7 | Steppe Farms; Urban Farms; Farm Estates; Hospices; Plantations; +2 more |
| field | 4 | Cereal Fields; Hill Farms; Paddy Fields; Steep-Slope Terrace Agriculture |
| fish | 4 | Common Tradeport; Murex Farm; Coastal Catch And Processing; Freshwater Catches |
| forest | 2 | Ironwood; Logging Camps |
| forge | 2 | Smiths; Wind Furnace |
| garden | 2 | Market-Adjacent Public Commons; Local Monuments And Squares |
| hospice | 3 | Oath Poor Building; Public Bathhouses; Professional Infirmaries |
| housing | 5 | Longhouses; Tribe; Wantilan; Common Small Residences; Dense Urban Housing |
| hunt | 1 | Hunting Grounds |
| market | 3 | Guild Halls; Market Villages; Commercial Guild Houses |
| mill | 2 | Watermills; Windmills |
| mine | 5 | Amber Collection; Gold Mines; Iron Island Mines; Silver Mines; Salt Gathering And Preservation |
| orchard | 2 | Apiaries; Orchards |
| pasture | 2 | Hillside Grazing; Pastures |
| peat | 1 | Peat Quarries |
| pirate | 7 | Pirate Control; Pirate Economic; Pirate Fortification; Pirate Military; Pirate Supply; +2 more |
| port | 1 | River Commerce Docks |
| quarry | 1 | Quarries |
| road | 1 | Caravanserai |
| school | 4 | Monastic Schools; Scriptorium; Vihara Halls; Lay Scholarly Community |
| security | 7 | Building Moat; City Walls; Curtain Walls; Hill Forts; Idjang Forts; +2 more |
| slave | 1 | Slave Camps |
| stable | 5 | Camel Farms; Elephant Pens; Horse Pastures; Stables; Mounted Training Fields |
| training | 4 | Oath Warriors Building; Regimental Grounds; Warrior Lodges; Archer Training Grounds |
| watch | 2 | Outposts; Watchtowers |
| water | 4 | Qanats; Waterworks; Sewerage And Drainage; Agricultural Irrigation Channels |
| workshop | 3 | Workshops; Hides And Leather Craft; Shipbuilding Yards |

## Full chain catalogue (design effects shown as cumulative final-tier scores)
The following tables list every proposed chain. If a legacy role seems counterintuitive, preserve its identity but **require a source-backed semantics correction before implementation**. This document is intentionally expansive because the player has explicitly prioritized choice and ecological diversity over a numerical chain cap.

### Barrack
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_barracks` — Barracks | legacy barracks | castle/tribal or city where legal barracks permitted | Security +3, Opportunity +4, Habitation -4 | +4% potential; infantry stationed bonuses; military capacity and recruitment |
| `aawc_military_camps` — Military Camps | legacy military_camps | castle/tribal or city where legal barracks permitted | Security +3, Opportunity +4, Habitation -4 | +4% potential; infantry stationed bonuses; military capacity and recruitment |
| `aawc_war_camps` — War Camps | legacy war_camps | castle/tribal or city where legal barracks permitted | Security +3, Opportunity +4, Habitation -4 | +4% potential; infantry stationed bonuses; military capacity and recruitment |
| `aawc_mustering_fields` — Civilian Levy Muster Organization | new | castle/tribal settlement with open drill space | Security +2, Opportunity +4, Habitation -3 | +4% potential; infantry stationed bonuses; military capacity and recruitment |

### Brew
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_breweries` — Breweries | legacy breweries | grain supply or trade access; urban/village craft settlement | Opportunity +8, Amenities +4, Health -1 | +12% potential; tax potential; stress relief only where appropriate |

### Civic
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_capital_bureau` — Capital Bureau | legacy capital_bureau | administratively developed settlement | Opportunity +7, Security +5, Habitation -1 | +10% potential; control growth; development growth |

### Dragon
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_dragon_kiln` — Dragon Kiln | legacy dragon_kiln | canonical dragon kiln/dragonstone region or proven eligible lore | Opportunity +8, Security +5, Health -3 | +13% potential; siege or specific MAA bonuses (verify) |
| `aawc_powder_magazine` — Powder Magazine | legacy powder_magazine | verified powder and related innovation/license | Security +5, Opportunity +4, Health -3 | +13% potential; siege or specific MAA bonuses (verify) |

### Duchy Culture
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_scholastic_guilds` — Scholastic Guilds (AGOT Heritage) | legacy agot_scholastic_guilds | duchy capital and scholastic tradition; audit and preserve original regional/cultural/technology eligibility | Amenities +15, Opportunity +6, Habitation -1 | +9% potential; prestige; development growth |
| `aawc_slave_learning` — Slave Learning (AGOT Heritage) | legacy agot_slave_learning | duchy capital with canonical slaveholding legal and scholastic gates; audit and preserve original regional/cultural/technology eligibility | Opportunity +11, Security -5, Health -7 | +9% potential; prestige; development growth |
| `aawc_examination_hall` — Examination Hall | legacy examination_hall | duchy capital and examination bureaucracy tradition | Amenities +15, Opportunity +6, Habitation -1 | +9% potential; prestige; development growth |
| `aawc_leisure_palace` — Leisure Palace | legacy leisure_palace | duchy royal seat and luxury palace institution | Amenities +15, Opportunity +6, Habitation -1 | +9% potential; prestige; development growth |
| `aawc_royal_forest` — Royal Forest | legacy royal_forest | duchy capital with forest/game and court access | Amenities +15, Opportunity +6, Habitation -1 | +9% potential; prestige; development growth |
| `aawc_royal_garden` — Royal Garden | legacy royal_garden | duchy capital with land/water for grounds | Amenities +17, Health +2, Opportunity -1 | +9% potential; prestige; development growth |
| `aawc_duchy_grand_hospital` — Regional University Hospital | new | duchy capital with advanced healthcare | Health +19, Amenities +7, Opportunity -1 | +9% potential; prestige; development growth |
| `aawc_duchy_royal_theatre` — Royal Theatre And Cultural Academy | new | urban duchy capital with advanced amenities | Amenities +15, Opportunity +6, Habitation -1 | +9% potential; prestige; development growth |

### Duchy Econ
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_glass_gardens` — Glass Gardens (AGOT Heritage) | legacy agot_glass_gardens | duchy capital; unique AGOT glass-garden geography/lore/innovation; audit and preserve original regional/cultural/technology eligibility | Sustenance +12, Opportunity +8, Habitation -1 | +23% potential; development and economic potential |
| `aawc_lighthouse` — Lighthouse (AGOT Heritage) | legacy agot_lighthouse | duchy coastal capital/harbor; audit and preserve original regional/cultural/technology eligibility | Opportunity +15, Amenities +4, Health -2 | +23% potential; development and economic potential |
| `aawc_slave_diplomacy` — Slave Diplomacy (AGOT Heritage) | legacy agot_slave_diplomacy | duchy capital with canonical slave-trade legal regional gates; audit and preserve original regional/cultural/technology eligibility | Opportunity +11, Security -5, Health -7 | +23% potential; development and economic potential |
| `aawc_slave_intrigue` — Slave Intrigue (AGOT Heritage) | legacy agot_slave_intrigue | duchy capital with canonical slave-trade legal regional gates; audit and preserve original regional/cultural/technology eligibility | Opportunity +11, Security -5, Health -7 | +23% potential; development and economic potential |
| `aawc_slave_stewardship` — Slave Stewardship (AGOT Heritage) | legacy agot_slave_stewardship | duchy capital with slave labor legal gates; audit and preserve original regional/cultural/technology eligibility | Opportunity +11, Security -5, Health -7 | +23% potential; development and economic potential |
| `aawc_vineyard` — Vineyard (AGOT Heritage) | legacy agot_vineyard | duchy capital; grape-compatible climate/terrain; audit and preserve original regional/cultural/technology eligibility | Opportunity +15, Amenities +4, Health -2 | +23% potential; development and economic potential |
| `aawc_tax_assessor` — Tax Assessor | legacy tax_assessor | duchy capital and institutional eligibility | Opportunity +15, Amenities +4, Health -2 | +23% potential; development and economic potential |
| `aawc_duchy_grand_harbor` — Grand Harbor Authority | new | coastal duchy capital and existing functioning harbor | Opportunity +15, Amenities +4, Health -2 | +23% potential; development and economic potential |
| `aawc_duchy_civic_court` — High Court And Revenue Offices | new | duchy capital with settled administrative tier | Opportunity +15, Amenities +4, Health -2 | +23% potential; development and economic potential |
| `aawc_duchy_agricultural_estates` — Duchy Granaries And Agricultural Estates | new | duchy capital, agricultural hinterland and supply access | Opportunity +15, Amenities +4, Health -2 | +23% potential; development and economic potential |

### Duchy Faith
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_burial_site` — Burial Site | legacy burial_site | duchy-capital burial culture/religion | Amenities +12, Health +1, Opportunity -1 | +3% potential; piety; clergy learning |
| `aawc_charnel_grounds` — Charnel Grounds | legacy charnel_grounds | duchy-capital death-ritual faith region; audit and preserve original regional/cultural/technology eligibility | Amenities +12, Health +1, Opportunity -1 | +3% potential; piety; clergy learning |
| `aawc_great_megalith` — Great Megalith | legacy great_megalith | duchy capital and megalith regional faith | Amenities +15, Health +5, Opportunity -1 | +3% potential; piety; clergy learning |
| `aawc_tower_of_silence` — Tower Of Silence | legacy tower_of_silence | duchy-capital Tower of Silence faith/culture; audit and preserve original regional/cultural/technology eligibility | Amenities +12, Health +1, Opportunity -1 | +3% potential; piety; clergy learning |

### Duchy Mil
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_slave_martial` — Slave Martial (AGOT Heritage) | legacy agot_slave_martial | duchy capital with slave military law/tradition; audit and preserve original regional/cultural/technology eligibility | Opportunity +11, Security -5, Health -7 | +6% potential; duchy/stationed military bonuses |
| `aawc_archery_ranges` — Archery Ranges | legacy archery_ranges | duchy capital with archery school tradition | Security +11, Opportunity +7, Habitation -3 | +6% potential; duchy/stationed military bonuses |
| `aawc_blacksmiths` — Blacksmiths | legacy blacksmiths | duchy capital with smithing industry | Security +11, Opportunity +7, Habitation -3 | +6% potential; duchy/stationed military bonuses |
| `aawc_jousting_lists` — Jousting Lists | legacy jousting_lists | duchy capital with knightly culture | Security +11, Opportunity +7, Habitation -3 | +6% potential; duchy/stationed military bonuses |
| `aawc_march` — March | legacy march | frontier duchy capital | Security +11, Opportunity +7, Habitation -3 | +6% potential; duchy/stationed military bonuses |
| `aawc_military_academy` — Military Academy | legacy military_academy | duchy capital with military institutional innovation | Security +11, Opportunity +7, Habitation -3 | +6% potential; duchy/stationed military bonuses |
| `aawc_royal_armory` — Royal Armory | legacy royal_armory | duchy capital with professional arms industry | Security +11, Opportunity +7, Habitation -3 | +6% potential; duchy/stationed military bonuses |
| `aawc_siege_works` — Siege Works | legacy siege_works | duchy capital with siege innovation | Security +11, Opportunity +7, Habitation -3 | +6% potential; duchy/stationed military bonuses |
| `aawc_duchy_military_college` — Professional Military College | new | duchy capital with professional military institutional access | Security +11, Opportunity +7, Habitation -3 | +6% potential; duchy/stationed military bonuses |

### Faith
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_citadel_shrine` — Citadel Shrine | legacy citadel_shrine | citadel/temple eligible faith; preserve exact faith/culture and holy-site eligibility from effective original | Amenities +9, Health +3, Opportunity -1 | +3% potential; piety; clergy/learning where applicable |
| `aawc_godswood` — Godswood | legacy godswood | Old Gods compatible region and sacred grove; preserve exact faith/culture and holy-site eligibility from effective original | Amenities +9, Health +3, Opportunity -1 | +3% potential; piety; clergy/learning where applicable |
| `aawc_megalith` — Megalith | legacy megalith | faith-gated or religion-compatible site; canonical source semantics retained | Amenities +9, Health +3, Opportunity -1 | +3% potential; piety; clergy/learning where applicable |
| `aawc_oath_faithful_building` — Oath Faithful Building | legacy oath_faithful_building | specific oath/faith regional tradition; preserve exact faith/culture and holy-site eligibility from effective original | Amenities +9, Health +3, Opportunity -1 | +3% potential; piety; clergy/learning where applicable |
| `aawc_sacred_pool` — Sacred Pool | legacy sacred_pool | faith-gated or religion-compatible site; canonical source semantics retained | Amenities +9, Health +3, Opportunity -1 | +3% potential; piety; clergy/learning where applicable |
| `aawc_temple_citadel` — Temple Citadel | legacy temple_citadel | faith-gated or religion-compatible site; canonical source semantics retained; preserve exact faith/culture and holy-site eligibility from effective original | Amenities +9, Health +3, Opportunity -1 | +3% potential; piety; clergy/learning where applicable |
| `aawc_water_temples` — Water Temples | legacy water_temples | faith-specific sacred water setting; preserve exact faith/culture and holy-site eligibility from effective original | Amenities +9, Health +3, Opportunity -1 | +3% potential; piety; clergy/learning where applicable |

### Farm
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_steppe_farms` — Steppe Farms (AGOT Heritage) | legacy agot_steppe_farms | steppe/arid grassland with cereal/pastoral suitability; audit and preserve original regional/cultural/technology eligibility | Sustenance +11, Opportunity +5, Habitation -1 | +17% potential; supply limit |
| `aawc_urban_farms` — Urban Farms (AGOT Heritage) | legacy agot_urban_farms | urban castle/city with agricultural plots and suitable climate; audit and preserve original regional/cultural/technology eligibility | Sustenance +7, Habitation +2, Health -1 | +17% potential; supply limit |
| `aawc_farm_estates` — Farm Estates | legacy farm_estates | arable farm country | Sustenance +11, Opportunity +5, Habitation -1 | +17% potential; supply limit |
| `aawc_hospices` — Hospices | legacy hospices | arable terrain and adequate moisture; specialized regional cultivation | Sustenance +11, Opportunity +5, Habitation -1 | +17% potential; supply limit |
| `aawc_plantations` — Plantations | legacy plantations | appropriate warm climate/soil and legal region | Sustenance +11, Opportunity +5, Habitation -1 | +17% potential; supply limit |
| `aawc_spice_plantation` — Spice Plantation | legacy spice_plantation | warm growing season/soil/water; audit and preserve original regional/cultural/technology eligibility | Sustenance +11, Opportunity +5, Habitation -1 | +17% potential; supply limit |
| `aawc_stilted_granaries` — Stilted Granaries | legacy stilted_granaries | arable terrain and adequate moisture; specialized regional cultivation | Sustenance +11, Opportunity +5, Habitation -1 | +17% potential; supply limit |

### Field
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_cereal_fields` — Cereal Fields | legacy cereal_fields | plains/farmland/floodplain | Sustenance +12, Opportunity +4, Habitation -2 | +15% potential; supply limit; development growth |
| `aawc_hill_farms` — Hill Farms | legacy hill_farms | hills with terracing and farming support | Sustenance +12, Opportunity +4, Habitation -2 | +15% potential; supply limit; development growth |
| `aawc_paddy_fields` — Paddy Fields | legacy paddy_fields | flooded/wet fertile fields with irrigation | Sustenance +12, Opportunity +4, Habitation -2 | +15% potential; supply limit; development growth |
| `aawc_terraced_farms` — Steep-Slope Terrace Agriculture | new | hill or mountain slopes where water/soil support farming | Sustenance +8, Opportunity +5, Habitation -2 | +15% potential; supply limit; development growth |

### Fish
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_common_tradeport` — Common Tradeport | legacy common_tradeport | valid coast OR significant freshwater access supported by geography | Sustenance +11, Opportunity +5, Health -1 | +15% potential; supply limit; coastal trade support |
| `aawc_murex_farm` — Murex Farm | legacy murex_farm | coastal murex habitat/region | Sustenance +11, Opportunity +5, Health -1 | +15% potential; supply limit; coastal trade support |
| `aawc_coastal_fisheries` — Coastal Catch And Processing | new | sea coast with fishing access | Sustenance +11, Opportunity +5, Health -1 | +15% potential; supply limit; coastal trade support |
| `aawc_river_fisheries` — Freshwater Catches | new | major river/lake with fishing access | Sustenance +11, Opportunity +5, Health -1 | +15% potential; supply limit; coastal trade support |

### Forest
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_ironwood` — Ironwood (AGOT Heritage) | legacy agot_ironwood | northern ironwood ecology/region and woodlands; audit and preserve original regional/cultural/technology eligibility | Opportunity +9, Sustenance +2, Health -2 | +12% potential; construction speed; supply limit |
| `aawc_logging_camps` — Logging Camps | legacy logging_camps | forest/taiga woodland; ironwood only in its canonical regional ecological range | Opportunity +9, Sustenance +2, Health -2 | +12% potential; construction speed; supply limit |

### Forge
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_smiths` — Smiths | legacy smiths | settled crafts or suitable ore/trade access | Opportunity +10, Security +2, Health -3 | +17% potential; stationed MAA equipment benefit if relevant |
| `aawc_wind_furnace` — Wind Furnace | legacy wind_furnace | settled crafts or suitable ore/trade access | Opportunity +10, Security +2, Health -3 | +17% potential; stationed MAA equipment benefit if relevant |

### Garden
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_public_squares` — Market-Adjacent Public Commons | new | populated city/castle; no environmental constraint beyond settlement | Amenities +13, Health +2, Opportunity -1 | +2% potential; prestige where institutional; stress modifier where scoped |
| `aawc_monument_works` — Local Monuments And Squares | new | developed city, castle or temple | Amenities +13, Health +2, Opportunity -1 | +2% potential; prestige where institutional; stress modifier where scoped |

### Hospice
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_oath_poor_building` — Oath Poor Building | legacy oath_poor_building | oathbound faith and charitable doctrine; preserve exact faith/culture and holy-site eligibility from effective original | Health +14, Amenities +3, Opportunity -1 | +2% potential; plague resistance |
| `aawc_public_baths` — Public Bathhouses | new | town or temperate/thermal water access with waterworks | Health +10, Amenities +7, Sustenance -1 | +2% potential; plague resistance |
| `aawc_infirmaries` — Professional Infirmaries | new | castle/city/temple with development | Health +14, Amenities +3, Opportunity -1 | +2% potential; plague resistance |

### Housing
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_longhouses` — Longhouses | legacy longhouses | northern/tribal architecture region | Habitation +15, Health +2, Sustenance -1 | +6% potential; development growth or reduced construction cost |
| `aawc_tribe` — Tribe | legacy tribe | habitable settled holding; cultural/architectural subtype | Habitation +15, Health +2, Sustenance -1 | +6% potential; development growth or reduced construction cost |
| `aawc_wantilan` — Wantilan | legacy wantilan | habitable settled holding; cultural/architectural subtype; audit and preserve original regional/cultural/technology eligibility | Habitation +15, Health +2, Sustenance -1 | +6% potential; development growth or reduced construction cost |
| `aawc_village_cottages` — Common Small Residences | new | rural village, castle or temple with habitation | Habitation +15, Health +2, Sustenance -1 | +6% potential; development growth or reduced construction cost |
| `aawc_urban_tenements` — Dense Urban Housing | new | city or suitably upgraded urban castle | Habitation +18, Opportunity +3, Health -4 | +6% potential; development growth or reduced construction cost |

### Hunt
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_hunting_grounds` — Hunting Grounds | legacy hunting_grounds | wildlife-bearing forest/taiga/hills or verified game region | Sustenance +8, Amenities +4, Security -1 | +7% potential; supply limit; defender terrain advantage if verified |

### Market
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_guild_halls` — Guild Halls | legacy guild_halls | settlement with trade-route/urban access; modest market village variants permitted | Opportunity +11, Amenities +4, Security -1 | +20% potential; development growth and tax potential |
| `aawc_market_villages` — Market Villages | legacy market_villages | settlement with trade-route/urban access; modest market village variants permitted | Opportunity +11, Amenities +4, Security -1 | +20% potential; development growth and tax potential |
| `aawc_trade_guilds` — Commercial Guild Houses | new | city or developed trade hub | Opportunity +11, Amenities +4, Security -1 | +20% potential; development growth and tax potential |

### Mill
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_watermills` — Watermills | legacy watermills | flowing water river/stream | Opportunity +8, Sustenance +5, Health -1 | +12% potential; development growth; supply limit |
| `aawc_windmills` — Windmills | legacy windmills | wind-exposed plains/coast/hills and verified innovation | Opportunity +8, Sustenance +5, Health -1 | +12% potential; development growth; supply limit |

### Mine
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_amber_collection` — Amber Collection (AGOT Heritage) | legacy agot_amber_collection | amber-bearing coastal/forest deposit or explicit AGOT region; audit and preserve original regional/cultural/technology eligibility | Opportunity +13, Sustenance -1, Health -6 | +23% potential; construction productivity or tax potential |
| `aawc_gold_mines` — Gold Mines (AGOT Heritage) | legacy agot_gold_mines | gold deposit only; mining ecology verified; audit and preserve original regional/cultural/technology eligibility | Opportunity +13, Sustenance -1, Health -6 | +23% potential; construction productivity or tax potential |
| `aawc_iron_island_mines` — Iron Island Mines (AGOT Heritage) | legacy agot_iron_island_mines | Iron Islands mine deposits and lore region; audit and preserve original regional/cultural/technology eligibility | Opportunity +13, Sustenance -1, Health -6 | +23% potential; construction productivity or tax potential |
| `aawc_silver_mines` — Silver Mines (AGOT Heritage) | legacy agot_silver_mines | silver deposit only; audit and preserve original regional/cultural/technology eligibility | Opportunity +13, Sustenance -1, Health -6 | +23% potential; construction productivity or tax potential |
| `aawc_saltworks` — Salt Gathering And Preservation | new | coastal evaporation climate or confirmed salt deposits | Opportunity +9, Sustenance +4, Health -2 | +23% potential; construction productivity or tax potential |

### Orchard
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_apiaries` — Apiaries | legacy apiaries | flowering/meadow/forest edges | Sustenance +5, Opportunity +4, Amenities +2 | +12% potential; development growth |
| `aawc_orchards` — Orchards | legacy orchards | temperate/appropriate watered fertile land | Sustenance +10, Amenities +4, Habitation -1 | +12% potential; development growth |

### Pasture
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_hillside_grazing` — Hillside Grazing | legacy hillside_grazing | grassland/plains/steppe/hills with grazing potential | Sustenance +8, Opportunity +5, Health -1 | +13% potential; supply limit; cavalry logistics when relevant |
| `aawc_pastures` — Pastures | legacy pastures | grassland/plains/steppe/hills with grazing potential | Sustenance +8, Opportunity +5, Health -1 | +13% potential; supply limit; cavalry logistics when relevant |

### Peat
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_peat_quarries` — Peat Quarries | legacy peat_quarries | wetland or peat deposit | Opportunity +7, Sustenance -1, Health -3 | +8% potential; construction or winter supply abstract |

### Pirate
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_pirate_control` — Pirate Control (AGOT Heritage) | legacy agot_pirate_control | pirate governance region; audit and preserve original regional/cultural/technology eligibility | Opportunity +8, Security +3, Health -2 | +13% potential; raid/maritime/fort bonuses by subtype |
| `aawc_pirate_economic` — Pirate Economic (AGOT Heritage) | legacy agot_pirate_economic | pirate coast/anchorage; audit and preserve original regional/cultural/technology eligibility | Opportunity +8, Security +3, Health -2 | +13% potential; raid/maritime/fort bonuses by subtype |
| `aawc_pirate_fortification` — Pirate Fortification (AGOT Heritage) | legacy agot_pirate_fortification | defensible raider coast; audit and preserve original regional/cultural/technology eligibility | Opportunity +8, Security +3, Health -2 | +13% potential; raid/maritime/fort bonuses by subtype |
| `aawc_pirate_military` — Pirate Military (AGOT Heritage) | legacy agot_pirate_military | pirate camp with raiding; audit and preserve original regional/cultural/technology eligibility | Opportunity +8, Security +3, Health -2 | +13% potential; raid/maritime/fort bonuses by subtype |
| `aawc_pirate_supply` — Pirate Supply (AGOT Heritage) | legacy agot_pirate_supply | coastal piracy access, suitable port/anchorage; audit and preserve original regional/cultural/technology eligibility | Opportunity +6, Sustenance +6, Security -1 | +13% potential; raid/maritime/fort bonuses by subtype |
| `aawc_pirate_troop` — Pirate Troop (AGOT Heritage) | legacy agot_pirate_troop | shipbuilding or landing access; audit and preserve original regional/cultural/technology eligibility | Opportunity +8, Security +3, Health -2 | +13% potential; raid/maritime/fort bonuses by subtype |
| `aawc_kora_kora_yards` — Kora Kora Yards | legacy kora_kora_yards | canonical sea-raider coast and local warcraft; audit and preserve original regional/cultural/technology eligibility | Opportunity +8, Security +3, Health -2 | +13% potential; raid/maritime/fort bonuses by subtype |

### Port
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_river_docks` — River Commerce Docks | new | navigable river with suitable bank; no open coast requirement | Opportunity +13, Amenities +3, Health -2 | +24% potential; naval embarking or supply where supported |

### Quarry
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_quarries` — Quarries | legacy quarries | quarryable hills/mountains/stone deposit | Opportunity +10, Security +2, Health -3 | +15% potential; construction speed or cost modifier where supported |

### Road
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_caravanserai` — Caravanserai | legacy caravanserai | trade-path or suitable land transit; caravan routes favor arid trade corridors | Opportunity +9, Security +3, Habitation -1 | +12% potential; movement speed; supply limit; development growth |

### School
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_monastic_schools` — Monastic Schools | legacy monastic_schools | settlement/temple/city with education institution access | Amenities +8, Opportunity +6, Habitation -1 | +9% potential; learning; development growth |
| `aawc_scriptorium` — Scriptorium | legacy scriptorium | settlement/temple/city with education institution access | Amenities +8, Opportunity +6, Habitation -1 | +9% potential; learning; development growth |
| `aawc_vihara_halls` — Vihara Halls | legacy vihara_halls | Buddhist-faith equivalent canonical source eligibility; preserve exact faith/culture and holy-site eligibility from effective original | Amenities +8, Opportunity +6, Habitation -1 | +9% potential; learning; development growth |
| `aawc_scholars_quarters` — Lay Scholarly Community | new | urban/temple/castle with institutional training | Amenities +8, Opportunity +6, Habitation -1 | +9% potential; learning; development growth |

### Security
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_building_moat` — Building Moat | legacy building_moat | castle defensive site with moat engineering/water or terrain viable | Security +15, Opportunity +1, Habitation -3 | +1% potential; fort level; defender advantage; garrison potential |
| `aawc_city_walls` — City Walls | legacy city_walls | city defensive legal site | Security +15, Opportunity +1, Habitation -3 | +1% potential; fort level; defender advantage; garrison potential |
| `aawc_curtain_walls` — Curtain Walls | legacy curtain_walls | castle defensive site | Security +15, Opportunity +1, Habitation -3 | +1% potential; fort level; defender advantage; garrison potential |
| `aawc_hill_forts` — Hill Forts | legacy hill_forts | hills/highlands suitable for hill fort | Security +15, Opportunity +1, Habitation -3 | +1% potential; fort level; defender advantage; garrison potential |
| `aawc_idjang_forts` — Idjang Forts | legacy idjang_forts | regional idjang construction and site; audit and preserve original regional/cultural/technology eligibility | Security +15, Opportunity +1, Habitation -3 | +1% potential; fort level; defender advantage; garrison potential |
| `aawc_palisades` — Palisades | legacy palisades | tribal/woodland fortification material and site | Security +15, Opportunity +1, Habitation -3 | +1% potential; fort level; defender advantage; garrison potential |
| `aawc_ramparts` — Ramparts | legacy ramparts | suitable castle/earthwork site | Security +15, Opportunity +1, Habitation -3 | +1% potential; fort level; defender advantage; garrison potential |

### Slave
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_slave_camps` — Slave Camps (AGOT Heritage) | legacy agot_slave_camps | slaveholding legality, culture and regional license; audit and preserve original regional/cultural/technology eligibility | Opportunity +11, Security -5, Health -7 | +20% potential; economic potential with unrest/control downsides |

### Stable
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_camel_farms` — Camel Farms | legacy camel_farms | arid desert/steppe with camel tradition; audit and preserve original regional/cultural/technology eligibility | Opportunity +6, Security +2, Habitation -3 | +5% potential; cavalry station bonuses; mounted support efficiency |
| `aawc_elephant_pens` — Elephant Pens | legacy elephant_pens | elephant ecology and cultural access; audit and preserve original regional/cultural/technology eligibility | Opportunity +6, Security +2, Habitation -3 | +5% potential; cavalry station bonuses; mounted support efficiency |
| `aawc_horse_pastures` — Horse Pastures | legacy horse_pastures | grassland/steppe/pastoral regions | Opportunity +6, Security +2, Habitation -3 | +5% potential; cavalry station bonuses; mounted support efficiency |
| `aawc_stables` — Stables | legacy stables | grazing or supply corridors; specialized mounts require ecology/culture | Opportunity +6, Security +2, Habitation -3 | +5% potential; cavalry station bonuses; mounted support efficiency |
| `aawc_cavalry_courses` — Mounted Training Fields | new | horse/camel/elephant access and military castle or tribal center | Opportunity +6, Security +2, Habitation -3 | +5% potential; cavalry station bonuses; mounted support efficiency |

### Training
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_oath_warriors_building` — Oath Warriors Building | legacy oath_warriors_building | oathbound martial faith tradition; preserve exact faith/culture and holy-site eligibility from effective original | Opportunity +5, Security +3, Habitation -2 | +3% potential; military recruitment speed; selected stationed bonuses |
| `aawc_regimental_grounds` — Regimental Grounds | legacy regimental_grounds | castle/tribal or approved training settlement | Opportunity +5, Security +3, Habitation -2 | +3% potential; military recruitment speed; selected stationed bonuses |
| `aawc_warrior_lodges` — Warrior Lodges | legacy warrior_lodges | martial tribal culture/tradition | Opportunity +5, Security +3, Habitation -2 | +3% potential; military recruitment speed; selected stationed bonuses |
| `aawc_archery_yards` — Archer Training Grounds | new | castle/city/tribal with archery tradition or innovation | Opportunity +5, Security +3, Habitation -2 | +3% potential; military recruitment speed; selected stationed bonuses |

### Watch
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_outposts` — Outposts | legacy outposts | border/frontier/road security coverage | Security +11, Opportunity +2, Habitation -1 | +2% potential; hostile raid resistance; defender advantage |
| `aawc_watchtowers` — Watchtowers | legacy watchtowers | visibility suitable watch site | Security +11, Opportunity +2, Habitation -1 | +2% potential; hostile raid resistance; defender advantage |

### Water
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_qanats` — Qanats | legacy qanats | drylands/desert with viable groundwater and engineering innovation | Health +10, Sustenance +7, Opportunity -1 | +4% potential; plague resistance; supply limit |
| `aawc_waterworks` — Waterworks | legacy waterworks | water access or irrigation viability; qanat only arid groundwater geography | Health +10, Sustenance +7, Opportunity -1 | +4% potential; plague resistance; supply limit |
| `aawc_sewers` — Sewerage And Drainage | new | urban settlement at sufficient tier; water disposal feasible | Health +17, Habitation +3, Opportunity -1 | +4% potential; plague resistance; supply limit |
| `aawc_irrigation_estates` — Agricultural Irrigation Channels | new | drylands/arid cultivated terrain and available water source | Health +10, Sustenance +7, Opportunity -1 | +4% potential; plague resistance; supply limit |

### Workshop
| Chain | Origin | Geography / eligibility | Structural demographic effects | Output/native role |
|---|---|---|---|---|
| `aawc_workshops` — Workshops | legacy workshops | settled castle/city/tribal or craft-capable holding | Opportunity +12, Amenities +1, Health -3 | +23% potential; development growth; economic potential |
| `aawc_leatherworkers` — Hides And Leather Craft | new | livestock/hunting supply region or trade access | Opportunity +12, Amenities +1, Health -3 | +23% potential; development growth; economic potential |
| `aawc_shipwrights` — Shipbuilding Yards | new | coast or navigable river with shipyard reach | Opportunity +12, Amenities +1, Health -3 | +23% potential; development growth; economic potential |

## Exceptional cases: verify against actual source mechanics before authorizing
| Identity group | Required investigation |
|---|---|
| Slave labor and administration | Preserve laws/culture/history/slavery semantics and appropriate control/Health tradeoffs. Do not erase coercion into generic free-industry productivity. |
| Pirate chains and kora-kora | Keep piracy logistics, recruitment, raiding, covert trade, shipyards and fortification distinct; validate sea access and regional rules. |
| Burial/charnel/Tower of Silence, Godswood, oath, temples | Preserve actual faith and tradition triggers, rituals and positive piety roles; avoid generic hospice substitution. |
| Dragon kiln / powder magazine | Verify AGOT/LoV innovation and equipment identity. Do not assume powder and dragons are universally accessible. |
| Ironwood, amber, named precious mines, glass gardens | Confirm resource deposit/region uniqueness and prohibit generic biome unlocking. |
| Cultural originals: wantilan, idjang, vihara, elephant, camel | Preserve architectural/faith/geographical requirements, not modern extrapolation. |
| Existing dukes and special sites | Ordinary duchy replacements must not become special-landmark replacements; retain main and special chains. |

## Codex implementation request: actionable sequence
1. **Produce an explicit lineage signoff report** for all 105 heritage chains showing original source path/triggers, legacy role, v2 candidate, reason to preserve, and whether every claimed physical gate is scriptable. For any doubtful gate, report `UNVERIFIED`, do not fake it.
2. **Review ecology data**: enumerate all CK3+AGOT terrains and effective province flags; construct a terrain/river/coast/deposit/region/faith matrix showing allowed, forbidden and blocked-no-data conditions for each of the 131 chains. Test dry plains (no forest hunting), landlocked mountains (no fishery), actual mountain coast/river (valid fishery if supported), forests, wetlands, drylands, deserts, islands, urban city, tribal, temple, castle and duchy capitals.
3. **Review chain uniqueness**: justify every chain against its closest neighbor. If two end up technically identical across restrictions, scoring, economic role, military effects and cost/AI, revise a meaningful distinction or flag for human merger review; do not add cosmetic-only duplicates.
4. **Bind currencies**: validate CK3/AGOT building construction support for simultaneous gold + prestige and (religious only) piety payments at correct holder scope. If unsupported for ordinary buildings, present a robust scripted-interaction/event construction route for review, including AI and cancellation refunds; never pretend a CSV column automatically changes native build pricing.
5. **Balance per-level and per-chain**: compare gold, prestige and piety versus era income, impact, geography rarity, expected workforce, 7–8 available slots, and investment scenarios. Adjust each sequence deliberately; all hardcoded gold/time templates are rejected. Describe costs in tooltips and confirm actual deduction/cancel behavior. No raw materials inventory.
6. **Verify per-building output contracts**: six-dimensional effects, positive/negative tradeoffs, workforce requirement, native CK3 effects, military capacity/training/support-efficiency, and whether each is structural, potential, or utilization-dependent. Do not activate the Stage-6 military or Stage-7 economy adapter prematurely.
7. **Create 100% source-compatible replacements in AAWC**: preserve main lines/special/restoration/blockers; build only reviewed standard/duchy chains; exact-ID wrapper plan for referenced legacy IDs; no exact-ID caller dropped; no double counting; upgrades replace current tier; no duplicate stacking.
8. **Author AI strategy** using legal terrain and settlement deficiencies, strategy needs, potential utilization, affordable resource balances, future tier costs and migration demographic role. AI must not lock itself into prestige costs or spam nonviable chains.
9. **Testing**: static uniqueness/cost/piety checks; content parser/startup; cross-region construction menus; upgrade links/cancel; player/AI payment and refund; holder change; fresh-save/reload; AGOT special/ruin chain regressions; normal/Valyria tooltips and icons; long-horizon 50/100/150-year five-path simulations using true Stage-2 formulas once ready; world-scale cadence and dirty-cache performance; zero suspicious script errors.
10. **Return a human-review package**: coverage tables, exact diff, flagged semantic issues, legal-build menus by region, income/payback comparison, dimension heatmaps and cohort consequences, military balance notes, complete test evidence and unresolved engine gates. Do not claim CK3 runtime proof from CSV or Python proxy data.

## Acceptance gates
**D7/D8 design acceptance** requires (a) all 105 legacy identities explicitly justified and mapped, (b) exactly supported, sensible physical/region/faith predicates, (c) distinct use cases, (d) variable and economically grounded currency/time ladders, (e) complete per-level effects with cumulative semantics, (f) correct potential/utilization separation, and (g) confirmation that main/special/ruin/blocker systems are untouched until their scheduled phase. **Implementation activation** additionally requires actual CK3 source and runtime validation of prices, construction, AI, buildings, compatibility wrapper effects, GUI mirrors and fresh-campaign startup. These are separate approvals.

**Decision state:** This is a proposed replacement for the former 31-chain catalogue and should be returned to VSCodex for source-audited correction and human review before Stage 3 is activated. D9 no-fallback rule remains binding; D6 colonial blocker balance remains deferred.