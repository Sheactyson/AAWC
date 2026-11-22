"""Exact marginal arithmetic oracle for Stage 5; not a CK3 runtime adapter.

Population is in whole persons. Shares use the existing five-decimal ledger
precision. Culture and faith callers invoke these operations independently;
there is deliberately no joint identity or age distribution here.
"""
from fractions import Fraction

SCALE = 100000
ABSORPTION = 500  # CaFG V_kCAFG_absorption_threshold = 0.005


def validated_shares(shares):
    if not shares or any(not isinstance(v, int) or v < 0 for v in shares.values()):
        raise ValueError('nonempty nonnegative fixed-point shares required')
    if sum(shares.values()) != SCALE:
        raise ValueError('shares must sum to one')
    return shares


def majority(shares):
    validated_shares(shares)
    return min(shares, key=lambda key: (-shares[key], key))


def resolve_axis(shares, amount, explicit=None, title_majority=None):
    """Resolve legacy packet provenance; never reweight explicit provenance.

    Returns the repaired source axis and frozen vector without mutating inputs.
    Repairs only an absent/empty axis; contradictions in a populated axis fail.
    """
    if not isinstance(amount, int) or amount <= 0:
        raise ValueError('positive whole-person amount required')
    if not shares:
        if title_majority is None:
            raise ValueError('no source majority available')
        shares = {title_majority: SCALE}
    validated_shares(shares)
    vector = {majority(shares): amount} if explicit is None else dict(explicit)
    if any(not isinstance(v, int) or v < 0 for v in vector.values()):
        raise ValueError('invalid provenance quantity')
    if sum(vector.values()) != amount:
        raise ValueError('provenance must equal physical transfer')
    if any(v and not shares.get(k, 0) for k, v in vector.items()):
        raise ValueError('known identity absent at source')
    return dict(shares), vector


def normalize(masses, scale=SCALE, threshold=ABSORPTION):
    """Hamilton rounding, then canonical CaFG absorption; exact integer sum."""
    if scale <= 0 or not 0 <= threshold < scale:
        raise ValueError('invalid precision or threshold')
    if not masses or any(v < 0 for v in masses.values()) or sum(masses.values()) <= 0:
        raise ValueError('positive total nonnegative masses required')
    total = sum(masses.values())
    quotas = {k: Fraction(v) * scale / total for k, v in masses.items()}
    result = {k: int(v) for k, v in quotas.items()}
    ranking = sorted(quotas, key=lambda k: (-(quotas[k] - result[k]), -quotas[k], k))
    for key in ranking[:scale - sum(result.values())]:
        result[key] += 1
    largest = min(result, key=lambda k: (-result[k], k))
    absorbed = sum(v for k, v in result.items() if k != largest and v < threshold)
    result = {k: (v if k == largest or v >= threshold else 0) for k, v in result.items()}
    result[largest] += absorbed
    return result


def reconcile(shares, population, vector, *, debit=False, protective_floor=0):
    """Return new CaFG factors only. Absolute population belongs to the caller."""
    if not isinstance(population, int) or population < 0:
        raise ValueError('invalid absolute population')
    if not vector or any(not isinstance(v, int) or v < 0 for v in vector.values()):
        raise ValueError('invalid packet')
    amount = sum(vector.values())
    if amount <= 0:
        raise ValueError('empty packet')
    if population:
        validated_shares(shares)
    elif shares:
        validated_shares(shares)
    if debit and population - amount <= max(0, protective_floor - 1):
        raise ValueError('source protective floor')
    masses = {k: Fraction(population * shares.get(k, 0), SCALE)
              + (-1 if debit else 1) * vector.get(k, 0)
              for k in shares.keys() | vector.keys()}
    if any(v < 0 for v in masses.values()):
        raise ValueError('identity debt exceeds available source mass')
    return normalize(masses)


def departure(shares, population, amount, owner=None, residuals=None):
    """Capped weighted Hamilton allocation with signed per-identity carries.

    Residuals are returned, never changed in place: a caller commits them only
    after finding an eligible destination and reserving the physical transfer.
    Saturated identities clear their carry, avoiding impossible future debt.
    """
    validated_shares(shares)
    if not isinstance(population, int) or population < 0 or not isinstance(amount, int) or amount < 0:
        raise ValueError('invalid population or demand')
    residuals = residuals or {}
    if amount == 0:
        return dict.fromkeys(shares, 0), {k: Fraction(residuals.get(k, 0)) for k in shares}
    capacity = {k: population * v // SCALE for k, v in shares.items()}
    if amount > sum(capacity.values()):
        raise ValueError('insufficient marginal capacity')
    scores = {k: Fraction(population * v, SCALE) *
              (1 if owner is None else Fraction(1, 2) if k == owner else 2)
              for k, v in shares.items()}
    allocated = dict.fromkeys(shares, 0)
    carries = dict.fromkeys(shares, Fraction(0))
    active = {k for k in shares if capacity[k] > 0}
    remaining = amount
    while remaining and active:
        total = sum(scores[k] for k in active)
        quota = {k: Fraction(remaining) * scores[k] / total + Fraction(residuals.get(k, 0))
                 for k in active}
        saturated = {k for k in active if quota[k] >= capacity[k]}
        if saturated:
            for k in saturated:
                allocated[k] = capacity[k]
                remaining -= capacity[k]
            active -= saturated
            continue
        for k in active:
            allocated[k] = max(0, min(capacity[k], int(quota[k])))
        # Signed carries can push quotas below zero. Correct both directions
        # using greatest entitlement/debt, stable keys, and hard capacity bounds.
        while sum(allocated[k] for k in active) < remaining:
            k = min((k for k in active if allocated[k] < capacity[k]),
                    key=lambda k: (-(quota[k] - allocated[k]), k))
            allocated[k] += 1
        while sum(allocated[k] for k in active) > remaining:
            k = min((k for k in active if allocated[k]), key=lambda k: (quota[k] - allocated[k], k))
            allocated[k] -= 1
        for k in active:
            carries[k] = quota[k] - allocated[k]
        remaining = 0
    return allocated, carries
