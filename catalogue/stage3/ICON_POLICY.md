# Stage 3 building-icon inventory

## Scope

This is the visual-asset authority for the 131 active Stage 3 construction
chains. Every chain has exactly one `aawc_<chain>.dds` icon under
`mod/AGOT_Alternate_World_Compatch/gfx/interface/icons/building_types/`.
Its upgrade tiers share that one icon because they are successive forms of the
same underlying structure. No different chains share artwork, including chains
in the same gameplay family.

The authoritative visual contract is the same one already proved by the AAWC
blocker-chain icons: every source cell and runtime DDS contains a simple,
fully opaque black subject on a fully transparent background. It deliberately
contains no baked-in frame, plate, color wash, painterly background, or
partially transparent edge. CK3 therefore supplies the visible state color
through the transparent pixels: the enabled building plate remains blue and
the unavailable or disabled plate can gray out normally.

The silhouettes are original deterministic AAWC primitives rather than
extracted CK3 or AGOT art. `scripts/aawc_stage3_icon_primitives.ps1` owns their
subject families and chain-specific identity details.
`scripts/generate_aawc_stage3_icons.ps1` rebuilds both the nine transparent
source atlases and the runtime assets in exactly the blocker icons' 256×256
uncompressed BGRA DDS layout.

## Source-sheet inventory

The sheet/cell registry is explicit in `generate_aawc_stage3_icons.ps1`, not
alphabetically inferred. Positions are left-to-right, then top-to-bottom.
Sheets 01–08 use all sixteen cells; sheet 09 uses its first three cells.

| Sheet | Chains in cell order |
| --- | --- |
| 01 | amber_collection; apiaries; archery_ranges; archery_yards; barracks; blacksmiths; breweries; building_moat; burial_site; camel_farms; capital_bureau; caravanserai; cavalry_courses; cereal_fields; citadel_shrine; coastal_fisheries |
| 02 | common_tradeport; curtain_walls; dragon_kiln; duchy_agricultural_estates; duchy_civic_court; duchy_grand_harbor; duchy_grand_hospital; duchy_military_college; duchy_royal_theatre; elephant_pens; examination_hall; farm_estates; glass_gardens; godswood; gold_mines; great_megalith |
| 03 | guild_halls; hill_farms; hill_forts; hillside_grazing; horse_pastures; hospices; hunting_grounds; idjang_forts; infirmaries; iron_island_mines; ironwood; irrigation_estates; jousting_lists; kora_kora_yards; leatherworkers; leisure_palace |
| 04 | lighthouse; logging_camps; longhouses; march; market_villages; megalith; military_academy; military_camps; monastic_schools; monument_works; murex_farm; mustering_fields; oath_faithful_building; oath_poor_building; oath_warriors_building; orchards |
| 05 | outposts; paddy_fields; palisades; pastures; peat_quarries; pirate_control; pirate_economic; pirate_fortification; pirate_military; pirate_supply; pirate_troop; plantations; powder_magazine; public_baths; public_squares; qanats |
| 06 | quarries; ramparts; regimental_grounds; river_docks; river_fisheries; royal_armory; royal_forest; royal_garden; sacred_pool; saltworks; scholars_quarters; scholastic_guilds; scriptorium; sewers; shipwrights; siege_works |
| 07 | silver_mines; slave_camps; slave_diplomacy; slave_intrigue; slave_learning; slave_martial; slave_stewardship; smiths; spice_plantation; stables; steppe_farms; stilted_granaries; tax_assessor; temple_citadel; terraced_farms; tower_of_silence |
| 08 | trade_guilds; tribe; urban_farms; urban_tenements; vihara_halls; village_cottages; vineyard; wantilan; war_camps; warrior_lodges; watchtowers; water_temples; watermills; waterworks; wind_furnace; windmills |
| 09 | charnel_grounds; city_walls; workshops |

`catalogue/stage3/icon_sources/aawc_stage3_icons_01.png` through `_09.png`
are deterministic transparent source atlases. They are regenerated from the
primitive library rather than treated as opaque illustration inputs. The
conversion script fails closed if any source sheet or runtime asset is absent,
has non-black RGB data, has partial alpha, lacks transparent background, or
lacks an opaque subject.

## Reuse and deferred exceptions

- Reuse is limited to the levels in one chain. There are 131 runtime DDS
  assets for 131 chains; a chain never borrows the old generic market icon.
- The only intended contextual continuity is tier progression within the same
  chain. Similar mechanics (for example, different military, maritime, faith,
  or pirate chains) have separate silhouettes and artwork.
- There are no visual-format exceptions. All 131 chains must follow the same
  blocker-derived transparency and silhouette contract.
- Direct CK3 inspection of installed `1.11.4.15` showed the engine plate through
  the silhouettes in enabled-blue and unavailable/disabled-gray states in both
  regular and duchy construction menus. The blocker-derived format is therefore
  rendered-verified for this version.

## Focused validation

```powershell
powershell -ExecutionPolicy Bypass -File scripts/generate_aawc_stage3_icons.ps1 -Check
python -X utf8 -B scripts/test_aawc_stage3_icons.py
```

The test requires the 131 generated definition references to be distinct by
chain, rejects `icon_building_market_villages.dds`, validates every target
asset's DDS magic, dimensions, byte length, exact blocker header, all-black
RGB channels, binary transparent/opaque alpha, and unique payload, and confirms
every referenced path is inside the release builder's recursive mod input
tree.

The direct result is recorded in
`evidence/stage3/AAWC_1.11.4.15_BUILDING_OVERHAUL_LIVE_VALIDATION.json`.
