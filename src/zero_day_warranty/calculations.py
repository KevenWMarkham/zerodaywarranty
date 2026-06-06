"""The reference-scenario calculation engine.

Every currency figure in the discovery pack has a calculation behind it. This
module makes that math executable and parameterized, so Toyota-specific inputs
can be swapped in during a Business Value Assessment without changing the
structure (Calculations & References §3–§5, §8 method disclosure).

All defaults are *reference-scenario figures* — synthetic, derived from
publicly-documented industry benchmarks and a worked plant-scale model. They
are not Toyota claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Calculation 1 · current-state manual RCA baseline (Calculations §3)
# ---------------------------------------------------------------------------

#: Person-hours per investigation, by the six teams in a manual warranty RCA.
RCA_TEAM_HOURS: dict[str, int] = {
    "Quality Assurance": 60,
    "Manufacturing Engineering": 80,
    "Plant Operations": 40,
    "Supplier Quality": 80,
    "Warranty / After-Sales": 60,
    "IT / Data Engineering": 120,
}

LOADED_LABOR_RATE_USD_PER_HOUR: float = 200.0


@dataclass(frozen=True)
class BaselineResult:
    """Cost of one manual warranty RCA investigation."""

    total_hours: int
    cost_per_investigation: float
    annual_cost: float
    investigations_per_year: int


def manual_rca_baseline(
    *,
    team_hours: dict[str, int] | None = None,
    rate: float = LOADED_LABOR_RATE_USD_PER_HOUR,
    investigations_per_year: int = 10,
) -> BaselineResult:
    """Calculation A — cost per manual warranty RCA investigation.

    ``440 hours × $200/hour = $88,000 per investigation``; at ~10/year that is
    ``$880,000`` in RCA labor cost annually.
    """
    hours = sum((team_hours or RCA_TEAM_HOURS).values())
    cost = hours * rate
    return BaselineResult(
        total_hours=hours,
        cost_per_investigation=cost,
        annual_cost=cost * investigations_per_year,
        investigations_per_year=investigations_per_year,
    )


# ---------------------------------------------------------------------------
# Calculation 2 · agentic-state wall-clock (Calculations §4)
# ---------------------------------------------------------------------------


def agent_chain_wall_clock_minutes(
    *,
    step_count: int = 24,
    seconds_per_step: float = 30.0,
) -> float:
    """Calculation B — agent-chain wall-clock in minutes.

    ``24 steps × ~30 seconds = ~12 minutes`` (normal-case execution; the
    human-review step is excluded from the wall-clock).
    """
    return (step_count * seconds_per_step) / 60.0


# ---------------------------------------------------------------------------
# Calculation 3 · the $4.2M / $2.8M / 340% scenario (Calculations §5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioInputs:
    """Inputs to the reference chargeback scenario (Calculations §5)."""

    vehicles_per_week: int = 5_000
    affected_build_weeks: int = 3
    warranty_cost_per_vehicle: float = 300.0
    suspect_lot_penetration: float = 0.40  # 40% of the window got the suspect lot
    excess_warranty_rate: float = 2.3  # vs. baseline (the "3x" heatmap observation)
    failure_tail_multiplier: float = 1.8  # 3-year warranty curve
    manual_recovery_rate: float = 0.15
    agentic_recovery_rate: float = 0.67

    @property
    def affected_vehicles(self) -> int:
        """Total vehicles produced in the affected window."""
        return self.vehicles_per_week * self.affected_build_weeks

    @property
    def lot_vehicles(self) -> int:
        """Vehicles in the window that received the suspect supplier lot."""
        return round(self.affected_vehicles * self.suspect_lot_penetration)


@dataclass(frozen=True)
class ScenarioResult:
    """Outputs of the reference chargeback scenario."""

    attributable_usd: float
    agentic_recovery_usd: float
    manual_recovery_usd: float
    improvement_pct: float
    base_impact_usd: float = field(default=0.0)

    def as_summary(self) -> dict[str, float]:
        """Headline figures as a flat dict (for CLI / report rendering)."""
        return {
            "attributable_usd": self.attributable_usd,
            "agentic_recovery_usd": self.agentic_recovery_usd,
            "manual_recovery_usd": self.manual_recovery_usd,
            "improvement_pct": self.improvement_pct,
        }


def chargeback_scenario(inputs: ScenarioInputs | None = None) -> ScenarioResult:
    """Calculations C1–C3 — the $4.2M / $2.8M / 340% reference figures.

    - **C1** attributable warranty exposure: incremental per-vehicle warranty
      cost on the suspect-lot vehicles, scaled by the multi-year failure tail.
    - **C2** agentic chargeback recovery: attributable × agentic recovery rate.
    - **C3** improvement over the manual baseline recovery.
    """
    i = inputs or ScenarioInputs()

    incremental_per_vehicle = i.warranty_cost_per_vehicle * (i.excess_warranty_rate - 1.0)
    base_impact = i.lot_vehicles * incremental_per_vehicle
    attributable = base_impact * i.failure_tail_multiplier

    agentic = attributable * i.agentic_recovery_rate
    manual = attributable * i.manual_recovery_rate
    improvement = ((agentic - manual) / manual * 100.0) if manual else 0.0

    return ScenarioResult(
        attributable_usd=attributable,
        agentic_recovery_usd=agentic,
        manual_recovery_usd=manual,
        improvement_pct=improvement,
        base_impact_usd=base_impact,
    )


__all__ = [
    "LOADED_LABOR_RATE_USD_PER_HOUR",
    "RCA_TEAM_HOURS",
    "BaselineResult",
    "ScenarioInputs",
    "ScenarioResult",
    "agent_chain_wall_clock_minutes",
    "chargeback_scenario",
    "manual_rca_baseline",
]
