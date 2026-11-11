"""Exact reference for the selected largest-remainder whole-person policy.

This is a mathematical oracle, not a CK3 emulator or evidence of native cost.
Inputs are nonnegative integer capacities and exact integer weights (any common
scale). Zero weights receive nothing. Saturated bands are removed and quotas
are recomputed before Hamilton rounding. Exact ties use ascending band index.
Demand that cannot be served is returned explicitly, never silently discarded.
"""
from fractions import Fraction


def apportion(capacities, weights, requested):
    if len(capacities) != len(weights) or not capacities:
        raise ValueError('capacities and weights must have the same nonzero length')
    if not isinstance(requested, int) or requested < 0:
        raise ValueError('requested must be a nonnegative integer')
    if any(not isinstance(x, int) or x < 0 for x in (*capacities, *weights)):
        raise ValueError('capacities and weights must be nonnegative integers')
    allocation = [0] * len(capacities)
    remaining = requested
    active = {i for i, (cap, weight) in enumerate(zip(capacities, weights)) if cap and weight}
    while remaining and active:
        weight_sum = sum(weights[i] for i in active)
        quotas = {i: Fraction(remaining * weights[i], weight_sum) for i in active}
        saturated = {i for i in active if quotas[i] >= capacities[i]}
        if saturated:
            for i in saturated:
                allocation[i] = capacities[i]
                remaining -= capacities[i]
            active -= saturated
            continue
        floors = {i: int(q) for i, q in quotas.items()}
        extras = remaining - sum(floors.values())
        ranking = sorted(active, key=lambda i: (-(quotas[i] - floors[i]), i))
        for i in active:
            allocation[i] = floors[i] + (i in ranking[:extras])
        remaining = 0
    return allocation, remaining


def flow(capacities, expected_fixedpoint, pending_fixedpoint=0, scale=100000):
    """Pool demand, allocate whole persons, return *all* unserved demand.

    The caller owns lifetime and classification of pending demand. This helper
    makes no decision about conversion, cancellation, or subsequent recipients.
    """
    if pending_fixedpoint < 0 or scale <= 0:
        raise ValueError('pending must be nonnegative and scale positive')
    due = sum(expected_fixedpoint) + pending_fixedpoint
    allocation, _ = apportion(capacities, expected_fixedpoint, due // scale)
    return allocation, due - sum(allocation) * scale
