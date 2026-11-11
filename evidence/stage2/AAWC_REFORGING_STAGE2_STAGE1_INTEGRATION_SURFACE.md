# AAWC Reforging 1.11.2.x — Stage 1 Integration Surface for Stage 2

**Recorded:** 2026-11-09  
**Development designation:** `1.11.2.0-stage2-map.0` (documentation-only development record; descriptors remain `1.11.1.0`)  
**Evidence:** source inspection plus focused Stage 1 static/prototype tests; no new CK3 runtime or rendered claim  
**Scope:** the authoritative holding lifecycle, demographic ledger, legacy capacity inputs, environmental access patterns, crisis-loss routes, tests, packaging workflow, and documentation that Stage 2 must extend

## Outcome

Stage 2 has one safe demographic integration surface: retain the existing thirteen-band province ledger and its single guarded monthly authority, calculate structural/effective living conditions before that authority reads its birth and mortality inputs, and replace the legacy `aawc_population_expected` capacity formula without restoring scalar population growth.

The Stage 1 source already exposes six zero-valued living-condition inputs, a zero capacity-pressure input, and neutral birth/mortality multipliers. Those declarations are deliberately inert. The birth multiplier is a usable insertion point. The single shared mortality multiplier is not sufficient by itself for Stage 2's required age-specific hardship response; Stage 2 must add per-band condition-aware mortality inputs or per-band multipliers while preserving the existing band variables, pooled rounding, fractional carries, and one monthly authority.

The old aggregate growth pipeline still calculates holding type, building, terrain, control, epidemic, and occupancy values for cache/UI/compatibility purposes, but its population mutation was retired. In particular, the epidemic override currently changes only `aawc_population_final_growth_rate`; it does not kill residents. Stage 2 must not treat that dormant calculation as an existing disease-loss debit.

## Inspected candidate identity

The writable source contains 337 files under `workspace/AGOT_Alternate_World_Compatch`. Git cleanliness cannot be asserted because the repository's `.git` directory is empty. The following hashes bind this map to the inspected sources:

| Source | SHA-256 |
| --- | --- |
| `common/on_action/aawc_population_on_actions.txt` | `E6DC7687AA19AF7A429EB38D2BC5D05F6B518CE86531662A007DB3FDE8125D54` |
| `common/on_action/aawc_population_holding_construction_on_actions.txt` | `9539466D53C28D30FD68EDDC224B6FD48C4173E60AB86E0F47552BDC29DDD6C9` |
| `common/on_action/aawc_population_warfare_on_actions.txt` | `454341027858055351C98AA08176A905F7A1DFBF7F914C2AE888F7ECDE35229C` |
| `common/scripted_effects/aawc_population_effects.txt` | `8E1EA0C3E6E1A3B6EA2EC5CAA9F1C12F55005A7DCFC89E9BAC70945D7D6C0BCC` |
| `common/scripted_effects/aawc_reforging_cohort_production_effects.txt` | `1DC02867831431E3A9D29822D6423134D3B3DD8913A4526A888D0262FBEECEE6` |
| `common/scripted_effects/aawc_reforging_cohort_stage1_effects.txt` | `742B26D9EB3E4E7AB04660827CDE9AAFD19E0C6FA4A00049672775BD31BB0286` |
| `common/scripted_effects/aawc_reforging_cohort_rounding_effects.txt` | `B18173855D3271755C29B09A3BBC2762CBD201C031D32CD40C1C680488A1D008` |
| `common/scripted_effects/zz_aawc_population_cache_effects.txt` | `51ED87996FBD033C29E0E63DE5655C635C46605A1706622F131731D279A61A80` |
| `common/script_values/aawc_population_values.txt` | `D2BD0366F422AA242E27F79F4700E68A451FEF65B266F3649FF2D88A8FF96412` |
| `common/script_values/aawc_reforging_cohort_stage1_values.txt` | `ADC614457E8AC6102A843D6F2BA86BF87540CF130F2B3A85AB7B0712A530DD1D` |
| `common/scripted_triggers/aawc_population_triggers.txt` | `EFD5B3EBBEB9E412029DF3A2450DC3090BBF14EBBF2D0541062C05F1FD2DF938` |
| `events/aawc_population_events.txt` | `AAEC467731A3E634892E93E3E085EA4D444CDC626F89699F9A52BADAF5B0B57C` |

## Authoritative holding lifecycle

| Phase | Authoritative route | Stage 2 extension boundary |
| --- | --- | --- |
| Eligible holding definition | `aawc_population_valid_settlement_for_cohort_trigger`, `common/scripted_triggers/aawc_population_triggers.txt:7-20` | Conditions belong only on populated/eligible holdings. Current eligible types are castle, tribal, city, church, nomad, herder, temple-citadel, pirate-den, and settlement. Ruin, wilderness, unknown, typeless, and no-holding provinces are cleared rather than simulated. |
| Fresh-game initialization | `on_game_start_after_lobby` -> `aawc_population_on_startup_pulse`, `common/on_action/aawc_population_on_actions.txt:19-73` | Initializes every eligible barony in each owned county through `aawc_population_initialize_holding_demographics_effect`; conditions may be initialized/recalculated here but must not create a second resident ledger. |
| Ledger initialization | `aawc_population_initialize_holding_demographics_effect`, `aawc_population_effects.txt:2-19`; `aawc_reforging_cohort_initialize_production_ledger_effect`, `aawc_reforging_cohort_production_effects.txt:260-430` | New uninitialized eligible holdings receive the established aggregate or default 100 and Hamilton apportion it into thirteen bands. Stage 2 state may be created alongside this path. Repeated ensure calls are idempotent. |
| Post-start eligibility reconciliation | delayed `aawc_population_event.0101`, `events/aawc_population_events.txt:3-12`; `aawc_reforging_cohort_reconcile_world_settlement_eligibility_effect`, production effects `:229-254` | Runs after world-mode conversion. Ineligible ledgers are cleared. Stage 2 persistent condition state must follow the same eligibility lifecycle without deleting structural caches needed for later valid conversion. |
| Recurring scheduler | `aawc_population_event.0100`, events `:14-46`, initially scheduled by startup and recovered by quarterly/yearly hooks | One 31-day character chain per landed non-dummy ruler, guarded by a 27-day character flag. Do not create a separate Stage 2 pulse. |
| Title transfer recovery | `on_title_gain` -> `aawc_population_on_county_holder_gain_cadence`, on-actions `:25-29,75-93` | Calls the same province-local monthly path; the province's 27-day lease prevents duplicate demographic ticks across owners. |
| Per-ruler/per-holding path | `aawc_population_apply_monthly_growth_character_effect`, `aawc_population_effects.txt:1431-1445`, then county-holder baronies and `aawc_population_apply_holding_monthly_growth_effect`, `:139-206` | Recalculate structural/effective conditions and capacity in this existing visit before the cohort tick. Do not reintroduce the retired scalar capacity-growth mutation. |
| Sole production adapter | `aawc_reforging_cohort_apply_production_month_effect`, production effects `:460-478` | Ensures the ledger, rejects duplicate province ticks with a 27-day lease, allocates a serial, and calls the sole monthly authority. |
| Sole natural-demography authority | `aawc_reforging_cohort_monthly_authority_effect`, `aawc_reforging_cohort_stage1_effects.txt:393-435` | Keep this order and guard: births, ordinary mortality, aging, inert Stage 6 training, reconcile, refresh mirrors, accounting. Stage 2 changes the values consumed by births/mortality, not the authority topology. |
| Building completion | `on_building_completed` -> `aawc_population_on_new_holding_completed`, construction on-actions `:15-20,176-219` | Every completed holding/building upgrade marks the holding static cache dirty. Stage 2 structural-condition and capacity caches should use this invalidation rather than polling all building definitions every month when unchanged. |
| New holding creation | same completion route, `:189-216` | Receipt-backed source debit precedes destination ledger initialization. Stage 2 initializes conditions after the holding exists; it must not change settlement accounting. |

## Persistent demographic state Stage 2 must preserve

### Resident authority and mirrors

- Thirteen authoritative whole-person province variables: `aawc_reforging_cohort_age_00_04`, `05_09`, `10_14`, `15_19`, `20_24`, `25_29`, `30_34`, `35_39`, `40_44`, `45_49`, `50_54`, `55_59`, and `60_plus`.
- Initial apportionment weights are `9/8/8/8/8/8/8/8/7/7/6/5/10`, implemented in `aawc_reforging_round_initialize_bands_effect`, rounding effects `:651-699`.
- Four display cohorts are derived values: children (0-14), younger adults (15-39), older adults (40-59), and elderly (60+), in `aawc_reforging_cohort_stage1_values.txt:9-35`.
- Seven stored mirrors are rebuilt only from authoritative state by `aawc_reforging_cohort_refresh_mirrors_effect`, stage1 effects `:10-20`: the four display cohorts, total population, military total, and civilian adults.
- `aawc_population_current` is a compatibility mirror, not authority. Its sole sanctioned writer is `aawc_reforging_cohort_sync_legacy_population_effect`, production effects `:9-21`; `aawc_population_total` and `aawc_population_surplus` are refreshed there as derived compatibility state.

### Durable fractional state

- Birth carry: `aawc_reforging_birth_fraction`.
- Thirteen ordinary-mortality carries: `aawc_reforging_mortality_fraction_age_*`.
- Twelve resident aging carries: `aawc_reforging_aging_fraction_age_*` for each closed five-year edge from 00-04 through 55-59.
- Nine adult military-aging carries and one inert training carry. Together with birth, mortality, and resident-aging carries, Stage 1 preserves 36 durable fractional carries.
- External fatal losses use the separate `aawc_reforging_round_population_death_pending` carry so crisis rounding does not overwrite the ordinary-mortality carries or the completed natural-tick snapshot.

### Guards, accounting, and diagnostics

- Initialization markers: `aawc_reforging_cohort_stage1_initialized` and `aawc_reforging_cohort_production_initialized`; the production marker is written last.
- Tick state: `aawc_reforging_cohort_requested_tick`, `aawc_reforging_cohort_last_tick`, `aawc_reforging_cohort_tick_count`, `aawc_reforging_cohort_tick_in_progress`, and the temporary 27-day `aawc_reforging_cohort_monthly_tick_recent` lease.
- Natural accounting: `last_before_total`, `last_births`, `last_deaths`, `last_aged`, `last_after_total`, and `last_expected_after`.
- External accounting: `last_external_deaths`, cumulative `external_deaths_total`, last transfer credit/debit, last loss class, and transaction receipts.
- Reconciliation clamps negatives to zero and military subsets to their parent age bands; it never manufactures residents (`aawc_reforging_cohort_reconcile_effect`, stage1 effects `:22-63`).

## Existing birth, mortality, and aging integration

Births use civilian residents aged 15-39 after subtracting military subsets. The neutral monthly demand is reproductive civilians multiplied by `0.011` and `aawc_reforging_stage2_birth_rate_multiplier` (`aawc_reforging_cohort_stage1_values.txt:37-50,92-100`). Whole births enter age 00-04; the remainder persists (`aawc_reforging_cohort_apply_births_effect`, stage1 effects `:265-282`).

Ordinary mortality is already age-specific. Annual rates are `0.012 / 0.003 / 0.003 / 0.005 / 0.005 / 0.005 / 0.006 / 0.006 / 0.010 / 0.012 / 0.016 / 0.022 / 0.055`, divided by twelve and multiplied by the one shared neutral Stage 2 mortality multiplier (`aawc_reforging_cohort_stage1_values.txt:102-181`). Pooled bounded rounding applies the losses and maintains per-band carries. Stage 2 must preserve these baseline rates and rounding while making condition response age-sensitive; replacing the one shared multiplier with thirteen condition-aware multipliers/values is safer than flattening mortality outside the ledger.

Aging is snapshot-based: one-sixtieth of each closed five-year band becomes monthly demand, pooled allocation is decided before mutations, and writes occur oldest-to-youngest. The 60+ band is open-ended. Stage 2 should not alter aging.

The existing inert Stage 2 declarations are at `aawc_reforging_cohort_stage1_values.txt:77-90`:

- `aawc_reforging_stage2_sustenance_input`
- `aawc_reforging_stage2_habitation_input`
- `aawc_reforging_stage2_opportunity_input`
- `aawc_reforging_stage2_health_input`
- `aawc_reforging_stage2_security_input`
- `aawc_reforging_stage2_amenities_input`
- `aawc_reforging_stage2_capacity_pressure_input`
- `aawc_reforging_stage2_birth_rate_multiplier`
- `aawc_reforging_stage2_mortality_rate_multiplier`

The seven inputs are zero and both multipliers are one. No structural/effective condition scores or carrying-capacity pressure are active yet.

## Legacy capacity and pressure surface to replace

The current compatibility capacity is `aawc_population_expected`:

1. `aawc_population_holding_main_line_capacity_base` selects the highest recognized main building level (`settlement_01-03`, `tribe_01-02`, `city_01-05`, `temple_01-04`, or `castle_01-05`) and falls back by holding type (`aawc_population_values.txt:1222-1250`).
2. `aawc_population_holding_main_line_development_bonus` multiplies the main line by `1 + county.development_level * 0.0045` (`:1252-1267`).
3. `aawc_population_holding_building_expected_capacity` adds fixed capacity from 595 explicit `has_building` checks (`:624-1221`). Standard, duchy, AGOT, Dependencies, AAWC, and special buildings are all accessed through the same trigger surface; the formula does not distinguish provenance.
4. `aawc_population_holding_expected` adds main-line and building capacity (`:1269-1277`).
5. `aawc_population_refresh_holding_static_effect` caches expected capacity, main capacity, building capacity, growth rating, terrain multiplier, and development snapshot (`zz_aawc_population_cache_effects.txt:1-30`).

Legacy occupancy pressure is a step table in `aawc_population_update_holding_dynamic_effect`, `aawc_population_effects.txt:42-80`: below 75% it applies no suppression (and below 25% it boosts the retired scalar rate); from 75% through 125% it steps down to zero. The cohort monthly path no longer consumes that scalar growth result. Stage 2 should replace this with progressive pressure that degrades effective Habitation and, where appropriate, effective Health; it must not apply both the old pressure multiplier and new condition effects to births/deaths.

`aawc_population_expected` has 120 references across 14 source files. Besides UI and caches, important consumers include migration protective floors/receive caps (`zzzz_aawc_population_migration_effects.txt`), reservation/MAA surplus calculations, county/character aggregation, tribal-to-feudal conversion capping, settlement GUI gates, and transaction validation. Stage 2 may change the capacity formula behind this compatibility variable, but should retain its numeric meaning as physical holding capacity until each consumer is deliberately migrated. It must not silently rename capacity while leaving those consumers bound to stale semantics.

Current gaps relevant to Stage 2:

- Eligible nomad, herder, temple-citadel, and pirate-den holdings have no holding-type fallback in the legacy main-line capacity value unless a recognized main building supplies one.
- The 595-building capacity list treats infrastructure as undifferentiated additive capacity and therefore cannot satisfy Stage 2's Habitation-led, Sustenance-moderated, tradeoff-aware model unchanged.
- The separate 595-building growth-rating list plus terrain multiplier feeds only the retired scalar growth calculation; it is useful as an infrastructure inventory, not as a Stage 2 formula.

## Safe environmental and infrastructure access patterns

| Required input | Existing verified source pattern | Notes for Stage 2 |
| --- | --- | --- |
| Holding type | `has_holding_type = ...` in the eligibility trigger and capacity/base-growth values | Safe for structural baselines. Cover every currently eligible holding type, not only the five legacy capacity fallbacks. |
| Main holding building and level | ordered `has_building = castle_05 ... castle_01`, city, temple, tribe, settlement in `aawc_population_holding_main_line_capacity_base` | CK3 resolves level through concrete building IDs. Preserve highest-level ordering so lower levels do not stack. |
| Standard/duchy/special buildings | explicit `has_building = <id>` checks in the two 595-entry building values | This is the established cross-mod-safe read surface. One building must contribute only to relevant dimensions/tradeoffs. Stage 3 should target reusable contribution values rather than demographic formulas. |
| Terrain | AGOT helper triggers such as `agot_is_urban_terrain`, `agot_is_farmlands_terrain`, `agot_is_floodplains_terrain`, `agot_is_oasis_terrain`, and the other positive/negative terrain groups at `aawc_population_values.txt:1351-1361` | Reuse the installed stack's helper triggers. Terrain should contribute separately to Sustenance, settlement space/Habitation, Health, or Security where justified, rather than one universal multiplier. |
| Development | `county.development_level`, directly read in `aawc_population_values.txt:1252-1260` and snapshotted in static refresh | Existing monthly dynamic refresh invalidates when the development snapshot changes. Development can support main settlement/infrastructure baselines but should not grant all six scores. |
| Building changes | `on_building_completed` marks `aawc_population_static_cache_dirty` | Reuse for structural conditions and capacity. Construction start/cancel is reservation state, not a completed structural contribution. |
| County control | `county.county_control`, clamped to 100 in `aawc_population_holding_control_factor`, values `:1391-1398` | A situational Security/stability input, not a generic birth or capacity multiplier. |
| Epidemic presence/intensity | `county = { has_province_with_epidemic = { intensity ... } }`, `aawc_population_effects.txt:107-124` | Safe situational Health input. Its current scalar growth override is dormant and must not be counted as deaths. |
| Raid/siege/war state | active county variables `aawc_population_raid_growth_suppressed` and `aawc_population_siege_growth_suppressed` | Safe temporary Security/disruption inputs. `aawc_population_warfare_growth_suppressed` is still read by compatibility code but has no writer in the current AAWC source, so Stage 2 must not treat it as an active signal unless it adds an explicit lifecycle. Direct event losses already exist separately and must not be repeated as ordinary mortality. |
| Occupancy | authoritative `aawc_reforging_cohort_band_sum` or compatibility mirror `aawc_population_current`, divided by the new physical capacity | Use the band sum inside demographic values. Pressure should alter effective conditions, not write residents or impose a target. |

## Crisis and other loss paths that must not be double-counted

| Cause | Active hook and amount | Ledger route | Stage 2 boundary |
| --- | --- | --- | --- |
| Raid completion | `on_raid_action_completion`, 15% of current holding population, warfare on-actions `:85-112` | `aawc_population_apply_warfare_population_loss_effect` -> `aawc_reforging_cohort_death_population_effect` -> child/elderly-first crisis debit | Effective Security/Health may deteriorate during a raid, but the 15% event loss is already a direct external death. Do not reproduce it through a second crisis mortality charge. |
| Siege completion | defensible castle/tribal/settlement holding, 30%, warfare on-actions `:114-183` | same centralized external-death route | Temporary effective Security can affect ordinary demography while the siege is active; the capture loss remains separate. |
| County occupation | non-defensible occupied holdings, 10%, warfare on-actions `:185-208` | same centralized external-death route | Do not apply both occupation loss and a second one-time Stage 2 occupation death. |
| Hostile army / active raid | temporary county suppression variables, warfare on-actions `:37-83` | no direct loss until completion hooks | These are appropriate temporary effective-condition inputs. |
| Disease/plague | epidemic intensity is read in the legacy dynamic effect, but source-wide authority tests find no active AAWC-owned disease/plague population writer | no current debit | Stage 2 may express ordinary disease burden through effective Health and age-specific ordinary mortality. If a future epidemic event adds direct deaths, it must use the central external-death API and be excluded from duplicate ordinary crisis charges. |
| Ordinary mortality | thirteen monthly age-specific candidates inside the sole cohort tick | pooled per-band mortality rounding and `last_deaths` | Stage 2 conditions modify this route. Direct warfare deaths remain in `last_external_deaths`, not `last_deaths`. |
| Tribal-to-feudal conversion | caps population at 50% of `aawc_population_expected`, `aawc_population_effects.txt:1690-1733` | `aawc_reforging_cohort_set_population_target_effect`, loss class 7 | This is an established conversion rule, not crowding mortality. A changed capacity formula can change its cap, so it requires a focused regression. |
| Legacy MAA expenditure | established MAA spending route | `aawc_reforging_cohort_debit_legacy_maa_population_effect`, adult-only, loss class 6 | Not mortality and not Stage 2. Preserve separately. |
| Migration/settlement spending | exact transfer packets or receipt-backed debit/credit/consumption | central transaction adapters | Not deaths. Do not let Stage 2 reconciliation reinterpret movement or construction consumption as mortality. |

The only production caller of `aawc_reforging_cohort_death_population_effect` is the warfare helper at `aawc_population_effects.txt:1853-1889`; the other call is an isolated Stage 1 runtime fixture. This makes the disease boundary explicit rather than inferred.

## Stage 2 implementation constraints derived from the map

1. Keep `aawc_reforging_cohort_monthly_authority_effect` as the only natural-demography authority.
2. Recalculate/copy structural and effective conditions before births and mortality are evaluated in that tick. Read-only GUI refresh must never initialize or advance them.
3. Persist the six structural and six effective scores as province variables if save-visible state is required; clamp each to 0-100. Keep structural state independent from temporary pressure/crisis deductions.
4. Replace the current zero Stage 2 input values with reusable dimension contribution values. Building-specific contributions must remain outside birth/mortality formulas so Stage 3 can add buildings without editing demographic math.
5. Keep one birth multiplier insertion point, but add age-band-specific mortality modulation. A single universal mortality multiplier cannot satisfy distinct child/elderly vulnerability without flattening the Stage 1 architecture.
6. Replace the legacy expected-capacity formula behind the compatibility cache with a Habitation-led, Sustenance-moderated, geography/main-holding model. Audit all 14 consumer files and specifically retest migration caps, MAA protected population, conversion capping, settlement gates, and county/character caches.
7. Retire the old occupancy-pressure effect from demographic meaning. New crowding effects should flow through effective Habitation/Health only; do not add an unexplained extra crowding death or fertility penalty.
8. Keep direct raid/siege/occupation losses in the external-death path. Temporary crisis conditions may influence ordinary births/deaths only while active and must not duplicate event percentages.
9. Keep `aawc_population_current` derived from the band sum. No Stage 2 formula may set/change it directly.
10. The supplied Stage 2 directive is truncated at the beginning of long-term calibration. This map is not blocked, but final calibration must use the recovered authoritative remainder or explicitly document which targets are unavailable rather than inventing them.

## Focused tests and validation locations

Primary Stage 1 gates to retain and extend:

- `scripts/test_aawc_stage1_demographic_engine_acceptance.py` — exact fixture, initialization, births, age-specific mortality, aging, duplicate guards, inert Stage 2 inputs, and reference projections.
- `scripts/validate_aawc_reforging_stage1_cohort_engine.py` — source contract, 36 carries, invariants, and authority consumption.
- `scripts/validate_aawc_reforging_stage1_authority_graph.py` — rejects unauthorized scalar population writers/caller escapes.
- `scripts/validate_aawc_reforging_stage1_candidate_activation.py` — verifies one guarded production monthly tick.
- `scripts/test_aawc_stage1_population_transaction_acceptance.py` — settlement/migration/MAA/crisis separation and central death profile.
- `scripts/test_aawc_cohort_tick_cadence.py` — duplicate scheduler/tick rejection.
- `scripts/test_aawc_population_readonly_refresh.py` — cache/UI refresh cannot initialize or mutate residents.
- `scripts/test_aawc_valid_settlement_lifecycle.py` and `scripts/test_aawc_cohort_caller_accounting.py` — receipt-backed lifecycle and one accounting route per caller.
- `scripts/run_aawc_reforging_stage1_integrated_validation.py` — bounded non-GUI integrated runner. Stage 2 should add focused dimension/capacity/equilibrium tests rather than relabeling this Stage 1 runner as Stage 2 certification.

Required new Stage 2 coverage belongs in later implementation tasks: score clamping and structural/effective separation; infrastructure tradeoffs; capacity composition; progressive occupancy pressure; 125% favorable-case net decline; age-sensitive hardship; no crisis double debit; differentiated agricultural/commercial/military/industrial/religious fixtures; and long-run equilibrium without a target-population write.

## Packaging, versioning, and documentation workflow

- Writable mod source: `workspace/AGOT_Alternate_World_Compatch/` plus `workspace/AGOT_Alternate_World_Compatch.mod`.
- Living master documentation: `versions/AGOT_Alternate_World_Compatch_Documentation_Master.md`.
- Working documentation exists at `workspace/AGOT_Alternate_World_Compatch_Documentation_Working.md`, but its current hash differs from the newer master; do not overwrite the master wholesale from that stale working copy.
- Release builder: `python -B scripts/build_aawc_release.py`. It reads matching inner/outer descriptor versions, validates blocker-description inputs, writes the archive and SHA-256 manifest under `versions/<first-three-version-components>/`, uses POSIX ZIP paths, and validates the two required roots.
- Candidate verifier: `python -B scripts/verify_aawc_release_candidate.py --workspace <workspace> --archive <zip> --manifest <manifest> --version <version> [--install-root <root>] [--report <json>]`.
- Release names follow `AGOT_Alternate_World_Compatch_X.Y.Z.N.zip`; iterative `X.Y.Z.N` builds are archived under `versions/X.Y.Z/`. Internal mod names remain unversioned.
- Do not use PowerShell `Compress-Archive`. Do not create versioned workspace copies. Build from the single live workspace and retain release zips/manifests.
- This discovery record changes no gameplay source and creates no package. `1.11.2.0-stage2-map.0` is a development-record designation only, matching the Stage 1 precedent; the later packaging task must update both descriptors together and create the first actual `1.11.2.x` archive after the integrated source is verified.

## Documentation authority

- Stage 1 demographic engine: `workspace/AAWC_REFORGING_STAGE1_DEMOGRAPHIC_ENGINE_ACCEPTANCE.md`.
- Stage 1 transaction integration: `workspace/AAWC_REFORGING_STAGE1_POPULATION_TRANSACTION_INTEGRATION_ACCEPTANCE.md`.
- Stage 1 integrated validation: `workspace/AAWC_REFORGING_STAGE1_INTEGRATED_VALIDATION_MATRIX.md`.
- Stage 1 review package and readiness: `workspace/AAWC_REFORGING_STAGE1_REVIEW_PACKAGE/`, especially `01_DEMOGRAPHIC_DATA_SPECIFICATION.md`, `02_POPULATION_MUTATION_OWNERSHIP_MATRIX.md`, `03_BIRTH_AGING_MORTALITY_SPECIFICATION.md`, `04_INTEGRATION_REPORT.md`, `05_VALIDATION_MATRIX.md`, and `09_STAGE2_READINESS_REPORT.md`.
- Frozen caller baseline: `workspace/AAWC_REFORGING_1_11_STAGE1_BASELINE_AND_MUTATION_MATRIX.md`.
- Living project authority and version workflow: `versions/AGOT_Alternate_World_Compatch_Documentation_Master.md`, Sections 3.1-3.5 and the append-only version log.

## Focused verification performed for this map

From `C:\Users\sheac\AAWC` on 2026-11-09:

- `python -X utf8 -B scripts/test_aawc_stage1_demographic_engine_acceptance.py`: 9/9 PASS.
- `python -X utf8 -B scripts/validate_aawc_reforging_stage1_authority_graph.py`: PASS; zero direct population-authority writers and one sanctioned compatibility-mirror writer.
- `python -X utf8 -B scripts/validate_aawc_reforging_stage1_candidate_activation.py`: PASS; recurring and title-gain paths share one province-guarded adapter and the retired scalar growth mutation is absent.
- `python -X utf8 -B scripts/test_aawc_stage1_population_transaction_acceptance.py`: 11/11 PASS, including distinct MAA/crisis profiles and central external-death routing.

These results validate the mapped Stage 1 topology and its preserved boundaries. They do not validate any Stage 2 implementation, CK3 parser/runtime behavior, save persistence, or rendered UI.

Workspace hygiene remains a documented limitation rather than a hidden success. The two pre-existing generated files `scripts/__pycache__/aawc_hook_only_control.cpython-310.pyc` and `scripts/__pycache__/verify_aawc_release_candidate.cpython-310.pyc` were re-identified. A single exact-path PowerShell removal attempt was rejected before execution by command policy, so both files and their directory remain. No alternate deletion bypass was attempted.

## Disposition

The Stage 1 integration surface is mapped completely enough for the condition/capacity implementation task to begin. No Stage 1 source defect was found within this discovery contract. The key downstream correction is architectural rather than a repair: Stage 2 cannot meet age-specific mortality requirements through the existing single shared mortality multiplier alone, and it must treat dormant legacy disease/pressure calculations as compatibility inputs rather than active demographic losses.
