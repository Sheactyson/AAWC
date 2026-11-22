# Stage 3 building localization and presentation policy — 1.11.4.12

This entry is the source authority for the post-review building-copy pass. It covers the 131 AAWC catalogue chains, 771 generated tiers, 23 retained main-line tiers, and nine retained small/medium/large ruin-clearance tiers. It does not claim rendered CK3 certification.

## Description convention

Every catalogue tier combines a `#F ...#!` CK3/AGOT-style description grounded in the structure's material setting and social role with a short functional sentence that points only to the live structural-condition and Settlement Space rows below it. Tier descriptions advance through an eight-step maturity vocabulary. Proposal-only `native_role.distinct_identity` metadata is never promoted into functional copy: the live 1.11.4.13 test caught that wording incorrectly claiming deferred MAA output, and 1.11.4.14 removes the entire proposal-derived sentence path. Copy never presents deferred Stage 6 military outputs, Stage 7 population-scaled economic outputs, or proposal-only native roles as live modifiers.

## Compact modifier convention

Generated `effect_desc` entries contain rows, not paragraphs. Each nonzero contribution is rendered as an icon, a green or red signed value, and its dimension label. Settlement Space is always present, including `0%`, so a chain's land-use contract is explicit.

| Field | Icon |
| --- | --- |
| Sustenance | `@county_fertility_icon!` |
| Habitation | `@building_icon!` |
| Opportunity | `@county_icon!` |
| Health | `@county_fertility_icon!` |
| Security | `@soldier_icon!` |
| Amenities | `@opinion_icon!` |
| Settlement Space | `@building_icon!` |

Values are the cumulative installed-tier values from `catalogue/stage3/catalogue.json`; upgrading replaces the preceding tier. The display contains no Growth Rating, fixed Building Capacity, Migration Rating, or prose about deferred systems.

## Prerequisite wording

The 53 authored prerequisite progressions are emitted from the same `progression_requirements()` result used to append the scripted `has_building_or_higher` gates. Each effect description therefore names the exact required AAWC tier. Alternative source chains use `or`; the two Siege Works foundations remain separate required rows. Culture, faith, terrain, resource, holding, title, and other inherited gates continue to render through CK3's native requirement UI and are not paraphrased into potentially stale prose.

## Retained main lines and ruins

The retained castle, city, settlement, temple, temple-citadel, and tribe definitions now reference AAWC presentation keys. Their panels show all six dimensions plus Settlement Space, including explicit zeroes. The displayed contribution exactly matches `aawc_stage2_main_level`: level 1 is neutral; every additional main-line tier adds `+3 Habitation` and `+1 Opportunity`; Settlement Space is `0%`. Native CK3/AGOT modifier blocks remain functional and render separately.

The retained `small_ruined_holding`, `medium_ruined_holding`, and `large_ruined_holding` clearance chains are not valid Stage 1/2 settlements. Their descriptions show the three clearance stages, explicit zeroes for all six dimensions and Settlement Space, and a note that structural conditions remain inactive while the holding is a ruin. No unimplemented ruin penalty is invented.

## Deterministic ownership and validation

`scripts/generate_aawc_stage3_buildings.py` owns `aawc_stage3_buildings_l_english.yml` and `aawc_retained_building_presentation_l_english.yml`.

```powershell
python -X utf8 -B scripts/generate_aawc_stage3_buildings.py --check
python -X utf8 -B scripts/test_aawc_stage3_buildings.py
python -X utf8 -B scripts/test_aawc_stage3_presentation.py
```

The presentation suite exhaustively verifies flavor/functional text, icon rows, signed values, prerequisite references, retained definition bindings, main-line tier math, ruin inactivity, localization uniqueness, and absence of superseded effect labels.

For `1.11.4.12`, deterministic construction, catalogue, and legacy-policy checks pass and the complete focused Stage 3 family passes 73/73. Package verification reports exact 486/486/486 source/archive/manifest parity with clean CRC. Rendered CK3 typography and wrapping remain an integrated-review observation, not a source-test claim.
