"""Tests for the Container Apps HTTP server route logic."""

from __future__ import annotations

import pytest

from zero_day_warranty.server import ROLES, route


@pytest.mark.parametrize("role", ROLES)
def test_health_ok_for_every_role(role: str) -> None:
    status, body = route(role, "/health")
    assert status == 200
    assert body["status"] == "ok"
    assert body["role"] == role
    assert set(body["config"]) >= {"aoai_endpoint_set", "database_url_set", "signing_key_set"}


def test_orchestrator_run_executes_chain() -> None:
    status, body = route("orchestrator", "/run")
    assert status == 200
    assert body["suspect_lot"] == "LOT-7743"
    assert body["significant"] is True
    assert body["ledger_rows"] == 24
    assert body["chain_verified"] is True
    assert body["financials"]["agentic_recovery_usd"] > body["financials"]["manual_recovery_usd"]


def test_mcp_warranty_tools_and_summary() -> None:
    status, tools = route("mcp-warranty", "/tools")
    assert status == 200
    assert any(t["tool_id"] == "axle_warranty.pull_vins" for t in tools["tools"])
    status, summary = route("mcp-warranty", "/gold/summary")
    assert status == 200
    assert summary["vins"] > 0
    assert "LOT-7743" in summary["top_lots_by_claims"]


def test_mcp_ledger_verify() -> None:
    status, body = route("mcp-ledger", "/verify")
    assert status == 200
    assert body["ledger_rows"] == 24
    assert body["chain_verified"] is True


def test_unknown_path_is_404() -> None:
    status, body = route("orchestrator", "/nope")
    assert status == 404
    assert body["error"] == "not found"


def test_role_isolation_run_only_on_orchestrator() -> None:
    # /run is not a route on the MCP roles
    assert route("mcp-warranty", "/run")[0] == 404


def test_orchestrator_hitl_card() -> None:
    status, body = route("orchestrator", "/hitl-card")
    assert status == 200
    assert body["card"]["type"] == "AdaptiveCard"
    assert body["role"] == "orchestrator"
