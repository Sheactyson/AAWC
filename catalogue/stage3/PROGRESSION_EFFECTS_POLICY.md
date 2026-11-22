# Stage 3 prerequisite progression and effects policy — 1.11.4.11

This entry is the review authority for the post-Stage-4 prerequisite and effects pass. It records the positive AAWC dependency graph and separates effects that work now from outputs deliberately deferred to the population-scaled economy and military lifecycle. It does not certify rendered CK3 behavior.

## Positive prerequisite graph

The compiler applies 53 positive prerequisite requirements to 52 specialized chains. A schedule is written as `target tier → required source tier`. The selected requirement is cumulative until the next threshold. Sources separated by `/` are alternative routes inside one `OR`; separate rows joined with `+` are both required. Inherited CK3/AGOT exclusions inside `NOT`, `NOR`, or `NAND` remain exclusions and are not misclassified as positive graph edges.

The regular schedules are:

- `1→1, 3→2, 5→3, 7→4` for an eight-tier foundation.
- `1→1, 3→2, 5→3` for a six-tier specialization.
- Chain-specific shorter schedules where the source or target has fewer levels.

The duchy default is `1→3, 2→5, 3→7`. Every duchy requirement points to a regular chain, so no chain requires a second building in the one duchy slot.

| Specialized chain | Required foundation(s) | Schedule |
| --- | --- | --- |
| Archer Training Grounds | Barracks | regular 8 |
| Mounted Training Fields | Barracks, plus the retained eligible-mount route | regular 8 |
| Civilian Levy Muster Organization | Barracks | regular 6 |
| Regimental Grounds | Barracks | regular 8 |
| Warrior Lodges | Barracks | regular 8 |
| Breweries | Cereal Fields | regular 8 |
| Farm Estates | Cereal Fields | regular 8 |
| Plantations | Farm Estates | regular 8 |
| Spice Plantation | Plantations | regular 8 |
| Urban Farms | Waterworks | regular 8 |
| Murex Farm | Coastal Catch and Processing | regular 8; source levels 1–4 |
| Wind Furnace | Smiths | regular 8 |
| Powder Magazine | Smiths | `1→2, 3→3, 5→4, 7→5` |
| Hides and Leather Craft | Workshops, plus the retained hide-supply route | regular 6 |
| Shipbuilding Yards | Workshops | `1→1, 3→2` |
| Guild Halls | Workshops | regular 8 |
| Caravanserai | Workshops | regular 8 |
| River Commerce Docks | Workshops | regular 6 |
| Local Monuments and Squares | Workshops | regular 6 |
| Dense Urban Housing | Public Squares | regular 6 |
| Sewerage and Drainage | Waterworks | regular 6 |
| Agricultural Irrigation Channels | Waterworks / Qanats | `1→1, 3→2, 5→3, 7→4` |
| Public Bathhouses | Waterworks / Qanats | regular 6 |
| Lay Scholarly Community | Monastic Schools / Scriptorium | regular 6 |
| Duchy Granaries and Agricultural Estates | Cereal Fields / Farm Estates | duchy default |
| High Court and Revenue Offices | Capital Bureau | duchy default |
| Grand Harbor Authority | Common Tradeport | duchy default |
| Regional University Hospital | Professional Infirmaries | `1→3, 2→4, 3→6` |
| Professional Military College | Barracks | duchy default |
| Royal Theatre and Cultural Academy | Public Squares | `1→3, 2→4, 3→5` |
| Archery Ranges | Archer Training Grounds | duchy default |
| Blacksmiths | Smiths | duchy default |
| Jousting Lists | Mounted Training Fields | `1→2, 2→4, 3→6` |
| Military Academy | Regimental Grounds | duchy default |
| Royal Armory | Smiths | `1→4, 2→6, 3→8` |
| Siege Works | Quarries + Smiths | duchy default for each |
| March | Ramparts | duchy default |
| Scholastic Guilds | Lay Scholarly Community | `1→2, 2→4, 3→6` |
| Examination Hall | Capital Bureau | duchy default |
| Tax Assessor | Capital Bureau | duchy default |
| Lighthouse | Common Tradeport | duchy default |
| Royal Garden | Public Squares | `1→3, 2→4, 3→5` |
| Leisure Palace | Public Squares | `1→3, 2→4, 3→5` |
| Royal Forest | Hunting Grounds | duchy default |
| Dragon Kiln | Smiths | duchy default |
| Glass Gardens | Waterworks | duchy default |
| Great Megalith | Megalith | `1→3, 2→6` |
| Slave Diplomacy | Slave Camps | duchy default |
| Slave Intrigue | Slave Camps | duchy default |
| Slave Learning | Slave Camps | duchy default |
| Slave Martial | Slave Camps | duchy default |
| Slave Stewardship | Slave Camps | duchy default |

All target and source IDs resolve to the generated 771-level catalogue. Schedules begin at target tier one, rise monotonically, do not exceed either chain, and never regress on upgrade. The positive graph is acyclic. Every terminal foundation is a regular chain registered in ordinary settled-holding construction surfaces. A chain omitted from this table remains foundational, resource/site-defined, identity-gated, or already has a sufficient inherited prerequisite; omission is not an implicit unrestricted-output grant. Commercial Guild Houses intentionally retain their existing `city OR (development 10 + Market Villages)` route: forcing Market Villages onto the city branch would be unreachable because that source chain is tribal/pirate-only.

## Effects inventory and authority

| Inventory key | Status | Precise policy |
| --- | --- | --- |
| `structural_conditions` | `implemented` | The six cumulative dimensions—Sustenance, Habitation, Opportunity, Health, Security, and Amenities—are functional holding inputs through the Stage 2 contribution adapter. Their compact building text describes that live structural input. |
| `settlement_space` | `implemented` | The authored space percentage is a functional holding-capacity input through the Stage 2 settlement-space adapter. It is distinct from the obsolete fixed “Building Capacity” display. |
| `construction_unlocks` | `implemented` | Holding, terrain, culture/innovation, faith/doctrine, title, government, resource, and prerequisite predicates are real Stage 3 construction gates. |
| `custom_holding_modifiers` | `deferred_population_scaling` | New “This Holding” tax, income, levy, garrison, supply, development, control, and analogous native modifiers are not emitted. Their magnitude must come from the Stage 7 population/output model, not fixed per-building placeholders. |
| `custom_county_modifiers` | `deferred_population_scaling` | New “This County” economic, control, development, opinion, supply, and analogous outputs are not emitted until the Stage 7 scaling contract defines their semantics. |
| `custom_holder_modifiers` | `deferred_population_scaling` | New holder/owner skill, opinion, prestige, piety, lifestyle, and similar outputs are not emitted until Stage 7 defines population-scaled or institution-scaled semantics. |
| `custom_military_modifiers` | `deferred_military_lifecycle` | MAA, knight, regiment, siege, reinforcement, levy, army, and stationing modifiers remain Stage 6 work. Building names and native-role proposals do not make those effects functional. |
| `neutral_effect_desc_bridge` | `implemented_non_gameplay` | Each custom definition retains exactly `county_modifier = { development_growth_factor = 0 }` only because CK3 otherwise hides `effect_desc`. It has no numeric gameplay output and is never described as one. |
| `retained_main_line_native_modifiers` | `implemented_preserved` | Castle, city, settlement, temple, temple-citadel, and tribe main-line definitions keep their effective CK3/AGOT modifier blocks. Those retained upstream semantics remain functional until a separately authorized main-line scaling replacement exists. |
| `retained_old_growth_capacity_effect_desc` | `removed` | The 23 retained main-line levels no longer reference AAWC’s obsolete Growth Rating, fixed Building Capacity, or Migration Rating effect descriptions. The underlying Stage 2 population/conditions system remains authoritative. Ruin lifecycle roots had no matching obsolete overlay entries to remove. |

No native-role proposal is represented as functional. The generated runtime metadata embeds this inventory beside every level, and the focused validator rejects any custom `province_modifier`, `character_modifier`, or `holding_modifier`; it also permits only the exact zero-value presentation bridge in `county_modifier`.

## Validation boundary

Run:

```powershell
python -X utf8 -B scripts/generate_aawc_stage3_buildings.py --check
python -X utf8 -B -m unittest discover -s scripts -p 'test_aawc_stage3_progression_effects.py'
python -X utf8 -B -m unittest discover -s scripts -p 'test_aawc_stage3_buildings.py'
```

The focused progression suite proves graph closure, monotonicity, source-tier bounds, acyclicity, regular-foundation termination, duchy-slot reachability, per-level emission, effects-inventory coverage, absence of falsely functional custom outputs, and removal of obsolete retained-main-line effect references. These are source and deterministic-generation claims; direct rendered construction-menu and AI confirmation remain part of the integrated review candidate.
