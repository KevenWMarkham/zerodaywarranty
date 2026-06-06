"""The four warranty data domains.

The Zero Day Warranty agent is only as useful as the data plumbing underneath.
Four source domains are required — each already exists somewhere in most
automotive OEM data estates; what is typically missing is the *per-VIN joinable
view* across all four. These Pydantic models are the canonical (Silver-layer)
shapes the four domains conform to.

Domains (see ``docs/design`` · Calculations §2):

1. :class:`BuildRecord`        — the vehicle build record (factory history per VIN)
2. :class:`WarrantyClaim`      — connected-vehicle warranty data (field failures)
3. :class:`QualityEvent`       — quality events on the line (inspections / SPC)
4. :class:`AssemblyTelemetry`  — assembly line telemetry (tool/equipment state)

A VIN is the join key across all four.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    """Failure-mode / defect severity bands."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InspectionResult(StrEnum):
    """Per-station inline inspection verdict (Day-0 layer · Figure 2)."""

    PASS = "pass"
    FAIL = "fail"


# ---------------------------------------------------------------------------
# Domain 1 · The vehicle build record
# ---------------------------------------------------------------------------


class BuildRecord(BaseModel):
    """Every VIN's complete factory build history, per installed part.

    When the vehicle was built, where (plant / line), on which station, with
    which tool, on which shift, by which operator, and from which supplier lot.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    vin: str = Field(min_length=11, description="Vehicle Identification Number — the join key.")
    plant: str
    line: str
    station: str
    tool_id: str
    shift: str
    operator_id: str
    supplier_lot: str = Field(description="Supplier lot code for the installed part.")
    part_number: str
    build_date: date
    build_week: int = Field(ge=1, le=53, description="ISO build week of the year.")


# ---------------------------------------------------------------------------
# Domain 2 · Connected vehicle warranty data
# ---------------------------------------------------------------------------


class WarrantyClaim(BaseModel):
    """A field warranty claim / failure mode tied back to a VIN."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    vin: str = Field(min_length=11)
    part_number: str
    failure_mode: str
    fault_code: str | None = None
    severity: Severity = Severity.MEDIUM
    dealer_code: str | None = None
    claim_date: date
    build_to_claim_months: float = Field(ge=0, description="Months from build date to claim.")
    claim_cost_usd: float = Field(ge=0, description="Cost of the warranty claim in USD.")


# ---------------------------------------------------------------------------
# Domain 3 · Quality events on the line
# ---------------------------------------------------------------------------


class QualityEvent(BaseModel):
    """An inspection / measurement / defect captured during the build.

    SPC measurements, dimensional inspections, visual-system catches,
    end-of-line audits, holds, rework — at the per-station / per-VIN level.
    This is also the record emitted by the Day-0 NVIDIA Metropolis layer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    vin: str = Field(min_length=11)
    station: str
    measurement: str = Field(description="What was measured / inspected.")
    value: float | None = None
    spec_lower: float | None = None
    spec_upper: float | None = None
    result: InspectionResult = InspectionResult.PASS
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    captured_at: datetime

    def is_spc_anomaly(self) -> bool:
        """True when a measured value falls outside the spec band."""
        if self.value is None:
            return self.result is InspectionResult.FAIL
        if self.spec_lower is not None and self.value < self.spec_lower:
            return True
        return self.spec_upper is not None and self.value > self.spec_upper


# ---------------------------------------------------------------------------
# Domain 4 · Assembly line telemetry
# ---------------------------------------------------------------------------


class AssemblyTelemetry(BaseModel):
    """Equipment state, throughput, and asset events from the production floor.

    Tool torque-and-angle traces, robot cycle times, conveyor speeds, fixture
    changeovers, environmental conditions, and equipment maintenance events.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str
    vin: str = Field(min_length=11)
    station: str
    tool_id: str
    torque_nm: float | None = None
    angle_deg: float | None = None
    calibration_drift_pct: float = Field(
        default=0.0, description="Percent drift of the tool from its calibrated baseline."
    )
    cycle_time_s: float | None = None
    humidity_pct: float | None = None
    temperature_c: float | None = None
    captured_at: datetime


__all__ = [
    "AssemblyTelemetry",
    "BuildRecord",
    "InspectionResult",
    "QualityEvent",
    "Severity",
    "WarrantyClaim",
]
