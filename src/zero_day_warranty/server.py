"""Minimal HTTP server for the Azure Container Apps deployment.

Standard-library only (no extra runtime deps). One module serves three roles,
selected by the ``ZDW_ROLE`` env var, so a single multi-stage image builds all
three Container Apps:

- ``orchestrator`` — ``GET /run`` executes the 24-step chain on the synthetic
  dataset and returns the evidence package + audit-chain verification;
  ``GET /portal`` renders the Swim Lane Views design portal (HTML) live from a
  fresh chain run.
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
import re
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from zero_day_warranty import __version__
from zero_day_warranty.chain import ChainConfig, WarrantyRootCauseChain
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


#: Orchestrator paths that return the rendered Swim Lane Views portal (text/html).
PORTAL_PATHS = ("/portal", "/lanes", "/swim-lanes", "/swimlanes")
#: Orchestrator paths that return the 3D process fly-through (text/html).
PROCESS_3D_PATHS = ("/process-3d", "/3d")
#: Orchestrator paths for the agent console and the audit ledger (text/html).
AGENT_CONSOLE_PATHS = ("/agents", "/console")
AUDIT_LEDGER_PATHS = ("/ledger", "/audit")
#: Safe design-pack filename (no slashes / traversal) — e.g. ``Foo_Bar.html``.
_DESIGN_NAME = re.compile(r"^[A-Za-z0-9_-]+\.html$")


def _design_dir() -> Path | None:
    """Directory holding the static design-pack HTML, if available.

    In the container the design pack is copied in and pointed at by
    ``ZDW_DESIGN_DIR``; for a local checkout we fall back to ``docs/design``.
    """
    env = os.getenv("ZDW_DESIGN_DIR")
    if env:
        p = Path(env)
        return p if p.is_dir() else None
    cand = Path(__file__).resolve().parents[2] / "docs" / "design"
    return cand if cand.is_dir() else None


def _serve_design(name: str) -> str | None:
    """Return the contents of a design-pack page by filename, or ``None``.

    Only bare ``*.html`` names are accepted (no path separators), so the request
    cannot escape the design directory.
    """
    if not _DESIGN_NAME.match(name):
        return None
    ddir = _design_dir()
    if ddir is None:
        return None
    f = ddir / name
    return f.read_text(encoding="utf-8") if f.is_file() else None


#: Content types for the static assets served from the design pack (e.g. the
#: vendored three.js modules, so the 3D demo needs no external CDN).
_STATIC_TYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".map": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".woff2": "font/woff2",
}


def _safe_under(base: Path, rel: str) -> Path | None:
    """Resolve ``rel`` under ``base``, refusing empties, ``..``, or escapes."""
    if not rel or any(part in ("", "..") for part in rel.split("/")):
        return None
    base_r = base.resolve()
    p = (base_r / rel).resolve()
    if p != base_r and base_r not in p.parents:
        return None
    return p if p.is_file() else None


def static_asset(role: str, path: str) -> tuple[int, bytes, str] | None:
    """Serve a static design-pack asset (vendored JS, css, …) as bytes, or ``None``."""
    if role != "orchestrator":
        return None
    ddir = _design_dir()
    if ddir is None:
        return None
    p = _safe_under(ddir, path.lstrip("/"))
    if p is None:
        return None
    return 200, p.read_bytes(), _STATIC_TYPES.get(p.suffix.lower(), "application/octet-stream")


def html_route(role: str, path: str) -> tuple[int, str] | None:
    """HTML router — returns ``(status, html)`` for portal paths, else ``None``.

    The Swim Lane Views portal and the 3D process fly-through are rendered **live**
    from a fresh chain run on each request, so the deployed app is
    self-documenting and always truthful to the running solution. Non-HTML paths
    return ``None`` so the caller falls back to the JSON :func:`route`.
    """
    if role == "orchestrator" and path in PORTAL_PATHS:
        from zero_day_warranty.lanes import render_swimlane_views_html

        return 200, render_swimlane_views_html()
    if role == "orchestrator" and path in PROCESS_3D_PATHS:
        from zero_day_warranty.process3d import render_process_3d_html

        return 200, render_process_3d_html()
    if role == "orchestrator" and path in AGENT_CONSOLE_PATHS:
        from zero_day_warranty.consoles import render_agent_console_html

        return 200, render_agent_console_html()
    if role == "orchestrator" and path in AUDIT_LEDGER_PATHS:
        from zero_day_warranty.consoles import render_audit_ledger_html

        return 200, render_audit_ledger_html()
    if role == "orchestrator" and path.endswith(".html"):
        page = _serve_design(path.lstrip("/"))
        if page is not None:
            return 200, page
    return None


def route(role: str, path: str) -> tuple[int, dict[str, Any]]:
    """Pure request router — returns ``(status_code, json_body)``."""
    base = {"service": "zero-day-warranty", "role": role, "version": __version__}

    if path in ("/health", "/", "/healthz"):
        body = {**base, "status": "ok", "config": _env_config()}
        if role == "orchestrator":
            body["portal"] = "/portal"
            body["process3d"] = "/process-3d"
            body["agents"] = "/agents"
            body["ledger"] = "/ledger"
        return 200, body

    if role == "orchestrator" and path == "/hitl-card":
        cfg = ChainConfig(teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL"))
        result = WarrantyRootCauseChain(generate().medallion, cfg).run()
        out = result.evidence_package.get("hitl_card")
        return 200, {**base, "card": out}

    if role == "orchestrator" and path == "/run":
        cfg = ChainConfig(teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL"))
        result = WarrantyRootCauseChain(generate().medallion, cfg).run()
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
            html = html_route(self.role, path)
            if html is not None:
                self._write(html[0], html[1].encode("utf-8"), "text/html; charset=utf-8")
                return
            asset = static_asset(self.role, path)
            if asset is not None:
                self._write(asset[0], asset[1], asset[2])
                return
            status, body = route(self.role, path)
        except Exception as exc:  # return any error as JSON, keep serving
            status, body = 500, {"role": self.role, "error": str(exc)}
        self._write(status, json.dumps(body, default=str).encode("utf-8"), "application/json")

    def _write(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
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
