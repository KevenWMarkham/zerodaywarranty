"""Minimal HTTP server for the Azure Container Apps deployment.

Standard-library only (no extra runtime deps). One module serves three roles,
selected by the ``ZDW_ROLE`` env var, so a single multi-stage image builds all
three Container Apps:

- ``orchestrator`` — ``GET /run`` executes the 24-step chain on the synthetic
  dataset and returns the evidence package + audit-chain verification.
- ``mcp-warranty`` — ``GET /tools`` lists the Gold-view tools; ``GET
  /gold/summary`` returns a compact summary of the per-VIN Gold view.
- ``mcp-ledger``  — ``GET /tools`` lists the ledger tools; ``GET /verify`` runs
  a chain and verifies the hash chain.

All roles answer ``GET /health``. The route logic is a pure function
(:func:`route`) so it is unit-tested without binding a socket. In production the
orchestrator reads the Fabric/Postgres Gold view and calls Azure OpenAI; this
reference run uses the embedded synthetic dataset so the deployed app is
self-proving on day one.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from zero_day_warranty import __version__
from zero_day_warranty.chain import WarrantyRootCauseChain
from zero_day_warranty.synthetic import generate

ROLES = ("orchestrator", "mcp-warranty", "mcp-ledger")

WARRANTY_TOOLS = [
    {"tool_id": "axle_warranty.pull_vins", "purpose": "Resolve a claim cohort to VINs"},
    {"tool_id": "fabric.gold.per_vin_view", "purpose": "Read the per-VIN joined Gold view"},
    {"tool_id": "axle_warranty.get_lot_trace", "purpose": "Extract supplier lot codes"},
    {"tool_id": "axle_warranty.chargeback_exposure", "purpose": "Compute chargeback exposure"},
]
LEDGER_TOOLS = [
    {
        "tool_id": "ledger.append_audit_row",
        "purpose": "Append a sealed 14-field row",
        "write": True,
    },
    {"tool_id": "ledger.fetch_row_by_trace", "purpose": "Fetch all rows for a trace"},
    {"tool_id": "ledger.verify_chain", "purpose": "Verify the hash chain"},
]


def _env_config() -> dict[str, bool]:
    """Which deployment config is wired (booleans only — never the values)."""
    return {
        "aoai_endpoint_set": bool(os.getenv("AOAI_ENDPOINT")),
        "aoai_chat_deployment_set": bool(os.getenv("AOAI_CHAT_DEPLOYMENT")),
        "database_url_set": bool(os.getenv("DATABASE_URL")),
        "signing_key_set": bool(os.getenv("AUDIT_LEDGER_SIGNING_KEY")),
        "app_insights_set": bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")),
    }


def route(role: str, path: str) -> tuple[int, dict[str, Any]]:
    """Pure request router — returns ``(status_code, json_body)``."""
    base = {"service": "zero-day-warranty", "role": role, "version": __version__}

    if path in ("/health", "/", "/healthz"):
        return 200, {**base, "status": "ok", "config": _env_config()}

    if role == "orchestrator" and path == "/run":
        result = WarrantyRootCauseChain(generate().medallion).run()
        return 200, {
            **base,
            "trace_id": result.trace_id,
            "suspect_lot": result.suspect_lot,
            "hot_station": result.hot_station,
            "hot_tool": result.hot_tool,
            "affected_weeks": result.affected_weeks,
            "significant": result.lot_test.significant,
            "p_value": result.lot_test.p_value,
            "confidence": result.confidence,
            "hitl_status": result.hitl_status.value,
            "financials": result.financials.as_summary(),
            "ledger_rows": len(result.ledger),
            "chain_verified": result.ledger.verify_chain(),
        }

    if role == "mcp-warranty" and path == "/tools":
        return 200, {**base, "tools": WARRANTY_TOOLS}

    if role == "mcp-warranty" and path == "/gold/summary":
        gold = generate().medallion.gold_per_vin()
        claimed = [v for v in gold.values() if v.has_claim]
        by_lot = Counter(v.build.supplier_lot for v in claimed)
        return 200, {
            **base,
            "vins": len(gold),
            "vins_with_claims": len(claimed),
            "top_lots_by_claims": dict(by_lot.most_common(5)),
        }

    if role == "mcp-ledger" and path == "/tools":
        return 200, {**base, "tools": LEDGER_TOOLS}

    if role == "mcp-ledger" and path == "/verify":
        ledger = WarrantyRootCauseChain(generate().medallion).run().ledger
        return 200, {**base, "ledger_rows": len(ledger), "chain_verified": ledger.verify_chain()}

    return 404, {**base, "error": "not found", "path": path}


class _Handler(BaseHTTPRequestHandler):
    role = "orchestrator"

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        try:
            status, body = route(self.role, path)
        except Exception as exc:  # return any error as JSON, keep serving
            status, body = 500, {"role": self.role, "error": str(exc)}
        payload = json.dumps(body, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args: Any) -> None:  # quiet default logging
        return


def main() -> None:
    """Serve the role from ``ZDW_ROLE`` on ``PORT`` (default 8080)."""
    role = os.getenv("ZDW_ROLE", "orchestrator")
    if role not in ROLES:
        raise SystemExit(f"ZDW_ROLE must be one of {ROLES}, got {role!r}")
    port = int(os.getenv("PORT", "8080"))
    handler = type("Handler", (_Handler,), {"role": role})
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    print(f"zero-day-warranty {role} listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
