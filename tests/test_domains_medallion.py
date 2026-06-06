"""Tests for the domain models, medallion join, and stats helpers."""

from __future__ import annotations

from datetime import date, datetime

from zero_day_warranty.domains import (
    BuildRecord,
    InspectionResult,
    QualityEvent,
    WarrantyClaim,
)
from zero_day_warranty.medallion import Medallion
from zero_day_warranty.stats import two_proportion_z_test
from zero_day_warranty.synthetic import generate


def _build(vin: str, week: int = 12) -> BuildRecord:
    return BuildRecord(
        vin=vin,
        plant="P",
        line="L",
        station="S-07",
        tool_id="T",
        shift="A",
        operator_id="OP",
        supplier_lot="LOT-1",
        part_number="PN",
        build_date=date(2025, 3, 1),
        build_week=week,
    )


def test_quality_event_spc_anomaly_detection() -> None:
    ok = QualityEvent(
        event_id="q1",
        vin="1ZDW000000001",
        station="S-07",
        measurement="m",
        value=0.3,
        spec_lower=0.0,
        spec_upper=0.6,
        result=InspectionResult.PASS,
        captured_at=datetime(2025, 3, 1),
    )
    bad = QualityEvent(
        event_id="q2",
        vin="1ZDW000000001",
        station="S-07",
        measurement="m",
        value=0.9,
        spec_lower=0.0,
        spec_upper=0.6,
        result=InspectionResult.FAIL,
        captured_at=datetime(2025, 3, 1),
    )
    assert not ok.is_spc_anomaly()
    assert bad.is_spc_anomaly()


def test_medallion_joins_claims_to_build_by_vin() -> None:
    vin = "1ZDW000000001"
    claim = WarrantyClaim(
        claim_id="c1",
        vin=vin,
        part_number="PN",
        failure_mode="f",
        claim_date=date(2025, 6, 1),
        build_to_claim_months=3.0,
        claim_cost_usd=300.0,
    )
    med = Medallion(builds=[_build(vin)], claims=[claim], quality_events=[], telemetry=[])
    gold = med.gold_per_vin()
    assert vin in gold
    assert gold[vin].has_claim
    assert gold[vin].total_claim_cost == 300.0


def test_two_proportion_z_test_flags_elevated_rate() -> None:
    test = two_proportion_z_test(successes_a=70, n_a=1000, successes_b=30, n_b=1000)
    assert test.rate_ratio > 2.0
    assert test.significant


def test_synthetic_dataset_has_all_four_domains_populated() -> None:
    ds = generate()
    med = ds.medallion
    assert med.builds and med.claims and med.quality_events and med.telemetry
    gold = med.gold_per_vin()
    # every claim's VIN exists in the build/gold view
    assert all(c.vin in gold for c in med.claims)
