"""Independent integer/fixedpoint oracle for all-flow Hamilton accounting.

Only mathematical expectations are modeled. This does not emulate CK3 or
replace retained pre-policy save references.
"""
from aawc_cohort_apportionment import apportion

SCALE = 100000
INITIAL = (9, 8, 8, 8, 8, 8, 8, 8, 7, 7, 6, 5, 10)
ANNUAL = (1200, 300, 300, 500, 500, 500, 600, 600, 1000, 1200, 1600, 2200, 5500)


def allocate_flow(capacities, weights, pending=0):
    due = sum(weights) + pending
    allocation, _ = apportion(capacities, weights, due // SCALE)
    remainder = due - sum(allocation) * SCALE
    whole, fractional = divmod(remainder, SCALE)
    carries = [0] * len(weights)
    positive = [i for i, w in enumerate(weights) if w > 0]
    left = fractional
    for i in positive:
        carries[i] = left if i == positive[-1] else fractional * weights[i] // sum(weights)
        left -= carries[i]
    return allocation, carries, whole * SCALE + left


class Ledger:
    def __init__(self, bands=INITIAL):
        self.bands = list(bands)
        self.military = [0] * 9
        self.birth = 0
        self.mortality = [0] * 13
        self.aging = [0] * 12
        self.military_aging = [0] * 9
        self.mortality_pending = self.aging_pending = self.military_aging_pending = 0
        self.last_births = self.last_deaths = self.last_aged = 0
        self.last_military_aged = self.last_military_retired = self.last_military_deaths = 0

    def births(self):
        expected = (sum(self.bands[3:8]) - sum(self.military[:5])) * 1100 + self.birth
        self.last_births, self.birth = divmod(expected, SCALE)
        self.bands[0] += self.last_births

    def deaths(self):
        before = self.bands[:]
        weights = [n * r // 12 + c for n, r, c in zip(before, ANNUAL, self.mortality)]
        movers, self.mortality, self.mortality_pending = allocate_flow(before, weights, self.mortality_pending)
        self.last_deaths = sum(movers)
        self.bands = [n - d for n, d in zip(before, movers)]
        self.last_military_deaths = 0
        for j, m in enumerate(self.military):
            i = j + 3
            if movers[i]:
                removed = max(0, m - self.bands[i])
                self.military[j] -= removed
                self.last_military_deaths += removed

    def age(self):
        before = self.bands[:]
        weights = [n * SCALE // 60 + c for n, c in zip(before, self.aging)]
        movers, self.aging, self.aging_pending = allocate_flow(before[:12], weights, self.aging_pending)
        self.last_aged = sum(movers)
        for i, moved in enumerate(movers):
            self.bands[i] -= moved
            self.bands[i + 1] += moved
        forced, capacities, military_weights = [], [], []
        for j, m in enumerate(self.military):
            i = j + 3
            minimum = max(0, m - (before[i] - movers[i]))
            forced.append(minimum)
            capacities.append(min(m, movers[i]) - minimum)
            expected = movers[i] * m * SCALE // before[i] if before[i] else 0
            military_weights.append(expected + self.military_aging[j] - minimum * SCALE)
        selected, self.military_aging, self.military_aging_pending = allocate_flow(
            capacities, military_weights, self.military_aging_pending)
        selected = [a + m for a, m in zip(selected, forced)]
        for j in reversed(range(9)):
            self.military[j] -= selected[j]
            if j < 8:
                self.military[j + 1] += selected[j]
        self.last_military_aged = sum(selected[:8])
        self.last_military_retired = selected[8]

    def tick(self):
        before = sum(self.bands)
        self.births()
        self.deaths()
        self.age()
        assert sum(self.bands) == before + self.last_births - self.last_deaths
        assert all(0 <= m <= self.bands[i + 3] for i, m in enumerate(self.military))


def reference(months):
    ledger = Ledger()
    for _ in range(months):
        ledger.tick()
    return ledger
