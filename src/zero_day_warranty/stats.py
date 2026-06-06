"""Minimal statistics helpers (no third-party numeric deps).

The reference run computes warranty-rate comparisons and a two-proportion
z-test by hand so the laptop substrate has zero heavy dependencies. The GPU
acceleration described in the architecture (NVIDIA RAPIDS cuML, steps 8/14/15)
replaces these with the same tests at 10–50× throughput; the math is identical.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ProportionTest:
    """Result of a two-proportion z-test."""

    rate_a: float
    rate_b: float
    rate_ratio: float
    z_score: float
    p_value: float

    @property
    def significant(self) -> bool:
        """True at the conventional alpha = 0.05 two-sided threshold."""
        return self.p_value < 0.05


def _two_sided_p(z: float) -> float:
    """Two-sided p-value for a z-score via the normal CDF (math.erfc)."""
    return math.erfc(abs(z) / math.sqrt(2.0))


def two_proportion_z_test(
    *, successes_a: int, n_a: int, successes_b: int, n_b: int
) -> ProportionTest:
    """Compare two proportions (group A vs. baseline group B).

    Used for "suspect-lot warranty rate vs. baseline" (steps 14–15) and the
    cohort × station interaction screen (step 8).
    """
    rate_a = successes_a / n_a if n_a else 0.0
    rate_b = successes_b / n_b if n_b else 0.0
    ratio = (rate_a / rate_b) if rate_b else float("inf")

    if n_a == 0 or n_b == 0:
        return ProportionTest(rate_a, rate_b, ratio, 0.0, 1.0)

    pooled = (successes_a + successes_b) / (n_a + n_b)
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n_a + 1.0 / n_b))
    z = (rate_a - rate_b) / se if se > 0 else 0.0
    return ProportionTest(rate_a, rate_b, ratio, z, _two_sided_p(z))


# ---------------------------------------------------------------------------
# Multiple-testing correction (Experts Panel gap #2)
#
# The chain screens many cohort × station × tool × supplier-lot combinations.
# Testing each at alpha=0.05 inflates false positives, so an attribution claim
# must survive a family-wise / false-discovery-rate correction.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MultipleTestResult:
    """Outcome of a multiple-testing correction over a family of p-values."""

    method: str
    alpha: float
    rejected: tuple[bool, ...]
    adjusted: tuple[float, ...]

    @property
    def n_significant(self) -> int:
        """How many hypotheses remain significant after correction."""
        return sum(self.rejected)


def bonferroni(pvalues: list[float], *, alpha: float = 0.05) -> MultipleTestResult:
    """Bonferroni family-wise correction: multiply each p-value by the family size."""
    n = len(pvalues)
    adjusted = tuple(min(1.0, p * n) for p in pvalues)
    rejected = tuple(p <= alpha for p in adjusted)
    return MultipleTestResult("bonferroni", alpha, rejected, adjusted)


def benjamini_hochberg(pvalues: list[float], *, alpha: float = 0.05) -> MultipleTestResult:
    """Benjamini-Hochberg FDR correction (step-up); returns adjusted q-values."""
    n = len(pvalues)
    if n == 0:
        return MultipleTestResult("benjamini-hochberg", alpha, (), ())
    order = sorted(range(n), key=lambda i: pvalues[i])
    adjusted = [0.0] * n
    running_min = 1.0
    # Walk ranks from largest p-value (rank n) down to smallest (rank 1).
    for rank in range(n, 0, -1):
        idx = order[rank - 1]
        q = min(1.0, pvalues[idx] * n / rank)
        running_min = min(running_min, q)
        adjusted[idx] = running_min
    rejected = tuple(adjusted[i] <= alpha for i in range(n))
    return MultipleTestResult("benjamini-hochberg", alpha, rejected, tuple(adjusted))


__all__ = [
    "MultipleTestResult",
    "ProportionTest",
    "benjamini_hochberg",
    "bonferroni",
    "two_proportion_z_test",
]
