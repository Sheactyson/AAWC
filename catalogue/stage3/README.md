# Stage 3 catalogue authoring contract

`catalogue.json` is the editable source of truth. The strict schema-v1 validator is
`scripts/generate_aawc_stage3_catalogue.py::validate`. Historical D7/D8 inputs under
`evidence/stage3/imported/` are immutable provenance, not a second editable source.
Changing a proposal here does not approve it or activate it in CK3.

Run from the repository root:

```powershell
python -X utf8 -B scripts/generate_aawc_stage3_catalogue.py
python -X utf8 -B scripts/generate_aawc_stage3_catalogue.py --check
python -X utf8 -B scripts/test_aawc_stage3_catalogue.py
```

The compiler uses the Python standard library and needs neither CK3 nor an
installed upstream mod. Paths are relative to the checkout. `--check` is read-only
and fails on missing, stale, or extra artifacts.

## Schema v1

Objects are closed: unknown or missing fields fail validation. Numbers must be
finite JSON numbers; booleans and numeric strings are rejected as numbers.

| Source object | Required contract |
| --- | --- |
| Root | Schema version, catalogue identity, hash-pinned import provenance, fixed Stage ownership policy, 131 chains |
| Chain | Unique ID, regular/duchy kind, family, legacy/new lineage, construction gates, presentation, AI, semantic review, levels |
| Gates | Status, authored proposal, nullable cited predicate text and source reference; approval requires both |
| Chain presentation | Status, proposed name, nullable description/icon/model/effect-description; approval requires all fields |
| AI | Status and nullable value; approval requires a nonnegative value |
| Semantic review | Explicit pending/approved status and reason |
| Level | Unique building ID, nullable legacy ID, integer tier, exact next-tier ID or terminal null, costs, construction days, conditions, capacity, tradeoffs, level-specific gate proposals, native role, constructibility, localization metadata |
| Costs | Nonnegative gold, prestige and piety; gold must be positive |
| Conditions | Exactly Sustenance, Habitation, Opportunity, Health, Security and Amenities, as signed cumulative installed-level contributions |
| Capacity | Separate `space_percent` and review status; missing means null, never implicit zero |
| Tradeoffs | Exact negative-condition subset plus nullable authored notes; negative effects remain signed |
| Native role | Deferred status and proposed output/role metadata as text; never executable effects |
| Constructibility | `blocked_review` with explicit reasons; this prerequisite has no runtime activation mode |
| Level presentation | Nullable proposed display name and deterministic name, description and effect-description localization keys |

The census is fixed to 99 regular and 32 duchy chains, 105 inherited lineages and
26 new chains, with 771 total levels. Tiers begin at one and are contiguous.
Upgrade links cannot skip tiers, cross chains, cycle or leak from a terminal tier.
All 624 historical level IDs are retained. Heritage chains contain 626 candidate
levels: Great Megalith and Tower of Silence each add a second tier with no legacy
counterpart. The 26 new chains contain 145 levels. These mappings are lineage
metadata, not implemented callers or compatibility wrappers.

The one-time `scripts/import_aawc_stage3_catalogue.py` bootstrap validates the
hash-pinned historical files and refuses to overwrite an existing source. Its
`--check-import` option audits exact initial-import parity; it is not a constraint
against later explicitly reviewed authoring changes. Normal regeneration always
reads `catalogue.json`. Historical predicate excerpts are cited evidence, not
complete validated trigger blocks. All tier names and explicit `space_percent`
values remain unspecified by the v2 input; none are fabricated by the bootstrap.

## Generated artifacts and ownership

- `generated/levels.json` materializes inherited gate, asset, AI and lineage
  metadata on every level, retaining all numeric, review and player-facing fields.
- `generated/condition_candidates.csv` is an inspectable projection of all six
  scores and the separate space field. Its status columns and blank unresolved
  capacity cells deliberately distinguish it from the approved Stage 2 adapter
  CSV. It is not a drop-in replacement for that table.
- `generated/readiness.json` records counts, canonical source hash, ownership
  policy, and every blocked level. Valid source is not runtime readiness.

All output is inert JSON/CSV, sorted by chain and tier, encoded as UTF-8 with LF
newlines, without timestamps or machine-specific paths. No production building
definitions, scripted effects, population mutations, demographic formulas,
Stage 6 military lifecycle, or Stage 7 native-output scaling are emitted.
Native-role proposals and predicate strings remain data even if they contain
CK3 syntax. The CLI refuses output under live mod/dependency directories.

Runtime building authoring, semantic approval, predicate authoring/refresh,
compatibility wrappers and caller migration, assets/localization/AI completion,
and Stage 2 adapter integration remain separate Stage 3 tasks. Their acceptance
must not be inferred from a passing source compiler or an installable tooling
release. Direct menu/gameplay certification requires rendered inspection.
