# AAWC Dependencies Modpack provenance and ownership manifest

Package: `AAWC Dependencies Modpack` `1.1.1`  
Target: Crusader Kings III `1.19.0.6`  
Required load order: pinned `A Game of Thrones` `0.5.2.1` -> this package -> `AGOT_Alternate_World_Compatch` `1.10.5.12` or later.

This is a private, non-distributed personal-use package. It isolates stable dependency behavior from AAWC's frequently updated final compatibility layer. Original authors retain credit for their work; this package does not claim authorship of incorporated third-party content.

## Included controlled surfaces

- `[Kei] Culture and Faith Granularity` `2.3.1 - CK 1.19`, Workshop item `3206891770`, reconstructed from Steam depot manifest `9182003674219179648`: retained CK3 1.19 culture/faith state, county aggregation, conversion, tension, laws, factions, map modes, events, on-actions, GUI support, assets, and English localization. Credit remains with the original CaFG author and contributors.
- `[Kei] CaFG Compatibility - AGOT` `1.0.8`, Workshop item `3212180390`: retained six verified AGOT-safe support files, including 42 map-mode titles rooted at `c_kings_landing`. Credit remains with the original compatibility author.
- `[Kei] Enhanced County View` `1.2.5 - CK 1.20`, Workshop item `3336466278`, by Keitaro_Ura: retained eleven byte-verified CK3/GUI support files. CK3 1.20 Rite UI is excluded; AAWC keeps the CK3 1.19 county/faith conflict-resolution GUI.
- `More Game Rules`, CK3 `1.19` Workshop build, item `2216850785`, by Neutrino and its translation contributors: retained alternate-world startup, rule, effect, temporary-title, coat-of-arms, and English-localization behavior under the atomically remapped `aawc_*` namespace.
- `Legacy of Valyria` `1.5.2.13`, Workshop item `3403938445`, by its original authors and contributors: retained 1,355 byte-identical same-path runtime files that form the LoV-priority map/content base, plus three byte-identical Lokiria throne textures relocated to the compatibility paths required by the retained artifact asset. The pinned LoV source remains the byte authority for these 1,358 files.

The package contains 1,538 gameplay/support files: 180 controlled CaFG/bridge/ECV/MGR files, 1,355 byte-identical same-path LoV files, and three byte-identical relocated LoV textures, plus this manifest and `descriptor.mod`.

## 1.1.1 AAWC world-mode prerequisite enforcement

The three AAWC world modes now own the required retained-MGR foundation. `aawc_ruined_world`, `aawc_age_of_reclamation`, and `aawc_age_of_silence` all open the existing alternate-world dispatcher and force its Counties shatter branch plus All Tribal holdings branch, regardless of contradictory saved/custom rule selections. The visible retained rules also default to Counties and All Tribal and label those settings as AAWC requirements.

This changes conditions inside the established calls only. The `on_game_start` registration, MGR-derived call membership and order, MGR-before-CaFG filename order, and AAWC's later preselection/classification/reset sequence are unchanged.

## Deliberately retained in AAWC

AAWC remains the final conflict-resolution layer. Its source continues to own:

- all 70 AAWC-modified LoV paths that compose current AGOT contracts, LoV behavior, and AAWC conflict fixes, including `definition.csv`, landed titles/history masks, regions, locators, on-actions, GUI, settlement, ruin, restoration, colonization, and other final overrides;
- byte-exact `common/defines/lv_defines.txt`, because AAWC's intentional `replace_path="common/defines"` masks every earlier layer and therefore requires this government-registry file to remain physically in AAWC;
- the CK3 1.19 AGOT/ECV county and faith GUI, normal/Valyria mirrors, and LoV-ECV composition;
- AAWC CaFG compatibility shadows and AGOT-safe defaults, including `00_kei_cafg_game_rules.txt`, `zzzz_aawc_kei_cafg_agot_compat_*`, and previously established value/tension shims;
- the adapted Better Buyable Building Slot interaction, GUI button, safety rules, localization, modifier ownership, and 21-slot cap;
- all AGOT rebases and all AAWC settlement, colonization, migration, ruin, population, title-handoff, generated-building, and final override files.

## Excluded surfaces

- AGOT remains external and pinned; no AGOT file is copied here.
- LoV source paths not present in the certified 1,426-path retained integration boundary remain excluded. The 70 modified retained paths remain in AAWC and must never be replaced by their unmodified LoV sources in this package.
- CK3 1.20 CaFG Rite APIs, stale CaFG-AGOT whole-event/whole-GUI overrides, ECV Rite UI, unrelated More Game Rules systems, More Building Slots, More Building++, and Cities of Wonder 3 remain excluded.
- Better Buyable Building Slot is not moved into this package because AAWC's adapted implementation is a final compatibility surface rather than a standalone middle-layer copy.

## Release discipline

The source directory and release archive are independently versioned. `scripts/build_aawc_dependencies_modpack.py` builds only this package and emits deterministic ZIP bytes. `scripts/install_aawc_dependencies_modpack.py` installs only this package. Routine `build_aawc_release.py` runs without reading or rebuilding this package.

Every release must pass `scripts/validate_aawc_dependencies_modpack.py`, archive CRC and source/archive parity, live-install parity, the three-entry launcher order check, and the cross-layer AAWC equivalence gate. Runtime playability still requires CK3 startup, fresh campaigns, save/reload, GUI and culture/faith checks, map inspection, and the 14-month simulation gate.


## Government setup repair candidate (2026-10-25)

Two AAWC-owned helper paths implement ordered tribal holding/government conversion and guarded DLC-aware Sothoryos requests: `common/scripted_effects/aawc_setup_government_effects.txt` and `common/scripted_triggers/aawc_setup_government_triggers.txt`. The retained alternate-world caller now uses the two-pass helper. All remaining 1,355 same-path LoV files remain byte-identical. The Sothoryos title-history repair is a new same-path override in the final AAWC layer, removed from the middle layer so every modified LoV path remains exclusively AAWC-owned. Version identity remains 1.1.1 for this explicitly hash-pinned private candidate; native certification is pending.

## Pirate succession-law applicability repair (2026-10-26)

`aawc_setup_sothoryos_pirate_history_effect` now follows the pinned AGOT law contract after verifying the intended pirate government. County-only pirates retain their ordinary realm succession because `pirate_succession_law` requires a duchy-or-higher holder. Eligible duchy-or-higher pirates receive that law idempotently only on held titles above county tier, matching AGOT's game-start and title-gain lifecycle. No government target, runtime ID, title-history caller, unrelated law, or demographic behavior changes. The dependency version remains 1.1.1. The final archive, manifest and installation match source exactly across 1,541 entries; their non-self-referential hashes are retained with the task evidence. The repeated native fixture, actual same-date reload and strict save/log audits pass, closing the prior two law failures without waiver.
