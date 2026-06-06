"""Tests for the statistics helpers, including multiple-testing correction."""

from __future__ import annotations

from zero_day_warranty.stats import (
    benjamini_hochberg,
    bonferroni,
    two_proportion_z_test,
)


def test_two_proportion_z_test_significant_for_clear_signal() -> None:
    t = two_proportion_z_test(successes_a=69, n_a=1000, successes_b=30, n_b=1000)
    assert t.rate_ratio > 2.0
    assert t.significant


def test_bonferroni_is_more_conservative_than_raw() -> None:
    pvals = [0.001, 0.02, 0.04, 0.5]
    res = bonferroni(pvals, alpha=0.05)
    # raw would call 3 significant; Bonferroni (×4) keeps only the strongest
    assert res.adjusted[0] == 0.004
    assert res.rejected[0] is True
    assert res.rejected[2] is False
    assert res.n_significant < sum(1 for p in pvals if p < 0.05)


def test_benjamini_hochberg_monotone_and_bounded() -> None:
    pvals = [0.001, 0.008, 0.02, 0.04, 0.6]
    res = benjamini_hochberg(pvals, alpha=0.05)
    assert all(0.0 <= q <= 1.0 for q in res.adjusted)
    # the weakest hypothesis is not rejected
    assert res.rejected[-1] is False
    # BH rejects at least as many as Bonferroni
    bf = bonferroni(pvals, alpha=0.05)
    assert res.n_significant >= bf.n_significant


def test_empty_family_is_safe() -> None:
    assert bonferroni([]).n_significant == 0
    assert benjamini_hochberg([]).n_significant == 0
