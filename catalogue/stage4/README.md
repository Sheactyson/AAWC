# Reforged Stage 4 transaction contract

This directory is the deterministic source contract for the Stage 4 colony
transaction layer.  `scripts/generate_aawc_stage4_transactions.py` emits the
runtime scripted effects and values from the fixed thirteen-band Stage 1
ledger.  Generated files identify their source and must not be edited by hand.

The shared expedition lifecycle is:

1. Planning may cache cost and destination metadata but does not reserve or
   debit residents.
2. Travel start allocates an exact age-band packet across concrete eligible
   source holdings.  The packet remains in the Stage 1 cohort ledger and is
   excluded from other non-fatal outward transfers while reserved.
   During the synchronous monthly demographic authority it is detached and
   reattached unchanged, keeping the token's exact age bands stable while all
   unreserved residents continue normal demographic processing.
3. Release is accepted only from the preparing/reserved states.  It clears
   every source packet and the sponsor availability reserve once; repeated
   callbacks are no-ops.
4. Commit is accepted only after the native AGOT/Legacy of Valyria handoff has
   produced a non-dummy, non-ruin destination.  Every source packet and its
   ownership is validated before the first debit.
5. Commit debits the exact reserved bands, credits the same bands up to the
   caller's retained-population amount, and records the remaining packet as
   explicit attrition.  `debit - credit - attrition` must equal zero.

The API owns no title, holder, travel, blocker, building, culture, faith, or
restoration transition.  Route adapters call it around the upstream handoff.
The existing LoV travel on-actions are the first adapter and preserve story
registration before reservation so the protected first expedition is not
purged while the route planner is still open.

## Generated outputs

- `common/scripted_effects/aawc_stage4_cohort_reservation_effects.txt`
- `common/script_values/aawc_stage4_cohort_reservation_values.txt`

## Token states

- `0`: planned only
- `1`: reserved
- `2`: committed
- `3`: released or failed before mutation
- `4`: preparing (rollback-eligible)

Terminal receipts remain on the settler token until the next reservation is
prepared.  Source holdings retain no transaction variables after release or
commit.

## New-holding funding and pending settlements

New-holding provinces use the same exact packet states. Construction start
reserves the type-specific founding population from real source holdings;
cancellation releases the token once. Completion first clears any generic
startup seed, then commits only after every source packet validates. If no
exact packet exists or validation fails, the completed holding remains marked
`aawc_stage4_pending_settlement` with zero residents.

Pending holdings are excluded from the Stage 1 settlement eligibility trigger,
which suppresses initialization, monthly demographics, workforce, and
settlement privileges. Their AAWC tax/levy values are zero and the dedicated
province modifier suppresses native tax, levy, garrison, reinforcement, and
development benefits. Each current top liege retries exact funding before the
monthly growth pass. Only a validated source debit removes pending state; the
matching age-band packet is then credited and normal Stage 1/2 lifecycle work
resumes.

## Colony lifecycle

A successful post-handoff expedition credit marks the destination as a colony.
Ruin and wilderness holdings remain ineligible for the Stage 1 ledger and are
therefore zero-resident/non-growing. While a colony has a native `obstacle`
blocker, its normal monthly Stage 2 structural replay carries the established
six-dimension blocker contribution; clearance progressively removes those
contributions. When no obstacle remains, colony mode is removed exactly once
without changing residents, title identity, holder, holding type, or any
restoration workflow. Final neutrality and separate blocker decline
coefficients are intentionally unauthored and recorded in
`colony_lifecycle_unresolved_config.md`; no new balance values are inferred.
