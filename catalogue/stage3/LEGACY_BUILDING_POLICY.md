# Legacy Building Suppression and Unlock Routes

This is the dedicated authority for AAWC's post-review legacy-building policy. Compatibility is preserved: legacy definitions remain loaded, existing instances keep their modifiers, and exact-ID scripted references keep resolving. Ordinary legacy roots are removed from holding construction allow-lists; unretained special/duchy definitions are fully mirrored in a late override with only visibility, construction eligibility, and AI selection disabled.

AAWC definitions, primary holding chains, ruin/wilderness lifecycle chains, settlement blockers, and restored-special endpoints reached through AAWC wrapper chains are retained. The policy does not delete dependency definitions and does not migrate existing saves.

## Unlock-route summary

- Ordinary legacy roots mapped to AAWC replacements: 88
- Ordinary holding-specific no-replacement exceptions: 3
- Special/duchy legacy tiers mapped by catalogue lineage: 74
- Site-specific special/duchy no-replacement exceptions: 561
- Retained special/duchy tiers: 943
- Complete historical tier unlock contracts: 624 (618 replaced; 6 retained main-line tiers with AAWC annexes)
- No direct character-skill/lifestyle construction gate was identified in the effective legacy catalogue; none is invented.

Culture/innovation, faith/doctrine, government, geography/resource, prerequisite-building, development, holding-type, title/realm, and DLC predicates are classified per route in the machine-readable JSON authority. Catalogue-lineage replacements preserve their recovered legacy predicates tier by tier; analogous settlement routes use the approved replacement's own reachable AAWC gate contract.

## Ordinary catalogue routes

| Legacy root | AAWC replacement | Route | Holdings | Replacement gate classes |
|---|---|---|---|---|
| `agot_gold_mines_01` | `aawc_gold_mines_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding | building_prerequisite, geography_or_resource |
| `agot_iron_island_mines_01` | `aawc_iron_island_mines_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding | building_prerequisite, geography_or_resource |
| `agot_ironwood_01` | `aawc_ironwood_01` | `catalogue_lineage` | castle_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `agot_pirate_control_01` | `aawc_pirate_control_01` | `catalogue_lineage` | pirate_den_holding | building_prerequisite, government |
| `agot_pirate_economic_01` | `aawc_pirate_economic_01` | `catalogue_lineage` | pirate_den_holding | building_prerequisite, government |
| `agot_pirate_fortification_01` | `aawc_pirate_fortification_01` | `catalogue_lineage` | pirate_den_holding | building_prerequisite, government |
| `agot_pirate_military_01` | `aawc_pirate_military_01` | `catalogue_lineage` | pirate_den_holding | building_prerequisite, government |
| `agot_pirate_supply_01` | `aawc_pirate_supply_01` | `catalogue_lineage` | pirate_den_holding | building_prerequisite, government |
| `agot_pirate_troop_01` | `aawc_pirate_troop_01` | `catalogue_lineage` | pirate_den_holding | building_prerequisite, government |
| `agot_silver_mines_01` | `aawc_silver_mines_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding | building_prerequisite, geography_or_resource |
| `agot_slave_camps_01` | `aawc_slave_camps_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, pirate_den_holding, tribal_holding | building_prerequisite, geography_or_resource |
| `agot_steppe_farms_01` | `aawc_steppe_farms_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding | building_prerequisite, geography_or_resource |
| `agot_urban_farms_01` | `aawc_urban_farms_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding | building_prerequisite, geography_or_resource |
| `apiaries_01` | `aawc_apiaries_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding | building_prerequisite, geography_or_resource |
| `barracks_01` | `aawc_barracks_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `breweries_01` | `aawc_breweries_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding, tribal_holding | building_prerequisite |
| `building_moat_01` | `aawc_building_moat_01` | `catalogue_lineage` | castle_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `camel_farms_01` | `aawc_camel_farms_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `capital_bureau_01` | `aawc_capital_bureau_01` | `catalogue_lineage` | castle_holding, temple_citadel_holding | building_prerequisite, government, title_or_realm |
| `caravanserai_01` | `aawc_caravanserai_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, culture_or_innovation, geography_or_resource, holding_type |
| `cereal_fields_01` | `aawc_cereal_fields_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `citadel_shrine_01` | `aawc_citadel_shrine_01` | `catalogue_lineage` | temple_citadel_holding | building_prerequisite, dlc |
| `city_walls_01` | `aawc_city_walls_01` | `catalogue_lineage` | city_holding | holding_type |
| `colony_forestry_01` | `aawc_logging_camps_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, geography_or_resource |
| `colony_port_01` | `aawc_common_tradeport_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `colony_quarries_01` | `aawc_quarries_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, geography_or_resource |
| `common_tradeport_01` | `aawc_common_tradeport_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding, tribal_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `construction_guilds_01` | `aawc_workshops_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `curtain_walls_01` | `aawc_curtain_walls_01` | `catalogue_lineage` | castle_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `elephant_pens_01` | `aawc_elephant_pens_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `farm_estates_01` | `aawc_farm_estates_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `godswood_01` | `aawc_godswood_01` | `catalogue_lineage` | castle_holding, tribal_holding | building_prerequisite, faith_or_doctrine |
| `guild_halls_01` | `aawc_guild_halls_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding | building_prerequisite |
| `hill_farms_01` | `aawc_hill_farms_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `hill_forts_01` | `aawc_hill_forts_01` | `catalogue_lineage` | castle_holding | building_prerequisite, geography_or_resource |
| `hillside_grazing_01` | `aawc_hillside_grazing_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding, tribal_holding | geography_or_resource |
| `horse_pastures_01` | `aawc_horse_pastures_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding, tribal_holding | culture_or_innovation, geography_or_resource |
| `hospices_01` | `aawc_hospices_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, temple_citadel_holding | building_prerequisite |
| `hunting_grounds_01` | `aawc_hunting_grounds_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `hyperborean_trade_post_01` | `aawc_common_tradeport_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `idjang_forts_01` | `aawc_idjang_forts_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, government |
| `kora_kora_yards_01` | `aawc_kora_kora_yards_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, geography_or_resource, government |
| `local_militia_01` | `aawc_mustering_fields_01` | `analogous_settlement_route` | settlement_holding | geography_or_resource, holding_type |
| `logging_camps_01` | `aawc_logging_camps_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `lokirian_barracks_01` | `aawc_barracks_01` | `analogous_settlement_route` | castle_holding, church_holding, city_holding, tribal_holding | building_prerequisite, geography_or_resource |
| `longhouses_01` | `aawc_longhouses_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, government |
| `market_villages_01` | `aawc_market_villages_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, government |
| `megalith_01` | `aawc_megalith_01` | `catalogue_lineage` | temple_citadel_holding | building_prerequisite, faith_or_doctrine |
| `military_camps_01` | `aawc_military_camps_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `monastic_schools_01` | `aawc_monastic_schools_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding, tribal_holding | building_prerequisite, faith_or_doctrine |
| `murex_farm_01` | `aawc_murex_farm_01` | `catalogue_lineage` | castle_holding, city_holding | building_prerequisite, geography_or_resource |
| `oath_faithful_building_01` | `aawc_oath_faithful_building_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, temple_citadel_holding, tribal_holding | faith_or_doctrine |
| `oath_poor_building_01` | `aawc_oath_poor_building_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, temple_citadel_holding, tribal_holding | none |
| `oath_warriors_building_01` | `aawc_oath_warriors_building_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, temple_citadel_holding, tribal_holding | none |
| `orchards_01` | `aawc_orchards_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `outposts_01` | `aawc_outposts_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding | building_prerequisite, geography_or_resource |
| `paddy_fields_01` | `aawc_paddy_fields_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `palisades_01` | `aawc_palisades_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, government |
| `pastures_01` | `aawc_pastures_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `peat_quarries_01` | `aawc_peat_quarries_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `plantations_01` | `aawc_plantations_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `qanats_01` | `aawc_qanats_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `quarries_01` | `aawc_quarries_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `ramparts_01` | `aawc_ramparts_01` | `catalogue_lineage` | castle_holding | building_prerequisite, geography_or_resource |
| `regimental_grounds_01` | `aawc_regimental_grounds_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `sacred_pool_01` | `aawc_sacred_pool_01` | `catalogue_lineage` | temple_citadel_holding | building_prerequisite, dlc |
| `scriptorium_01` | `aawc_scriptorium_01` | `catalogue_lineage` | church_holding, temple_citadel_holding | building_prerequisite, dlc |
| `smiths_01` | `aawc_smiths_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `spice_plantation_01` | `aawc_spice_plantation_01` | `catalogue_lineage` | castle_holding, city_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `stables_01` | `aawc_stables_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `stilted_granaries_01` | `aawc_stilted_granaries_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, government |
| `stockades_01` | `aawc_palisades_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, government |
| `trading_outposts_01` | `aawc_market_villages_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, government |
| `tribal_construction_guilds_01` | `aawc_workshops_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, culture_or_innovation, geography_or_resource |
| `tribal_local_militia_01` | `aawc_mustering_fields_01` | `analogous_settlement_route` | settlement_holding | geography_or_resource, holding_type |
| `tribal_stockades_01` | `aawc_palisades_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, government |
| `tribal_trading_outposts_01` | `aawc_market_villages_01` | `analogous_settlement_route` | settlement_holding | building_prerequisite, government |
| `vihara_halls_01` | `aawc_vihara_halls_01` | `catalogue_lineage` | temple_citadel_holding | building_prerequisite, dlc |
| `wantilan_01` | `aawc_wantilan_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, government |
| `war_camps_01` | `aawc_war_camps_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, government |
| `warrior_lodges_01` | `aawc_warrior_lodges_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding, tribal_holding | geography_or_resource, government, holding_type |
| `watchtowers_01` | `aawc_watchtowers_01` | `catalogue_lineage` | castle_holding | building_prerequisite, geography_or_resource |
| `water_temples_01` | `aawc_water_temples_01` | `catalogue_lineage` | tribal_holding | building_prerequisite, government |
| `watermills_01` | `aawc_watermills_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, culture_or_innovation, geography_or_resource, holding_type |
| `waterworks_01` | `aawc_waterworks_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `wind_furnace_01` | `aawc_wind_furnace_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, geography_or_resource |
| `windmills_01` | `aawc_windmills_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, culture_or_innovation, geography_or_resource, holding_type |
| `workshops_01` | `aawc_workshops_01` | `catalogue_lineage` | castle_holding, church_holding, city_holding, monastery_holding, temple_citadel_holding | building_prerequisite, culture_or_innovation, geography_or_resource |

## Ordinary no-replacement exceptions

| Legacy root | Scope | Reason |
|---|---|---|
| `generic_dragon_pit_01` | castle_holding | Generic dragon pits are owned by AGOT's dragon lifecycle; AAWC has no safe repeatable structural substitute, so the legacy ordinary-menu route is hidden. |
| `valyria_mines_01` | castle_holding, church_holding, city_holding, tribal_holding | The active Valyria mine remains an exact-ID ruin/settlement lifecycle endpoint and is removed from ordinary settled-holding catalogues. |
| `valyria_mines_dormant_01` | castle_holding, church_holding, city_holding, tribal_holding | The dormant mine is retained only in ruin/settlement lifecycle holdings and is not a general-purpose economic construction route. |

## Special and duchy disposition

Every suppressed special/duchy tier is listed in `legacy_building_policy.json` with its source hash, gate classes, preserved-payload hash, and either an exact AAWC tier mapping or a per-ID no-replacement record. The no-replacement class is intentionally narrow: unique world landmarks and dependency-owned special sites do not become repeatable generic AAWC infrastructure. Existing instances remain active for save and event compatibility.

## Retained exceptions

- All `aawc_*` definitions, including the 131 Stage 3 chains and restoration wrappers.
- Primary holding chains for castle, city, church, tribe, temple citadel, monastery, pirate den, settlement, wilderness, nomad, herder, unknown, and ruin holdings.
- All roots registered in ruin and wilderness holdings, plus exact settlement blocker/cleared-state and Valyria mine lifecycle roots.
- Non-AAWC special endpoints reached recursively from AAWC restoration wrappers.

## Verification boundary

Focused tests enumerate holding-list suppression, mapping/no-replacement coverage, special override payload preservation, retained main/ruin availability, and target reachability. This is source/package validation; rendered CK3 menu inspection belongs to the integrated review candidate.
