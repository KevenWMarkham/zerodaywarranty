"""End-to-end tests for the 24-step agent chain."""

from __future__ import annotations

import pytest

from zero_day_warranty.audit import HitlStatus
from zero_day_warranty.chain import STEP_CATALOG, ChainConfig, WarrantyRootCauseChain
from zero_day_warranty.synthetic import generate


@pytest.fixture
def result():  # type: ignore[no-untyped-def]
    dataset = generate()
    return dataset.ground_truth, WarrantyRootCauseChain(dataset.medallion).run()


def test_chain_emits_one_audit_row_per_step(result) -> None:  # type: ignore[no-untyped-def]
    _, res = result
    assert len(res.ledger) == len(STEP_CATALOG) == 24


def test_chain_audit_ledger_verifies(result) -> None:  # type: ignore[no-untyped-def]
    _, res = result
    assert res.ledger.verify_chain()


def test_chain_finds_the_planted_suspect_lot(result) -> None:  # type: ignore[no-untyped-def]
    truth, res = result
    assert res.suspect_lot == truth.suspect_lot
    assert res.hot_station == truth.hot_station
    assert res.hot_tool == truth.hot_tool


def test_hot_weeks_are_within_the_affected_window(result) -> None:  # type: ignore[no-untyped-def]
    truth, res = result
    assert res.affected_weeks  # non-empty
    assert set(res.affected_weeks).issubset(set(truth.affected_weeks))


def test_attribution_is_statistically_significant(result) -> None:  # type: ignore[no-untyped-def]
    _, res = result
    assert res.root_cause_found
    assert res.lot_test.significant
    assert res.lot_test.rate_ratio > 1.5


def test_hitl_auto_approved_by_default(result) -> None:  # type: ignore[no-untyped-def]
    _, res = result
    assert res.hitl_status is HitlStatus.APPROVED


def test_hitl_can_be_held_pending() -> None:
    dataset = generate()
    res = WarrantyRootCauseChain(dataset.medallion, ChainConfig(auto_approve_hitl=False)).run()
    assert res.hitl_status is HitlStatus.PENDING


def test_chain_is_deterministic() -> None:
    a = WarrantyRootCauseChain(generate().medallion).run()
    b = WarrantyRootCauseChain(generate().medallion).run()
    assert a.suspect_lot == b.suspect_lot
    assert a.evidence_package["financials"] == b.evidence_package["financials"]


def test_evidence_package_has_financials_and_statistics(result) -> None:  # type: ignore[no-untyped-def]
    _, res = result
    pkg = res.evidence_package
    assert "financials" in pkg
    assert pkg["statistics"]["significant"] is True
    assert pkg["financials"]["agentic_recovery_usd"] > pkg["financials"]["manual_recovery_usd"]
