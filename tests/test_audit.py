"""Tests for the hash-chained audit ledger."""

from __future__ import annotations

import pytest

from zero_day_warranty.audit import (
    GENESIS_LINK,
    AppendOnlyViolationError,
    AuditLedger,
    AuditRow,
    HitlStatus,
)

KEY = b"test-key"


def _row(decision_id: str, trace_id: str = "t-1") -> AuditRow:
    return AuditRow(
        trace_id=trace_id,
        decision_id=decision_id,
        agent_id="apex.axle.agents.warranty-detect",
        invoking_identity="analyst@example.com",
        manifest_version="1.0.0",
        policy_version="1.0.0",
        model_version="gpt-4o-2024-11-20",
        prompt_version="1.0.0",
        inputs_ref="gold://x",
        reasoning_trace_ref="trace://x",
        decision_output={"ok": True},
        hitl_status=HitlStatus.NONE,
    )


def test_append_seals_and_signs() -> None:
    ledger = AuditLedger(signing_key=KEY)
    sealed = ledger.append(_row("d-1"))
    assert sealed["signature"]
    assert sealed["sealed_at"]
    assert sealed["prev_link"] == GENESIS_LINK
    assert len(ledger) == 1


def test_chain_links_each_row_to_the_previous() -> None:
    ledger = AuditLedger(signing_key=KEY)
    first = ledger.append(_row("d-1"))
    second = ledger.append(_row("d-2"))
    assert second["prev_link"] == first["signature"]
    assert ledger.verify_chain()


def test_append_only_refuses_overwrite() -> None:
    ledger = AuditLedger(signing_key=KEY)
    ledger.append(_row("d-1"))
    with pytest.raises(AppendOnlyViolationError):
        ledger.append(_row("d-1"))


def test_tamper_breaks_the_chain() -> None:
    ledger = AuditLedger(signing_key=KEY)
    ledger.append(_row("d-1"))
    ledger.append(_row("d-2"))
    assert ledger.verify_chain()
    # mutate a sealed row in place
    ledger.get("d-1")["decision_output"] = {"ok": False}
    assert not ledger.verify_row("d-1")
    assert not ledger.verify_chain()


def test_missing_trace_id_rejected() -> None:
    ledger = AuditLedger(signing_key=KEY)
    with pytest.raises(ValueError, match="trace_id"):
        ledger.append(_row("d-1", trace_id=""))


def test_by_trace_returns_rows_in_order() -> None:
    ledger = AuditLedger(signing_key=KEY)
    ledger.append(_row("d-1"))
    ledger.append(_row("d-2"))
    rows = ledger.by_trace("t-1")
    assert [r["decision_id"] for r in rows] == ["d-1", "d-2"]


def test_audit_row_is_immutable() -> None:
    row = _row("d-1")
    with pytest.raises(Exception):  # pydantic frozen error
        row.decision_id = "d-2"  # type: ignore[misc]
