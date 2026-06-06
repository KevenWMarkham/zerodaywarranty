"""Medallion data plane — Bronze → Silver → Gold.

The agent's value is in *composing* the four source domains into a single
per-VIN view (Calculations §2). This module models that composition:

- **Bronze** — raw landing, source-native shapes (not modelled here; the
  domain models already represent post-ingest, typed records).
- **Silver** — canonical, VIN-conformed, typed, joinable. The four
  :mod:`zero_day_warranty.domains` models *are* the Silver shapes.
- **Gold** — the per-VIN joinable view the agent actually reads:
  ``Build × Warranty × Quality × Telemetry``, classification-aware and
  identity-scoped. Implemented here as :class:`GoldVehicleView` rows assembled
  by :class:`Medallion.gold_per_vin`.

In production these are Microsoft Fabric OneLake Delta tables and Direct Lake
Gold views; this is the laptop-substrate, mock-mode reference.
"""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict

from zero_day_warranty.domains import (
    AssemblyTelemetry,
    BuildRecord,
    QualityEvent,
    WarrantyClaim,
)


class GoldVehicleView(BaseModel):
    """The per-VIN joined Gold view — one row per VIN.

    This is the agent-safe shape: a vehicle's build provenance with all of its
    warranty claims, quality events, and telemetry traces hung off the VIN.
    """

    model_config = ConfigDict(frozen=True)

    vin: str
    build: BuildRecord
    claims: tuple[WarrantyClaim, ...] = ()
    quality_events: tuple[QualityEvent, ...] = ()
    telemetry: tuple[AssemblyTelemetry, ...] = ()

    @property
    def has_claim(self) -> bool:
        """True when the vehicle has at least one warranty claim."""
        return len(self.claims) > 0

    @property
    def total_claim_cost(self) -> float:
        """Sum of warranty claim cost for this VIN."""
        return sum(c.claim_cost_usd for c in self.claims)


class Medallion:
    """Holds the four Silver domains and produces Gold per-VIN views.

    Mirrors a Fabric Lakehouse: Silver tables in, Gold views out. The Gold join
    is keyed on VIN — the single conformed key across all four domains.
    """

    def __init__(
        self,
        *,
        builds: list[BuildRecord],
        claims: list[WarrantyClaim],
        quality_events: list[QualityEvent],
        telemetry: list[AssemblyTelemetry],
    ) -> None:
        """Hold the four Silver-layer domains for Gold-view assembly."""
        self.builds = builds
        self.claims = claims
        self.quality_events = quality_events
        self.telemetry = telemetry

    def gold_per_vin(self) -> dict[str, GoldVehicleView]:
        """Assemble the per-VIN Gold view across all four domains.

        Every VIN with a build record yields one :class:`GoldVehicleView`.
        Warranty / quality / telemetry records are indexed by VIN and attached.
        """
        claims_by_vin: dict[str, list[WarrantyClaim]] = defaultdict(list)
        for c in self.claims:
            claims_by_vin[c.vin].append(c)

        quality_by_vin: dict[str, list[QualityEvent]] = defaultdict(list)
        for q in self.quality_events:
            quality_by_vin[q.vin].append(q)

        telemetry_by_vin: dict[str, list[AssemblyTelemetry]] = defaultdict(list)
        for t in self.telemetry:
            telemetry_by_vin[t.vin].append(t)

        gold: dict[str, GoldVehicleView] = {}
        for build in self.builds:
            gold[build.vin] = GoldVehicleView(
                vin=build.vin,
                build=build,
                claims=tuple(claims_by_vin.get(build.vin, ())),
                quality_events=tuple(quality_by_vin.get(build.vin, ())),
                telemetry=tuple(telemetry_by_vin.get(build.vin, ())),
            )
        return gold


__all__ = ["GoldVehicleView", "Medallion"]
