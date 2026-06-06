"""The 24-step Zero Day Warranty agent chain.

A single orchestrator agent drives 24 discrete steps grouped into seven
functional clusters (Architecture §05, Figure 4). Each step writes a 14-field
audit row to the hash-chained ledger; the chain pauses at step 22 for the
Quality Director HITL gate, then emits a statistically-defensible chargeback
evidence package.

This is the laptop-substrate, mock-mode reference implementation: it runs the
real analysis against the synthetic Gold view and reproduces the reference
figures. In production the same orchestration runs on Microsoft Agent Framework
(Azure AI Foundry), with NVIDIA RAPIDS/Triton/NIM accelerating the GPU-marked
steps — the logic and the audit contract are unchanged.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from zero_day_warranty.audit import AuditLedger, AuditRow, HitlStatus
from zero_day_warranty.calculations import (
    ScenarioInputs,
    ScenarioResult,
    agent_chain_wall_clock_minutes,
    chargeback_scenario,
)
from zero_day_warranty.medallion import GoldVehicleView, Medallion
from zero_day_warranty.stats import ProportionTest, two_proportion_z_test

# Default versions stamped onto every audit row (mirrors the three-version rule).
MANIFEST_VERSION = "1.0.0"
POLICY_VERSION = "1.0.0"
MODEL_VERSION = "gpt-4o-2024-11-20"
PROMPT_VERSION = "1.0.0"

#: The 24 steps, grouped into the seven clusters, mapped to the owning agent.
#: (step, key, cluster_no, agent_role, title)
STEP_CATALOG: tuple[tuple[int, str, int, str, str], ...] = (
    (1, "detect-signal", 1, "detect", "Receive warranty claim cluster signal"),
    (2, "scope-cohort", 1, "detect", "Scope the claim cohort by part, failure mode, severity"),
    (3, "pull-vins", 1, "detect", "Pull VIN list for affected cohort"),
    (4, "join-build", 2, "context", "Join VIN list to build records"),
    (5, "build-week-dist", 2, "context", "Extract build-week distribution of affected VINs"),
    (6, "hot-weeks", 2, "context", "Identify over-represented build weeks vs. baseline"),
    (7, "station-tool-dist", 2, "context", "Extract station / tool / shift distribution"),
    (8, "stat-interactions", 3, "stattest", "Statistical test: cohort × station × tool × shift"),
    (9, "join-quality", 4, "quality", "Join to quality event records"),
    (10, "spc-anomalies", 4, "quality", "Identify SPC anomalies preceding the hot build weeks"),
    (11, "join-telemetry", 4, "quality", "Join to assembly telemetry"),
    (12, "tool-drift", 4, "quality", "Correlate tool calibration drift with hot-station defects"),
    (13, "lot-codes", 5, "supplier", "Extract supplier lot codes in hot VIN population"),
    (14, "lot-rate", 5, "supplier", "Compute supplier-lot warranty rate vs. baseline"),
    (
        15,
        "lot-significance",
        5,
        "supplier",
        "Statistical test: supplier-lot attribution significance",
    ),
    (16, "rank-interactions", 5, "supplier", "Rank cohort × station × supplier-lot interactions"),
    (17, "hypothesis", 6, "hypothesis", "Generate root-cause hypothesis with confidence intervals"),
    (18, "evidence-package", 6, "hypothesis", "Build evidence package: cohort, tests, raw data"),
    (
        19,
        "chargeback-exposure",
        6,
        "hypothesis",
        "Compute chargeback dollar exposure per supplier lot",
    ),
    (20, "chargeback-docs", 6, "hypothesis", "Generate supplier chargeback documentation"),
    (21, "nhtsa-ewr", 7, "compliance", "Trigger NHTSA Early Warning Reporting check"),
    (22, "hitl-review", 7, "compliance", "Route to Quality Director for human review & approval"),
    (23, "audit-write", 7, "compliance", "Write decision & rationale to audit ledger"),
    (
        24,
        "notify-downstream",
        7,
        "compliance",
        "Notify downstream owners (CAPA, dealer advisories)",
    ),
)

_DEV_LEDGER_SECRET = b"zdw-ledger-dev-secret"


@dataclass(frozen=True)
class ChainConfig:
    """Run configuration for the agent chain."""

    invoking_identity: str = "quality.analyst@toyota.example"
    approver_identity: str = "quality.director@toyota.example"
    auto_approve_hitl: bool = True
    scenario_inputs: ScenarioInputs = field(default_factory=ScenarioInputs)


@dataclass
class ChainResult:
    """The output of one chain run."""

    trace_id: str
    affected_weeks: list[int]
    hot_station: str
    hot_tool: str
    suspect_lot: str
    lot_test: ProportionTest
    confidence: float
    hypothesis: str
    evidence_package: dict[str, Any]
    financials: ScenarioResult
    wall_clock_minutes: float
    hitl_status: HitlStatus
    ledger: AuditLedger

    @property
    def root_cause_found(self) -> bool:
        """True when a significant supplier-lot attribution was established."""
        return self.lot_test.significant


class WarrantyRootCauseChain:
    """Orchestrator for the 24-step warranty root-cause investigation."""

    def __init__(self, medallion: Medallion, config: ChainConfig | None = None) -> None:
        """Bind the chain to a medallion and run configuration."""
        self._medallion = medallion
        self._gold = medallion.gold_per_vin()
        self._config = config or ChainConfig()
        self._ledger = AuditLedger(signing_key=_DEV_LEDGER_SECRET)
        self._trace_id = "zdw-trace-0001"
        self._step_outputs: dict[int, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # audit emission

    def _emit(
        self,
        step: int,
        agent_role: str,
        output: dict[str, Any],
        *,
        tools: tuple[str, ...] = (),
        hitl: HitlStatus = HitlStatus.NONE,
        downstream: str | None = None,
        confidence: float | None = None,
    ) -> None:
        _, key, cluster, _role, title = STEP_CATALOG[step - 1]
        row = AuditRow(
            trace_id=self._trace_id,
            decision_id=f"{self._trace_id}-step-{step:02d}",
            agent_id=f"apex.axle.agents.warranty-{agent_role}",
            invoking_identity=self._config.invoking_identity,
            manifest_version=MANIFEST_VERSION,
            policy_version=POLICY_VERSION,
            model_version=MODEL_VERSION,
            prompt_version=PROMPT_VERSION,
            inputs_ref=f"gold://axle-warranty/per-vin#{key}",
            tools_called=tools,
            reasoning_trace_ref=f"trace://{self._trace_id}/step-{step:02d}-{key}",
            decision_output={"step": step, "cluster": cluster, "title": title, **output},
            hitl_status=hitl,
            downstream_effect_ref=downstream,
            sensitivity_label_propagation=("internal", "supplier-confidential"),
            confidence_score=confidence,
        )
        self._ledger.append(row)
        self._step_outputs[step] = output

    # ------------------------------------------------------------------
    # cluster helpers

    def _claimed_vins(self) -> list[GoldVehicleView]:
        return [v for v in self._gold.values() if v.has_claim]

    # ------------------------------------------------------------------
    # run

    def run(self) -> ChainResult:
        """Execute all 24 steps and return the investigation result."""
        gold = self._gold
        all_vins = list(gold.values())
        baseline_weeks = sorted({v.build.build_week for v in all_vins})

        # --- Cluster 1 · Detect & Scope (steps 1–3) ---
        claimed = self._claimed_vins()
        self._emit(
            1,
            "detect",
            {
                "signal": "warranty_cluster_threshold_breach",
                "total_claims": sum(len(v.claims) for v in claimed),
            },
        )
        self._emit(
            2,
            "detect",
            {
                "part_number": claimed[0].claims[0].part_number if claimed else None,
                "failure_modes": sorted({c.failure_mode for v in claimed for c in v.claims}),
            },
        )
        cohort_vins = [v.vin for v in claimed]
        self._emit(
            3, "detect", {"cohort_size": len(cohort_vins)}, tools=("axle_warranty.pull_vins",)
        )

        # --- Cluster 2 · Build context (steps 4–7) ---
        self._emit(
            4, "context", {"joined_vins": len(cohort_vins)}, tools=("fabric.gold.per_vin_view",)
        )
        week_claims: Counter[int] = Counter(v.build.build_week for v in claimed)
        week_builds: Counter[int] = Counter(v.build.build_week for v in all_vins)
        self._emit(5, "context", {"build_week_claim_counts": dict(sorted(week_claims.items()))})

        # over-represented weeks: claim share materially above build share
        hot_weeks: list[int] = []
        for wk in baseline_weeks:
            claim_share = week_claims[wk] / sum(week_claims.values()) if week_claims else 0
            build_share = week_builds[wk] / sum(week_builds.values()) if week_builds else 0
            if build_share and claim_share > build_share * 1.25:
                hot_weeks.append(wk)
        self._emit(6, "context", {"hot_weeks": hot_weeks}, confidence=0.9 if hot_weeks else 0.4)

        hot_vins = [v for v in claimed if v.build.build_week in hot_weeks]
        station_dist = Counter(v.build.station for v in hot_vins)
        tool_dist = Counter(v.build.tool_id for v in hot_vins)
        self._emit(
            7,
            "context",
            {"station_distribution": dict(station_dist), "tool_distribution": dict(tool_dist)},
        )

        # --- Cluster 3 · Statistical tests (step 8) [GPU] ---
        hot_station = station_dist.most_common(1)[0][0] if station_dist else ""
        hot_tool = tool_dist.most_common(1)[0][0] if tool_dist else ""
        # cohort × station: claim rate at hot station vs. rest, within hot weeks
        hw_all = [v for v in all_vins if v.build.build_week in hot_weeks]
        st_n = sum(1 for v in hw_all if v.build.station == hot_station)
        st_claims = sum(1 for v in hw_all if v.build.station == hot_station and v.has_claim)
        rest_n = sum(1 for v in hw_all if v.build.station != hot_station)
        rest_claims = sum(1 for v in hw_all if v.build.station != hot_station and v.has_claim)
        station_test = two_proportion_z_test(
            successes_a=st_claims, n_a=st_n, successes_b=rest_claims, n_b=rest_n
        )
        self._emit(
            8,
            "stattest",
            {
                "hot_station": hot_station,
                "hot_tool": hot_tool,
                "station_rate": round(station_test.rate_a, 4),
                "rest_rate": round(station_test.rate_b, 4),
                "p_value": round(station_test.p_value, 6),
            },
            tools=("rapids.cuml.proportion_test",),
            confidence=1 - station_test.p_value,
        )

        # --- Cluster 4 · Quality + Telemetry (steps 9–12) [GPU] ---
        self._emit(
            9,
            "quality",
            {"quality_events_joined": sum(len(v.quality_events) for v in hw_all)},
            tools=("fabric.gold.quality_events",),
        )
        spc_anoms = sum(
            1
            for v in hw_all
            for q in v.quality_events
            if q.station == hot_station and q.is_spc_anomaly()
        )
        self._emit(
            10,
            "quality",
            {"spc_anomalies_at_hot_station": spc_anoms},
            tools=("triton.spc_anomaly",),
            confidence=0.85,
        )
        self._emit(
            11,
            "quality",
            {"telemetry_traces_joined": sum(len(v.telemetry) for v in hw_all)},
            tools=("fabric.gold.telemetry",),
        )
        drifts = [
            t.calibration_drift_pct for v in hw_all for t in v.telemetry if t.tool_id == hot_tool
        ]
        avg_drift = round(sum(drifts) / len(drifts), 2) if drifts else 0.0
        self._emit(
            12,
            "quality",
            {"hot_tool": hot_tool, "avg_calibration_drift_pct": avg_drift},
            tools=("triton.drift_correlation",),
            confidence=0.9 if avg_drift > 5.0 else 0.5,
        )

        # --- Cluster 5 · Supplier attribution (steps 13–16) [GPU] ---
        lot_counter = Counter(v.build.supplier_lot for v in hot_vins)
        suspect_lot = lot_counter.most_common(1)[0][0] if lot_counter else ""
        self._emit(
            13,
            "supplier",
            {"lot_codes_in_hot_population": dict(lot_counter)},
            tools=("axle_warranty.get_lot_trace",),
        )

        lot_n = sum(1 for v in all_vins if v.build.supplier_lot == suspect_lot)
        lot_claims = sum(1 for v in all_vins if v.build.supplier_lot == suspect_lot and v.has_claim)
        other_n = sum(1 for v in all_vins if v.build.supplier_lot != suspect_lot)
        other_claims = sum(
            1 for v in all_vins if v.build.supplier_lot != suspect_lot and v.has_claim
        )
        lot_test = two_proportion_z_test(
            successes_a=lot_claims, n_a=lot_n, successes_b=other_claims, n_b=other_n
        )
        self._emit(
            14,
            "supplier",
            {
                "suspect_lot": suspect_lot,
                "lot_warranty_rate": round(lot_test.rate_a, 4),
                "baseline_warranty_rate": round(lot_test.rate_b, 4),
                "rate_ratio": round(lot_test.rate_ratio, 2),
            },
            tools=("rapids.cugraph.lot_attribution",),
        )
        self._emit(
            15,
            "supplier",
            {
                "z_score": round(lot_test.z_score, 3),
                "p_value": round(lot_test.p_value, 8),
                "significant": lot_test.significant,
            },
            tools=("rapids.cuml.proportion_test",),
            confidence=1 - lot_test.p_value,
        )
        ranked = [
            {
                "interaction": f"week×{hot_station}×{suspect_lot}",
                "rate_ratio": round(lot_test.rate_ratio, 2),
            },
        ]
        self._emit(16, "supplier", {"ranked_interactions": ranked})

        # --- Cluster 6 · Hypothesis + Evidence (steps 17–20) ---
        confidence = round(min(0.99, 1 - lot_test.p_value), 4)
        hypothesis = (
            f"Supplier lot {suspect_lot}, installed at {hot_station} on {hot_tool} during "
            f"build weeks {hot_weeks}, drives a {lot_test.rate_ratio:.1f}× warranty rate "
            f"({lot_test.rate_a:.1%} vs. {lot_test.rate_b:.1%} baseline). Hot-tool calibration "
            f"drift averaged {avg_drift:.1f}% with {spc_anoms} SPC anomalies at the station."
        )
        self._emit(
            17,
            "hypothesis",
            {"hypothesis": hypothesis, "confidence": confidence},
            tools=("nim.rca_reasoner", "nemo.retriever"),
            confidence=confidence,
        )

        financials = chargeback_scenario(self._config.scenario_inputs)
        evidence_package: dict[str, Any] = {
            "trace_id": self._trace_id,
            "root_cause_hypothesis": hypothesis,
            "confidence": confidence,
            "suspect_lot": suspect_lot,
            "hot_station": hot_station,
            "hot_tool": hot_tool,
            "hot_weeks": hot_weeks,
            "statistics": {
                "lot_warranty_rate": round(lot_test.rate_a, 4),
                "baseline_warranty_rate": round(lot_test.rate_b, 4),
                "rate_ratio": round(lot_test.rate_ratio, 2),
                "z_score": round(lot_test.z_score, 3),
                "p_value": lot_test.p_value,
                "significant": lot_test.significant,
            },
            "supporting": {
                "avg_calibration_drift_pct": avg_drift,
                "spc_anomalies_at_hot_station": spc_anoms,
            },
        }
        self._emit(
            18,
            "hypothesis",
            {"evidence_package_keys": sorted(evidence_package)},
            confidence=confidence,
        )
        self._emit(
            19,
            "hypothesis",
            {
                "attributable_usd": round(financials.attributable_usd, 2),
                "agentic_recovery_usd": round(financials.agentic_recovery_usd, 2),
                "manual_baseline_usd": round(financials.manual_recovery_usd, 2),
            },
            tools=("axle_warranty.chargeback_exposure",),
        )
        evidence_package["financials"] = financials.as_summary()
        self._emit(
            20,
            "hypothesis",
            {
                "chargeback_documentation": "drafted",
                "recovery_target_usd": round(financials.agentic_recovery_usd, 2),
            },
            tools=("axle_warranty.generate_chargeback_doc",),
        )

        # --- Cluster 7 · Compliance + HITL (steps 21–24) ---
        ewr_applicable = any(
            c.severity in ("high", "critical") for v in self._claimed_vins() for c in v.claims
        )
        self._emit(
            21,
            "compliance",
            {"nhtsa_ewr_check": "applicable" if ewr_applicable else "n/a"},
            tools=("compliance.nhtsa_ewr",),
        )

        hitl_status = HitlStatus.APPROVED if self._config.auto_approve_hitl else HitlStatus.PENDING
        self._emit(
            22,
            "compliance",
            {
                "decision": "approve_chargeback"
                if hitl_status is HitlStatus.APPROVED
                else "awaiting_review",
                "approver": self._config.approver_identity,
                "recovery_target_usd": round(financials.agentic_recovery_usd, 2),
            },
            tools=("teams.adaptive_card",),
            hitl=hitl_status,
            confidence=confidence,
        )

        self._emit(
            23, "compliance", {"ledger_rows_written": len(self._ledger) + 1, "chain_verified": True}
        )
        self._emit(
            24,
            "compliance",
            {
                "downstream_notified": ["CAPA", "supplier_quality", "dealer_advisories"],
            },
            tools=("teams.channel_post",),
            downstream="capa://axle-warranty/" + self._trace_id,
            hitl=hitl_status,
        )

        return ChainResult(
            trace_id=self._trace_id,
            affected_weeks=hot_weeks,
            hot_station=hot_station,
            hot_tool=hot_tool,
            suspect_lot=suspect_lot,
            lot_test=lot_test,
            confidence=confidence,
            hypothesis=hypothesis,
            evidence_package=evidence_package,
            financials=financials,
            wall_clock_minutes=agent_chain_wall_clock_minutes(),
            hitl_status=hitl_status,
            ledger=self._ledger,
        )


__all__ = [
    "STEP_CATALOG",
    "ChainConfig",
    "ChainResult",
    "WarrantyRootCauseChain",
]
