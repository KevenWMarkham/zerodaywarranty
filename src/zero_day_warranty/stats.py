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


__all__ = ["ProportionTest", "two_proportion_z_test"]
