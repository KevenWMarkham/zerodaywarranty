"""Human-in-the-loop notification — the Teams Adaptive Card (chain step 22).

Builds a Microsoft Teams **Adaptive Card** from the chargeback evidence package
and posts it to an Incoming Webhook. Pure card construction
(:func:`build_adaptive_card`) is unit-tested; delivery (:func:`post_to_teams`)
is best-effort and never raises — when no webhook is configured the chain simply
records that the card was *generated* but not delivered.

In production this is the Foundry Tool-Approval surface; here it is a standard
Teams Incoming Webhook so the card is real and demoable.
"""

from __future__ import annotations

import json
from typing import Any

ADAPTIVE_CARD_VERSION = "1.5"


def _fact(title: str, value: str) -> dict[str, str]:
    return {"title": title, "value": value}


def build_adaptive_card(evidence: dict[str, Any], *, approver: str) -> dict[str, Any]:
    """Build the Quality-Director approval Adaptive Card from an evidence package."""
    stats = evidence.get("statistics", {})
    fin = evidence.get("financials", {})
    trace_id = evidence.get("trace_id", "")

    def usd(x: Any) -> str:
        try:
            return f"${float(x):,.0f}"
        except (TypeError, ValueError):
            return "—"

    facts = [
        _fact("Suspect lot", str(evidence.get("suspect_lot", "—"))),
        _fact(
            "Hot station / tool",
            f"{evidence.get('hot_station', '—')} / {evidence.get('hot_tool', '—')}",
        ),
        _fact("Affected build weeks", str(evidence.get("hot_weeks", "—"))),
        _fact("Warranty-rate ratio", f"{stats.get('rate_ratio', '—')}x"),
        _fact("Significance (p)", f"{stats.get('p_value', '—')}"),
        _fact("Confidence", f"{round(float(evidence.get('confidence', 0)) * 100)}%"),
        _fact("Attributable exposure", usd(fin.get("attributable_usd"))),
        _fact("Recovery target", usd(fin.get("agentic_recovery_usd"))),
    ]

    card: dict[str, Any] = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": ADAPTIVE_CARD_VERSION,
        "body": [
            {
                "type": "TextBlock",
                "size": "Large",
                "weight": "Bolder",
                "text": "Zero Day Warranty — chargeback approval",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "spacing": "None",
                "isSubtle": True,
                "text": f"Trace {trace_id} · approver: {approver}",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": str(evidence.get("root_cause_hypothesis", "")),
                "wrap": True,
            },
            {"type": "FactSet", "facts": facts},
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Approve chargeback",
                "style": "positive",
                "data": {"decision": "approve", "trace_id": trace_id},
            },
            {
                "type": "Action.Submit",
                "title": "Amend",
                "data": {"decision": "amend", "trace_id": trace_id},
            },
            {
                "type": "Action.Submit",
                "title": "Deny",
                "style": "destructive",
                "data": {"decision": "deny", "trace_id": trace_id},
            },
        ],
    }
    return card


def teams_envelope(card: dict[str, Any]) -> dict[str, Any]:
    """Wrap an Adaptive Card in the Teams Incoming-Webhook message envelope."""
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": card,
            }
        ],
    }


def post_to_teams(card: dict[str, Any], webhook_url: str | None, *, timeout: float = 10.0) -> bool:
    """Post the card to a Teams webhook. Returns True on success; never raises.

    A falsy ``webhook_url`` is treated as "not configured" and returns False
    without attempting delivery.
    """
    if not webhook_url:
        return False
    import urllib.error
    import urllib.request

    try:
        payload = json.dumps(teams_envelope(card)).encode("utf-8")
        req = urllib.request.Request(
            webhook_url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return bool(200 <= resp.status < 300)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False


__all__ = ["ADAPTIVE_CARD_VERSION", "build_adaptive_card", "post_to_teams", "teams_envelope"]
