"""Tests for the agent console + audit ledger views."""

from __future__ import annotations

from pathlib import Path

from zero_day_warranty.chain import WarrantyRootCauseChain
from zero_day_warranty.consoles import (
    build_console_graph,
    build_ledger_view,
    render_agent_console_html,
    render_audit_ledger_html,
)
from zero_day_warranty.synthetic import generate


def _result() -> object:
    return WarrantyRootCauseChain(generate().medallion).run()


def test_console_graph_roster_and_stream() -> None:
    g = build_console_graph(_result())
    roles = {a["role"] for a in g["agents"]}
    assert "orchestrator" in roles
    assert {
        "detect",
        "context",
        "stattest",
        "quality",
        "supplier",
        "hypothesis",
        "compliance",
    } <= roles
    assert len(g["events"]) == 24
    assert [e["n"] for e in g["events"]] == list(range(1, 25))
    # the HITL gate decision surfaces in the stream
    assert any(e["hitl"] == "approved" for e in g["events"])
    assert g["meta"]["verified"] is True


def test_ledger_view_has_sealed_chain() -> None:
    v = build_ledger_view(_result())
    assert v["meta"]["algorithm"] == "HMAC-SHA256"
    assert v["meta"]["fields"] == 14
    assert len(v["rows"]) == 24
    for r in v["rows"]:
        assert r["signature"]  # every row is signed
        assert "prev_link" in r  # and hash-chained
        assert {"agent_id", "decision_output", "model_version"} <= set(r)


def test_agent_console_html_is_self_contained() -> None:
    result = _result()
    html = render_agent_console_html(result)
    assert html.startswith("<!DOCTYPE html>")
    assert result.suspect_lot in html
    assert 'id="data"' in html  # embedded decision stream
    assert "apex.axle.agents." in html
    assert "ZeroDayWarranty_Audit_Ledger.html" in html  # cross-link


def test_audit_ledger_html_shows_rows_and_verify() -> None:
    result = _result()
    html = render_audit_ledger_html(result)
    assert html.startswith("<!DOCTYPE html>")
    assert "HMAC-SHA256" in html
    assert "Hash chain VERIFIED" in html
    # a real signature/prev_link from the sealed rows is rendered
    sig = result.ledger.rows()[0]["signature"][:12]
    assert sig in html


def test_committed_console_pages_exist_and_valid() -> None:
    # These pages embed real sealed_at timestamps + signatures, so they are not
    # byte-reproducible (unlike the portal/3D pages); assert the committed
    # snapshots exist and look valid instead of enforcing byte equality.
    root = Path(__file__).resolve().parents[1]
    console = (root / "docs" / "design" / "ZeroDayWarranty_Agent_Console.html").read_text("utf-8")
    ledger = (root / "docs" / "design" / "ZeroDayWarranty_Audit_Ledger.html").read_text("utf-8")
    assert console.startswith("<!DOCTYPE html>") and 'id="data"' in console
    assert ledger.startswith("<!DOCTYPE html>") and "Hash chain VERIFIED" in ledger
