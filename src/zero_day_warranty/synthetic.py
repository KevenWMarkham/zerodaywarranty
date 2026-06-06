"""Synthetic reference-scenario data generator.

Produces a deterministic, mock-substrate dataset across the four domains that
embeds the reference signal the agent chain is designed to find:

- An **affected build window** (weeks 12–14) over-represented in warranty claims.
- A **suspect supplier lot** present in ~40% of the window's vehicles, installed
  at a single **hot station / tool** that shows calibration drift.
- Suspect-lot vehicles carry an **elevated warranty rate** (~2.3× baseline).
- **SPC anomalies** in the quality stream preceding the hot weeks.

The dollar magnitudes in the headline figures come from
:mod:`zero_day_warranty.calculations` (parameterized by the documented
plant-scale inputs); this generator produces a smaller but proportional
population so the statistics are meaningful and the run is fast on a laptop.

All data is synthetic. Not Toyota data.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from zero_day_warranty.domains import (
    AssemblyTelemetry,
    BuildRecord,
    InspectionResult,
    QualityEvent,
    Severity,
    WarrantyClaim,
)
from zero_day_warranty.medallion import Medallion

PLANT = "PLANT-NA-01"
LINE = "LINE-A"
PART_NUMBER = "PN-48820-BRK"
STATIONS = [f"STATION-{n:02d}" for n in range(1, 11)]
HOT_STATION = "STATION-07"
HOT_TOOL = "TOOL-TQ-07"
SUSPECT_LOT = "LOT-7743"
SHIFTS = ["A", "B", "C"]
AFFECTED_WEEKS = (12, 13, 14)
BASELINE_WEEKS = (11, 15, 16)


@dataclass(frozen=True)
class GroundTruth:
    """The planted signal — used by tests to confirm the chain finds it."""

    suspect_lot: str = SUSPECT_LOT
    hot_station: str = HOT_STATION
    hot_tool: str = HOT_TOOL
    affected_weeks: tuple[int, ...] = AFFECTED_WEEKS


@dataclass(frozen=True)
class SyntheticDataset:
    """A generated dataset plus the medallion and the planted ground truth."""

    medallion: Medallion
    ground_truth: GroundTruth


def _vin(seq: int) -> str:
    """Deterministic 17-char-style VIN for a sequence number."""
    return f"1ZDW{seq:013d}"


def generate(
    *,
    seed: int = 42,
    vehicles_per_week: int = 600,
    baseline_warranty_rate: float = 0.030,
    excess_warranty_rate: float = 2.3,
    suspect_lot_penetration: float = 0.40,
) -> SyntheticDataset:
    """Generate a deterministic reference dataset across the four domains."""
    rng = random.Random(seed)
    builds: list[BuildRecord] = []
    claims: list[WarrantyClaim] = []
    quality: list[QualityEvent] = []
    telemetry: list[AssemblyTelemetry] = []

    seq = 0
    year_start = date(2025, 1, 1)

    for week in (*BASELINE_WEEKS, *AFFECTED_WEEKS):
        is_affected = week in AFFECTED_WEEKS
        build_day = year_start + timedelta(weeks=week - 1)
        for _ in range(vehicles_per_week):
            seq += 1
            vin = _vin(seq)
            station = rng.choice(STATIONS)
            tool = f"TOOL-TQ-{station[-2:]}"

            # Suspect lot is over-installed at the hot station during the window.
            got_suspect_lot = is_affected and rng.random() < suspect_lot_penetration
            if got_suspect_lot:
                station = HOT_STATION
                tool = HOT_TOOL
            supplier_lot = SUSPECT_LOT if got_suspect_lot else f"LOT-{rng.randint(1000, 1999)}"

            builds.append(
                BuildRecord(
                    vin=vin,
                    plant=PLANT,
                    line=LINE,
                    station=station,
                    tool_id=tool,
                    shift=rng.choice(SHIFTS),
                    operator_id=f"OP-{rng.randint(100, 199)}",
                    supplier_lot=supplier_lot,
                    part_number=PART_NUMBER,
                    build_date=build_day,
                    build_week=week,
                )
            )

            # Telemetry — the hot tool drifts during the affected window.
            drift = (
                round(rng.uniform(6.0, 12.0), 2)
                if (got_suspect_lot or (is_affected and station == HOT_STATION))
                else round(rng.uniform(0.0, 1.5), 2)
            )
            telemetry.append(
                AssemblyTelemetry(
                    trace_id=f"T-{seq}",
                    vin=vin,
                    station=station,
                    tool_id=tool,
                    torque_nm=round(rng.uniform(48.0, 52.0), 2),
                    angle_deg=round(rng.uniform(88.0, 92.0), 2),
                    calibration_drift_pct=drift,
                    cycle_time_s=round(rng.uniform(55.0, 65.0), 1),
                    humidity_pct=round(rng.uniform(35.0, 55.0), 1),
                    temperature_c=round(rng.uniform(19.0, 24.0), 1),
                    captured_at=datetime.combine(build_day, datetime.min.time()),
                )
            )

            # Quality event — SPC anomalies cluster on the drifting hot tool.
            anomalous = drift > 5.0 and rng.random() < 0.5
            quality.append(
                QualityEvent(
                    event_id=f"Q-{seq}",
                    vin=vin,
                    station=station,
                    measurement="weld_bead_offset_mm",
                    value=round(rng.uniform(0.8, 1.2) if anomalous else rng.uniform(0.1, 0.5), 3),
                    spec_lower=0.0,
                    spec_upper=0.6,
                    result=InspectionResult.FAIL if anomalous else InspectionResult.PASS,
                    confidence=round(rng.uniform(0.9, 0.99), 3),
                    captured_at=datetime.combine(build_day, datetime.min.time()),
                )
            )

            # Warranty claim — suspect-lot vehicles fail at the excess rate.
            rate = baseline_warranty_rate * (excess_warranty_rate if got_suspect_lot else 1.0)
            if rng.random() < rate:
                months = round(rng.uniform(2.0, 20.0), 1)
                claims.append(
                    WarrantyClaim(
                        claim_id=f"C-{seq}",
                        vin=vin,
                        part_number=PART_NUMBER,
                        failure_mode="brake_actuator_premature_wear",
                        fault_code="B1318",
                        severity=Severity.HIGH if got_suspect_lot else Severity.MEDIUM,
                        dealer_code=f"D-{rng.randint(10, 99)}",
                        claim_date=build_day + timedelta(days=int(months * 30)),
                        build_to_claim_months=months,
                        claim_cost_usd=round(rng.uniform(250.0, 450.0), 2),
                    )
                )

    medallion = Medallion(
        builds=builds,
        claims=claims,
        quality_events=quality,
        telemetry=telemetry,
    )
    return SyntheticDataset(medallion=medallion, ground_truth=GroundTruth())


__all__ = [
    "AFFECTED_WEEKS",
    "HOT_STATION",
    "HOT_TOOL",
    "SUSPECT_LOT",
    "GroundTruth",
    "SyntheticDataset",
    "generate",
]
