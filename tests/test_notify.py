"""Tests for the Teams HITL Adaptive Card (step 22)."""

from __future__ import annotations

from zero_day_warranty.chain import ChainConfig, WarrantyRootCauseChain
from zero_day_warranty.notify import build_adaptive_card, post_to_teams, teams_envelope
from zero_day_warranty.synthetic import generate

EVIDENCE = {
    "trace_id": "t-1",
    "root_cause_hypothesis": "Lot LOT-7743 drives a 2.4x warranty rate.",
    "confidence": 0.96,
    "suspect_lot": "LOT-7743",
    "hot_station": "STATION-07",
    "hot_tool": "TOOL-TQ-07",
    "hot_weeks": [12, 13],
    "statistics": {"rate_ratio": 2.4, "p_value": 1e-6, "significant": True},
    "financials": {"attributable_usd": 4_212_000, "agentic_recovery_usd": 2_822_040},
}


def test_card_structure_and_actions() -> None:
    card = build_adaptive_card(EVIDENCE, approver="qd@example.com")
    assert card["type"] == "AdaptiveCard"
    assert card["version"]
    titles = [a["title"] for a in card["actions"]]
    assert titles == ["Approve chargeback", "Amend", "Deny"]
    # the approve action carries the decision + trace for the callback
    approve = card["actions"][0]
    assert approve["data"] == {"decision": "approve", "trace_id": "t-1"}


def test_card_facts_include_key_figures() -> None:
    card = build_adaptive_card(EVIDENCE, approver="qd@example.com")
    factset = next(b for b in card["body"] if b["type"] == "FactSet")
    facts = {f["title"]: f["value"] for f in factset["facts"]}
    assert facts["Suspect lot"] == "LOT-7743"
    assert "$4,212,000" in facts["Attributable exposure"]
    assert facts["Confidence"] == "96%"


def test_teams_envelope_shape() -> None:
    env = teams_envelope({"type": "AdaptiveCard"})
    assert env["type"] == "message"
    assert env["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"


def test_post_is_noop_without_webhook() -> None:
    assert post_to_teams({"type": "AdaptiveCard"}, None) is False
    assert post_to_teams({"type": "AdaptiveCard"}, "") is False


def test_post_never_raises_on_bad_url() -> None:
    # An invalid URL must be handled gracefully (returns False, no exception).
    assert post_to_teams({"type": "AdaptiveCard"}, "not-a-real-url") is False


def test_chain_attaches_card_and_records_status() -> None:
    result = WarrantyRootCauseChain(generate().medallion, ChainConfig()).run()
    card = result.evidence_package.get("hitl_card")
    assert card and card["type"] == "AdaptiveCard"
    step22 = result.ledger.get(f"{result.trace_id}-step-22")
    assert step22["decision_output"]["teams_card_generated"] is True
    assert step22["decision_output"]["teams_card_posted"] is False  # no webhook configured
