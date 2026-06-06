"""Append-only, hash-chained decision audit ledger.

Every step the agent chain executes produces one immutable :class:`AuditRow`.
The :class:`AuditLedger` seals each row on append: it stamps ``sealed_at``,
links the row to the previous row's signature (the *hash chain*), then signs
the result with HMAC-SHA256. Tampering with any row breaks the chain from that
row forward — which is what makes the ledger regulator-answerable.

This mirrors the APEX ``apex_audit`` contract (the 14-field row of Sellers
Guide §11.2) and its ``AuditStore``, adding the explicit per-row hash-chain
link called for in the Architecture diagrams (Figure 1 · "Audit ledger ·
Hash chain · every agent decision row").

Production wires the store to a Delta table with a WORM policy and pulls the
signing key from Key Vault, keyed by ``tenant_id``. This reference
implementation keeps rows in memory and accepts any ``bytes`` key.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

GENESIS_LINK = "0" * 64
"""Hash-chain link recorded on the very first row in a ledger."""


class HitlStatus(StrEnum):
    """Human-in-the-loop decision states (Sellers Guide §11.2)."""

    NONE = "none"
    PENDING = "pending"
    APPROVED = "approved"
    MODIFIED = "modified"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"


class AuditRow(BaseModel):
    """The 14-field required decision row, plus carried optionals.

    Immutable once constructed (``frozen=True``). The ledger appends seal
    metadata via :meth:`AuditLedger.append`, which returns a sealed dict; the
    original row instance is never mutated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- 14 required fields ---
    trace_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    invoking_identity: str = Field(min_length=1)
    manifest_version: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    inputs_ref: str = Field(min_length=1)
    tools_called: tuple[str, ...] = ()
    reasoning_trace_ref: str = Field(min_length=1)
    decision_output: dict[str, Any]
    hitl_status: HitlStatus = HitlStatus.NONE
    downstream_effect_ref: str | None = None  # required field; null = advisory

    # --- commonly carried optionals ---
    cost_attribution: dict[str, float] | None = None
    sensitivity_label_propagation: tuple[str, ...] = ()
    confidence_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready dict with enums serialised to strings."""
        return self.model_dump(mode="json")


def _canonical(row: dict[str, Any]) -> bytes:
    """Deterministic byte encoding of a row, excluding its own signature."""
    return json.dumps(
        {k: v for k, v in row.items() if k != "signature"},
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    ).encode("utf-8")


def sign_row(row: dict[str, Any], *, key: bytes) -> str:
    """Compute the HMAC-SHA256 hex digest over the row (excluding ``signature``)."""
    return hmac.new(key, _canonical(row), hashlib.sha256).hexdigest()


def verify_row(row: dict[str, Any], *, key: bytes) -> bool:
    """Constant-time verify a single stored row's signature."""
    stored = row.get("signature")
    if not isinstance(stored, str) or not stored:
        return False
    return hmac.compare_digest(stored, sign_row(row, key=key))


class AppendOnlyViolationError(Exception):
    """Raised on any attempt to overwrite a sealed row."""


class AuditLedger:
    """In-memory, append-only, hash-chained store for decision rows.

    Rows are sealed on append. Each sealed row carries ``prev_link`` (the prior
    row's signature) so the ledger forms a tamper-evident chain. A trace index
    lets auditors walk ``trace_id -> all rows`` in append order.
    """

    def __init__(self, *, signing_key: bytes) -> None:
        """Create an empty ledger sealed with ``signing_key`` (HMAC-SHA256)."""
        self._signing_key = signing_key
        self._rows: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []
        self._by_trace: dict[str, list[str]] = {}
        self._last_link: str = GENESIS_LINK

    def append(self, row: AuditRow) -> dict[str, Any]:
        """Seal, hash-chain, and append a decision row; return the sealed dict."""
        if not row.trace_id:
            raise ValueError("AuditRow.trace_id is required (Section 11.6)")
        if row.decision_id in self._rows:
            raise AppendOnlyViolationError(
                f"decision_id {row.decision_id!r} already sealed; "
                "append-only ledger refuses overwrite"
            )
        sealed = row.to_dict()
        sealed["sealed_at"] = datetime.now(UTC).isoformat()
        sealed["prev_link"] = self._last_link
        sealed["signature"] = sign_row(sealed, key=self._signing_key)

        self._rows[row.decision_id] = sealed
        self._order.append(row.decision_id)
        self._by_trace.setdefault(row.trace_id, []).append(row.decision_id)
        self._last_link = sealed["signature"]
        return sealed

    def get(self, decision_id: str) -> dict[str, Any]:
        """Return a single sealed row by decision id."""
        if decision_id not in self._rows:
            raise KeyError(f"No row {decision_id!r}")
        return self._rows[decision_id]

    def by_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """Return every row emitted under ``trace_id`` in append order."""
        return [self._rows[rid] for rid in self._by_trace.get(trace_id, [])]

    def rows(self) -> list[dict[str, Any]]:
        """Return all sealed rows in global append order."""
        return [self._rows[rid] for rid in self._order]

    def verify_row(self, decision_id: str) -> bool:
        """Recompute and compare the signature for a single stored row."""
        return verify_row(self._rows[decision_id], key=self._signing_key)

    def verify_chain(self) -> bool:
        """Verify every signature and that the hash chain is unbroken.

        Returns ``True`` only when each row's signature is valid *and* its
        ``prev_link`` matches the signature of the row appended before it.
        """
        prev = GENESIS_LINK
        for rid in self._order:
            sealed = self._rows[rid]
            if sealed.get("prev_link") != prev:
                return False
            if not verify_row(sealed, key=self._signing_key):
                return False
            prev = sealed["signature"]
        return True

    def __len__(self) -> int:
        """Number of sealed rows in the ledger."""
        return len(self._rows)


__all__ = [
    "GENESIS_LINK",
    "AppendOnlyViolationError",
    "AuditLedger",
    "AuditRow",
    "HitlStatus",
    "sign_row",
    "verify_row",
]
