# AAWC Reforging 1.11 — Stage 1 Population Authority Graph

**Status:** Final Milestone 0 contract for Stage 1 implementation. This document maps the complete baseline set of direct `aawc_population_current` writers. The isolated Stage 1A representation pilot is implemented, but no production writer has migrated and no live cohort ledger is active.

**Authority:** `workspace/AAWC_Reforging_1.11_Design_and_Codex_Handoff.md`, especially sections 3, 11, 12, and 15.

**Generated evidence:** `workspace/AAWC_Reforging_1.11_Milestone_0_Audit/aawc_reforging_population_mutations.csv` and `aawc_reforging_population_authorities.csv`, produced by `scripts/audit_aawc_reforging_milestone0.py`.

## Audit correction and closed inventory

The first audit revision counted only mutation commands whose target variable appeared on the same physical line. That omitted multiline `change_variable` blocks and two multiline settlement writers, and it could label prefixed event-file scripted effects as file scope. The corrected auditor extracts each complete balanced mutation statement, recognizes indented top-level definitions and `scripted_effect NAME = { ... }`, and produces byte-deterministic output across consecutive runs.

The corrected baseline contains 709 population/reservation mutation statements under 72 exact file/authority pairs. There are no file-scope rows. Exactly 22 statements in 13 authorities directly mutate `aawc_population_current`; these replace the superseded 640/68 and ten-authority preliminary counts.

## Required Stage 1 invariants

1. The thirteen age bands are the people ledger. `aawc_population_current` and visible aggregate totals are derived mirrors, never an independent source of people.
2. Every direct writer below must be replaced, adapted, or removed before the Stage 1 exit gate. No compatibility wrapper may write the aggregate without applying and reconciling the same cohort transaction.
3. Military overlays remain subsets of adult age bands. Civilian-to-military classification is net zero; supported deaths and explicit dispersal are the only military paths that reduce total people.
4. Transfers must carry an age-aware package from source to destination. Source debit, reservation/package state, destination credit, and any explicit travel loss must reconcile exactly.
5. Holding conversions preserve people. Capacity reductions may change conditions and future demography but may not clamp or delete residents.
6. Read-only refreshes may rebuild expected capacity, dimensions, display mirrors, and diagnostics, but may not initialize or mutate people after the explicit fresh-start initializer has run.
7. The old aggregate monthly-growth write is disabled only after the cohort monthly authority has passed multi-year accounting, one-tick, and UI-drift tests.

## Direct-writer disposition

| Baseline authority | Current write | Stage 1 disposition | Later-stage boundary |
|---|---|---|---|
| `aawc_population_update_holding_dynamic_effect` | Initializes missing ordinary holdings to 100, ruin/wilderness to zero, and clamps negatives. | Split initialization from refresh. A one-time fresh-start initializer creates the approved thirteen-band 100-person distribution for survivor holdings and zero bands for unreclaimed ruin/wilderness. Dynamic refresh becomes read-only and derives the aggregate from bands. | Stage 2 replaces old capacity/growth inputs with dimensions; refresh remains non-mutating. |
| `aawc_population_apply_holding_monthly_growth_effect` | Applies aggregate monthly growth and a zero clamp. | Supersede with the sole scheduled cohort birth/death/aging authority, including fractional remainders, adult military-overlay reconciliation, before/after logging, and one-authoritative-tick guard. | Stage 2 supplies calibrated dimension-driven fertility, mortality, and crowding curves. |
| `aawc_population_consume_reserved_from_holding_surplus_effect` | Debits an immediate reservation spend from a holding's aggregate population. | Select only eligible civilian cohort members, debit the bands exactly, and attach the same age package to the reservation/transaction record. Never reduce military overlays implicitly. | Stage 4 consumes these packages for colonization/reclamation; other construction callers retain the same transaction boundary. |
| `aawc_population_spend_reserved_pool_from_holding_effect` | Proportionally debits reserved population from contributing holdings. | Apply the proportional amount to eligible civilian bands and accumulate one age-aware transfer package. Reconcile contributor debits to the reservation amount with deterministic remainder handling. | Stage 4 changes costs and arrival behavior, not this conservation rule. |
| `aawc_population_on_new_holding_completed` | Seeds a completed holding with its reserved aggregate cost. | Credit the exact saved cohort package to the destination; reject completion if package accounting is absent or mismatched. Remove the raw aggregate setter. | Stage 3 may change building availability; Stage 4 may change colony packages, but neither may invent residents. |
| `aawc_establish_owned_settlement_from_gui` | Consumes a population cost but seeds a fixed 250 residents; the baseline difference is unclassified disappearance. | Route player settlement through the shared cohort reservation/transfer authority. Destination credit plus explicit classified loss must equal source debit; no fixed population seed. | Stage 4 approves final settlement cost, travel-loss, and blocker-demography tuning. |
| `aawc_population_ai_establish_selected_owned_settlement_effect` | AI equivalent of the GUI path, with the same cost/start mismatch. | Use the identical shared cohort transaction and invariants as the player path; AI receives no population shortcut. | Stage 4/8 tune colony costs and AI policy without changing conservation. |
| `lv_settlement_establish_effect` | Enforces a minimum settlement population of 100 at two points. | Consume and credit the expedition's saved arrival package once. Remove both minimum-100 injections; rerunning restoration hooks must be idempotent for population. | Stage 4 supplies the finalized 250/500-per-slot expedition package and explicit travel losses. |
| `aawc_age_of_silence_found_tribal_holding_effect` | Directly creates 100 residents. | Replace with an explicit, source-backed founding package. If no legitimate source is engine-accessible for the landless route, keep this path blocked and present a reviewed exception; do not fabricate residents. | Stage 4 owns the final Age of Silence/colony transfer contract. |
| `aawc_migration_apply_holding_population_delta_effect` | Applies aggregate projected migration deltas. | Preserve the coordinated reservation/commit boundary but transfer explicit cohort packages and verify connected-world net zero. The old rating model may remain temporarily, but its payload cannot remain aggregate-only. | Stage 5 replaces scoring, family batching, and destination absorption policy. |
| `aawc_population_spend_maa_population_pool_from_holding_effect` | Removes residents from the holding to back legacy MAA replenishment. | Convert eligible adult civilians into age-band military overlays without reducing total people. Preserve existing replenishment callbacks only behind this net-zero adapter. | Stage 6 replaces the legacy pool with verified stationed-regiment support, casualty, and unstationing rules. |
| `aawc_population_apply_warfare_population_loss_effect` | Removes a percentage of aggregate holding population. | Debit explicit bands and matching military overlays as classified warfare deaths, with exact before/after totals. Stage 1 may use a documented interim age distribution but may not write only the aggregate. | Stages 2 and 6 refine age vulnerability and supported military casualty attribution. |
| `aawc_population_cap_tribal_to_feudal_conversion_effect` | Deletes residents above 50% of expected capacity during tribal-to-feudal conversion. | Remove the population clamp entirely. Recompute structure/capacity and preserve every cohort and overlay through conversion; overcrowding acts through later births/deaths, never instant deletion. | Stage 2 supplies the post-conversion capacity/crowding response. |

## Transaction graph and implementation order

1. Fresh-start initialization creates age bands, military overlays at zero, fractional accumulators, and derived aggregate mirrors.
2. A shared cohort transaction primitive performs deterministic debit/credit/package reconciliation and invariant logging.
3. Reservation, construction, player settlement, AI settlement, LoV settlement, and migration payloads migrate to that primitive before their raw aggregate writes are removed.
4. Warfare uses a classified death primitive; MAA spending uses a net-zero civilian-to-military primitive; conversion removes its destructive clamp.
5. The cohort monthly authority replaces old natural growth last, after all nonscheduled writers reconcile against the same ledger.
6. Validators must fail on any newly introduced direct aggregate writer, any unresolved file-scope mutation, band/overlay/aggregate disagreement, transfer imbalance, or second monthly mutation.

## Milestone boundary

This graph finalizes the repository-side Stage 1 mutation contract. It approves no production writer migration. The additive Stage 1A source pilot defines only new, unhooked `aawc_reforging_*` fields and read-only diagnostics; `scripts/validate_aawc_reforging_stage1a_cohort_pilot.py` proves it adds no aggregate writer or production reference. Save/reload, runtime scope, and performance proof remain required before this graph can authorize adapting even one live writer. The 23-regular/8-duchy catalogue, dynamic native-output control, regiment lifecycle APIs, and a clean `1.11.0.1` fresh-campaign runtime remain separate gates recorded in the feasibility map.
