"""Tests for the reference-scenario calculation engine.

Asserts the documented headline figures reproduce (Calculations §3–§5):
$88K manual investigation, ~12 min agent wall-clock, and the
$4.2M / $2.8M / ~340% chargeback scenario.
"""

from __future__ import annotations

from zero_day_warranty.calculations import (
    agent_chain_wall_clock_minutes,
    chargeback_scenario,
    manual_rca_baseline,
)


def test_manual_rca_baseline_is_88k_per_investigation() -> None:
    baseline = manual_rca_baseline()
    assert baseline.total_hours == 440
    assert baseline.cost_per_investigation == 88_000
    assert baseline.annual_cost == 880_000


def test_agent_chain_wall_clock_is_about_12_minutes() -> None:
    assert agent_chain_wall_clock_minutes() == 12.0


def test_chargeback_scenario_reproduces_headline_figures() -> None:
    result = chargeback_scenario()
    # $4.2M attributable (within rounding of the worked model)
    assert 4.15e6 <= result.attributable_usd <= 4.25e6
    # $2.8M agentic recovery at 67%
    assert 2.78e6 <= result.agentic_recovery_usd <= 2.85e6
    # ~340% improvement over the 15% manual baseline
    assert 340 <= result.improvement_pct <= 350


def test_scenario_inputs_are_parameterizable() -> None:
    from zero_day_warranty.calculations import ScenarioInputs

    # Double the plant volume → double the attributable exposure.
    base = chargeback_scenario()
    doubled = chargeback_scenario(ScenarioInputs(vehicles_per_week=10_000))
    assert round(doubled.attributable_usd, 2) == round(base.attributable_usd * 2, 2)
