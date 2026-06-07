"""Per-swim-lane views into one investigation (the Swim Lane Views portal).

The capability swim lanes (``docs/design/ZeroDayWarranty_Capability_SwimLanes``)
show *every* lane at once across the seven phases. This module renders the
complementary drill-down: one **view per lane**, showing the single
investigation as that lane experiences it — the steps it owns, the live decision
output it sealed to the audit ledger, its KPIs, and how it hands off to the next
lane.

The views are generated from an actual :class:`~zero_day_warranty.chain.ChainResult`
(the orchestrator's evidence package + the 24 sealed audit rows), so the figures
on every lane stay truthful as the chain evolves rather than drifting from
hand-typed mockups. :func:`render_swimlane_views_html` produces the standalone
design-pack portal (reusing the shared visual system); :func:`render_swimlane_views_md`
produces the diffable Markdown twin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

from zero_day_warranty.chain import STEP_CATALOG, ChainResult, WarrantyRootCauseChain
from zero_day_warranty.synthetic import generate

#: The seven phases of one investigation and the step range each spans.
PHASES: tuple[tuple[str, int, int], ...] = (
    ("Detect", 1, 3),
    ("Context", 4, 7),
    ("Analyze", 8, 12),
    ("Attribute", 13, 16),
    ("Hypothesis", 17, 20),
    ("Decide", 21, 22),
    ("Act", 23, 24),
)


@dataclass(frozen=True)
class Kpi:
    """A single KPI tile on a lane view."""

    value: str
    label: str
    delta: str = ""
    tone: str = "flat"  # up | down | flat
    color: str = ""  # "" | nv | rust | gov | amber


@dataclass(frozen=True)
class StepCell:
    """One step a lane owns, with its live, sealed decision output."""

    step: int
    phase: str
    title: str
    summary: str
    tools: tuple[str, ...]
    sealed: bool


@dataclass(frozen=True)
class LaneView:
    """A complete view into one swim lane for a single investigation."""

    id: str
    name: str
    owner: str
    color: str  # "" (ms-blue) | nv | rust | gov | exec
    initials: str
    scope: str
    invariant: str
    receives: str
    hands_to: str
    steps: tuple[int, ...]
    personas: tuple[tuple[str, str], ...]  # (label, persona-portal anchor id)
    kpis: list[Kpi] = field(default_factory=list)
    cells: list[StepCell] = field(default_factory=list)


# --------------------------------------------------------------------------
# lane specification — owner, look, steps owned, personas, handoffs
# Steps are drawn from the capability catalog (capability-swim-lanes.md). A step
# may appear in more than one lane (e.g. the Data Plane serves a step the Agent
# Orchestration drives); the union covers all 24.

_LaneSpec = tuple[
    str, str, str, str, str, str, str, str, str, tuple[int, ...], tuple[tuple[str, str], ...]
]

LANE_SPECS: tuple[_LaneSpec, ...] = (
    (
        "consumption",
        "Consumption & Detection",
        "Power BI · Teams",
        "",
        "CD",
        "Where the signal is seen and the result lands — warranty-cost heatmaps "
        "raise the cluster, recovery KPIs roll up the outcome.",
        "—",
        "Agent Orchestration →",
        "Identity-scoped Power BI Direct Lake surfaces; no row leaves the Gold view.",
        (1, 24),
        (("VP Quality", "exec"), ("Warranty Analyst", "warranty")),
    ),
    (
        "dataplane",
        "Data Plane",
        "Microsoft Fabric · medallion",
        "",
        "DP",
        "The per-VIN join. Bronze→Silver→Gold makes build, warranty, quality and "
        "telemetry answerable as one classification-aware view.",
        "← Consumption (cohort signal)",
        "Agent Orchestration · Accelerated Analytics →",
        "VIN-conformed, tokenized Silver; sensitivity labels propagate to Gold.",
        (3, 4, 5, 6, 7, 9, 11, 13, 19),
        (("IT / Data Eng", "it"), ("Supplier Quality", "supplier")),
    ),
    (
        "orchestration",
        "Agent Orchestration",
        "Agent Framework · Foundry",
        "",
        "AO",
        "The 24-step orchestrator. Typed tool-calling on-behalf-of the invoking "
        "identity, sealing one audit row per step.",
        "← Data Plane (Gold view)",
        "Accelerated Analytics · Human-in-the-Loop →",
        "Per-agent managed identity (OBO); single HITL gate at step 22.",
        (1, 2, 3, 4, 5, 6, 7, 17, 18, 19, 20, 21, 22, 23, 24),
        (("Quality Analyst", "warranty"), ("Quality Director", "director")),
    ),
    (
        "analytics",
        "Accelerated Analytics",
        "NVIDIA · optional",
        "nv",
        "NV",
        "The statistical core — interaction tests, SPC/drift correlation, supplier-"
        "lot attribution graph and RCA reasoning. Runs on CPU without GPUs.",
        "← Agent Orchestration (cohort)",
        "Agent Orchestration (evidence) →",
        "GPU acceleration is optional; the same math and audit contract hold on CPU.",
        (8, 10, 12, 14, 15, 16, 17, 18),
        (("Mfg Engineering", "mfg"), ("Supplier Quality", "supplier")),
    ),
    (
        "hitl",
        "Human-in-the-Loop",
        "Quality Director · Teams",
        "rust",
        "HL",
        "The single human gate. The evidence package arrives as a Teams Adaptive "
        "Card; approve / amend / deny — the decision is sealed.",
        "← Agent Orchestration (evidence package)",
        "Downstream Action →",
        "Exactly one approval gate; the decision and approver are sealed at step 22.",
        (22,),
        (("Quality Director", "director"), ("VP Quality", "exec")),
    ),
    (
        "downstream",
        "Downstream Action",
        "CAPA · Supplier · Dealer · NHTSA",
        "amber",
        "DA",
        "Turning the approved decision into action — NHTSA EWR check, supplier "
        "chargeback docs, CAPA / SCAR / dealer advisories.",
        "← Human-in-the-Loop (approval)",
        "Consumption (KPI rollup) →",
        "Every dispatched action references the trace; downstream effects are logged.",
        (20, 21, 24),
        (("Compliance", "compliance"), ("Plant Ops", "plant")),
    ),
    (
        "governance",
        "Governance Foundation",
        "Entra · Purview · Audit ledger · Defender",
        "gov",
        "GV",
        "Cross-cutting under every phase — identity, DLP/DSPM, the 14-field hash-"
        "chained audit row per step, and OT security.",
        "underlies every lane",
        "regulator-replayable record",
        "Tamper-evident hash chain; one sealed 14-field row per step; verifiable.",
        tuple(range(1, 25)),
        (("Compliance", "compliance"), ("IT / Security", "it")),
    ),
    (
        "day0",
        "Day-0 Prevention",
        "NVIDIA Metropolis · edge",
        "nv",
        "D0",
        "Catch the defect at the station so it never becomes a claim — inline "
        "vision, edge inference, jidoka stop, per-VIN inspection record.",
        "continuous · at the build station",
        "Data Plane (inspection record) →",
        "Every unit inspected (no sampling); per-VIN evidence persisted to Bronze.",
        (9,),
        (("Line Operator", "operator"), ("Quality / Agent", "warranty")),
    ),
)


def _phase_of(step: int) -> str:
    for name, lo, hi in PHASES:
        if lo <= step <= hi:
            return name
    return "—"


def _fmt_usd(x: float | int) -> str:
    return f"${x:,.0f}"


def _summarize(decision_output: dict[str, object]) -> str:
    """Compact one-line summary of a step's decision output (drops meta keys)."""
    skip = {"step", "cluster", "title"}
    parts: list[str] = []
    for key, value in decision_output.items():
        if key in skip:
            continue
        if isinstance(value, dict):
            shown = ", ".join(f"{k}: {v}" for k, v in list(value.items())[:3])
            rendered = f"{{{shown}}}" if shown else "{}"
        elif isinstance(value, list):
            rendered = ", ".join(str(v) for v in value) if value else "—"
        else:
            rendered = str(value)
        if len(rendered) > 64:
            rendered = rendered[:61] + "…"
        parts.append(f"{key.replace('_', ' ')}: {rendered}")
        if len(parts) >= 3:
            break
    return " · ".join(parts)


# --------------------------------------------------------------------------
# live KPI builders — one per lane, fed the ChainResult


def _kpis(lane_id: str, result: ChainResult) -> list[Kpi]:
    ev = result.evidence_package
    stats = ev.get("statistics", {})
    fin = result.financials
    out = {row["decision_output"]["step"]: row["decision_output"] for row in result.ledger.rows()}
    conf_pct = f"{round(result.confidence * 100)}%"

    if lane_id == "consumption":
        claims = out.get(1, {}).get("total_claims", "—")
        cohort = out.get(3, {}).get("cohort_size", "—")
        return [
            Kpi(str(claims), "Claims in signal", "cluster threshold breach", "up"),
            Kpi(str(cohort), "Cohort VINs", "scoped from signal", "flat"),
            Kpi(_fmt_usd(fin.agentic_recovery_usd), "Recovery target", "to dashboards", "up"),
            Kpi(conf_pct, "Evidence confidence", "rolled to KPI", "up"),
        ]
    if lane_id == "dataplane":
        joined = out.get(4, {}).get("joined_vins", "—")
        lots = len(out.get(13, {}).get("lot_codes_in_hot_population", {}))
        return [
            Kpi(str(joined), "VINs joined (Gold)", "per-VIN view", "flat"),
            Kpi(str(len(result.affected_weeks)), "Hot build weeks", "over-represented", "up"),
            Kpi(str(lots), "Supplier lots traced", "in hot population", "flat"),
            Kpi(_fmt_usd(fin.attributable_usd), "Exposure composed", "step 19", "up"),
        ]
    if lane_id == "orchestration":
        owned = (1, 2, 3, 4, 5, 6, 7, 17, 18, 19, 20, 21, 22, 23, 24)
        sealed = sum(1 for s in owned if s in out)
        return [
            Kpi("24", "Steps orchestrated", "7 clusters", "flat"),
            Kpi(f"{sealed}/{len(owned)}", "Owned steps sealed", "audit rows", "up"),
            Kpi(result.hitl_status.value, "HITL gate", "step 22", "flat", "rust"),
            Kpi(conf_pct, "Hypothesis confidence", "step 17", "up"),
        ]
    if lane_id == "analytics":
        return [
            Kpi(
                f"{stats.get('rate_ratio', '—')}×",
                "Warranty-rate ratio",
                "lot vs baseline",
                "up",
                "nv",
            ),
            Kpi(f"{stats.get('p_value', 0):.1e}", "Significance p", "two-proportion z", "up", "nv"),
            Kpi(
                str(ev.get("supporting", {}).get("spc_anomalies_at_hot_station", "—")),
                "SPC anomalies",
                "at hot station",
                "down",
                "nv",
            ),
            Kpi(
                f"{ev.get('supporting', {}).get('avg_calibration_drift_pct', '—')}%",
                "Tool drift",
                "hot tool",
                "down",
                "nv",
            ),
        ]
    if lane_id == "hitl":
        s22 = out.get(22, {})
        posted = "yes" if s22.get("teams_card_posted") else "generated"
        return [
            Kpi(
                str(s22.get("decision", "—")).replace("_", " "), "Decision", "step 22", "up", "rust"
            ),
            Kpi(
                _fmt_usd(fin.agentic_recovery_usd), "Recovery approved", "chargeback", "up", "rust"
            ),
            Kpi(conf_pct, "Evidence confidence", "p < 0.05", "up", "rust"),
            Kpi(posted, "Adaptive Card", "Teams", "flat", "rust"),
        ]
    if lane_id == "downstream":
        ewr = out.get(21, {}).get("nhtsa_ewr_check", "—")
        notified = len(out.get(24, {}).get("downstream_notified", []))
        return [
            Kpi(str(ewr), "NHTSA EWR", "49 CFR 579", "flat", "amber"),
            Kpi(_fmt_usd(fin.agentic_recovery_usd), "Recovery target", "supplier", "up", "amber"),
            Kpi(str(notified), "Downstream owners", "notified", "flat", "amber"),
            Kpi("drafted", "Chargeback docs", "step 20", "flat", "amber"),
        ]
    if lane_id == "governance":
        rows = len(result.ledger)
        verified = "VERIFIED" if result.ledger.verify_chain() else "BROKEN"
        return [
            Kpi(str(rows), "Audit rows sealed", "14-field", "flat", "gov"),
            Kpi(verified, "Hash chain", "tamper-evident", "up", "gov"),
            Kpi("1 / step", "Coverage", "every decision", "flat", "gov"),
            Kpi("2", "Sensitivity labels", "propagated", "flat", "gov"),
        ]
    if lane_id == "day0":
        events = out.get(9, {}).get("quality_events_joined", "—")
        return [
            Kpi("100%", "Units inspected", "no sampling", "up", "nv"),
            Kpi(str(events), "Inspection records", "→ Bronze", "flat", "nv"),
            Kpi("~5 ms", "Edge inference", "per unit", "up", "nv"),
            Kpi("jidoka", "On FAIL", "line stop", "flat", "nv"),
        ]
    return []


def build_lane_views(result: ChainResult) -> list[LaneView]:
    """Assemble the per-lane views from a completed chain run."""
    rows_by_step = {row["decision_output"]["step"]: row for row in result.ledger.rows()}
    views: list[LaneView] = []
    for (
        lane_id,
        name,
        owner,
        color,
        initials,
        scope,
        receives,
        hands_to,
        invariant,
        steps,
        personas,
    ) in LANE_SPECS:
        cells: list[StepCell] = []
        for step in steps:
            _, _key, _cluster, _role, title = STEP_CATALOG[step - 1]
            row = rows_by_step.get(step)
            output = row["decision_output"] if row else {}
            cells.append(
                StepCell(
                    step=step,
                    phase=_phase_of(step),
                    title=title,
                    summary=_summarize(output) if output else "always-on",
                    tools=tuple(row["tools_called"]) if row else (),
                    sealed=row is not None,
                )
            )
        views.append(
            LaneView(
                id=lane_id,
                name=name,
                owner=owner,
                color=color,
                initials=initials,
                scope=scope,
                invariant=invariant,
                receives=receives,
                hands_to=hands_to,
                steps=steps,
                personas=personas,
                kpis=_kpis(lane_id, result),
                cells=cells,
            )
        )
    return views


# --------------------------------------------------------------------------
# HTML rendering — clones the shared design-pack visual system

_PERSONA_PORTALS = "ZeroDayWarranty_Persona_Portals.html"
_SWIMLANES = "ZeroDayWarranty_Capability_SwimLanes.html"

_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Zero Day Warranty · Swim Lane Views</title>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&family=Aptos:wght@400;600;700&family=Cascadia+Mono&display=swap" rel="stylesheet">
  <style>
  :root {
    --navy: #1A2339; --navy-soft: #2A3349;
    --ms-blue: #0078D4; --ms-blue-dark: #005A9E;
    --nv-green: #76B900; --nv-green-dark: #5C9300;
    --slate: #64748B; --slate-light: #94A3B8;
    --amber: #D97706; --green: #047857; --rust: #B85450;
    --bg: #ffffff; --bg-soft: #FAFAF7; --border: #E5E7EB;
    --text: #1F2937; --code-bg: #F5F5F7;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { font-family: "Source Serif 4", Charter, Georgia, serif; background: var(--bg); color: var(--text); line-height: 1.6; font-size: 16px; }
  .classification { background: var(--amber); color: #fff; padding: 6px 24px; text-align: center; font-family: Aptos, sans-serif; font-size: 10.5px; letter-spacing: 0.18em; text-transform: uppercase; font-weight: 700; }
  header.cover { padding: 44px 56px 28px; background: linear-gradient(135deg, var(--navy) 0%, var(--navy-soft) 100%); color: #fff; border-bottom: 6px solid var(--ms-blue); }
  header.cover .eyebrow { font-family: Aptos, sans-serif; font-size: 11px; letter-spacing: 0.28em; text-transform: uppercase; color: var(--ms-blue); font-weight: 700; }
  header.cover h1 { font-family: Aptos, sans-serif; font-size: 36px; font-weight: 700; line-height: 1.12; margin: 12px 0 6px; color: #fff; }
  header.cover .subtitle { font-family: Aptos, sans-serif; font-size: 18px; color: #cbd5e1; font-weight: 400; margin: 0 0 20px; }
  header.cover .meta { display: flex; gap: 22px; flex-wrap: wrap; font-family: Aptos, sans-serif; font-size: 12.5px; color: #94A3B8; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.16); }
  header.cover .meta strong { color: #cbd5e1; font-weight: 600; }
  main { max-width: 1180px; margin: 0 auto; padding: 28px 24px 64px; }
  .lead { font-size: 16px; color: var(--slate); margin: 0 0 14px; max-width: 940px; }
  h2 { font-family: Aptos, sans-serif; color: var(--navy); font-size: 22px; margin: 0 0 6px; }
  a { color: var(--ms-blue-dark); }
  code { font-family: "Cascadia Mono", Consolas, monospace; font-size: 13px; background: var(--code-bg); padding: 1px 5px; border-radius: 3px; color: var(--navy); }
  .tab-nav { position: sticky; top: 0; z-index: 100; background: #fff; border-bottom: 2px solid var(--border); padding: 0 16px; display: flex; gap: 2px; flex-wrap: wrap; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
  .tab-btn { border: none; background: transparent; padding: 12px 14px; cursor: pointer; font-family: Aptos, sans-serif; font-size: 12.5px; font-weight: 600; color: var(--slate); border-bottom: 3px solid transparent; margin-bottom: -2px; transition: all 0.15s; display: inline-flex; align-items: center; gap: 7px; }
  .tab-btn:hover { color: var(--navy); background: var(--bg-soft); }
  .tab-btn.active { color: var(--navy); border-bottom-color: var(--ms-blue); }
  .tab-btn .vmark { width: 8px; height: 8px; border-radius: 50%; display: inline-block; background: var(--ms-blue); }
  .tab-btn .vmark.nv { background: var(--nv-green-dark); }
  .tab-btn .vmark.gov { background: #334155; }
  .tab-btn .vmark.rust { background: var(--rust); }
  .tab-btn .vmark.amber { background: var(--amber); }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .portal { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
  .portal-top { background: linear-gradient(135deg, var(--navy), var(--navy-soft)); color: #fff; padding: 16px 22px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; border-bottom: 4px solid var(--ms-blue); }
  .portal-top.nv { border-bottom-color: var(--nv-green); }
  .portal-top.rust { border-bottom-color: var(--rust); }
  .portal-top.amber { border-bottom-color: var(--amber); }
  .portal-top.gov { border-bottom-color: #64748B; }
  .portal-id { display: flex; align-items: center; gap: 14px; }
  .avatar { width: 42px; height: 42px; border-radius: 50%; background: var(--ms-blue); display: flex; align-items: center; justify-content: center; font-family: Aptos, sans-serif; font-weight: 700; font-size: 15px; color: #fff; }
  .avatar.nv { background: var(--nv-green-dark); } .avatar.rust { background: var(--rust); } .avatar.amber { background: var(--amber); } .avatar.gov { background: #64748B; }
  .portal-id h3 { font-family: Aptos, sans-serif; margin: 0; font-size: 18px; }
  .portal-id .role { font-family: Aptos, sans-serif; font-size: 12px; color: #cbd5e1; }
  .portal-scope { font-family: Aptos, sans-serif; font-size: 11px; color: #94A3B8; text-align: right; max-width: 380px; }
  .portal-body { background: var(--bg-soft); padding: 18px; }
  .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px; }
  @media (max-width: 760px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
  .kpi { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; border-top: 3px solid var(--ms-blue); }
  .kpi.nv { border-top-color: var(--nv-green); } .kpi.rust { border-top-color: var(--rust); } .kpi.gov { border-top-color: #64748B; } .kpi.amber { border-top-color: var(--amber); }
  .kpi-val { font-family: Aptos, sans-serif; font-size: 22px; font-weight: 700; color: var(--navy); line-height: 1.1; word-break: break-word; }
  .kpi-lbl { font-family: Aptos, sans-serif; font-size: 11px; color: var(--slate); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }
  .kpi-delta { font-family: "Cascadia Mono", monospace; font-size: 11px; margin-top: 6px; }
  .kpi-delta.up { color: var(--green); } .kpi-delta.down { color: var(--rust); } .kpi-delta.flat { color: var(--slate); }
  .panels { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  @media (max-width: 860px) { .panels { grid-template-columns: 1fr; } }
  .panel { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; }
  .panel.span2 { grid-column: span 2; }
  @media (max-width: 860px) { .panel.span2 { grid-column: span 1; } }
  .panel-title { font-family: Aptos, sans-serif; font-size: 12px; font-weight: 700; color: var(--ms-blue-dark); text-transform: uppercase; letter-spacing: 0.07em; margin: 0 0 10px; display: flex; justify-content: space-between; align-items: center; }
  .panel-title .meta { color: var(--slate-light); font-weight: 600; font-size: 10.5px; }
  /* phase strip */
  .phases { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
  @media (max-width: 860px) { .phases { grid-template-columns: repeat(2, 1fr); } }
  .ph { border: 1px solid var(--border); border-radius: 6px; padding: 8px 6px; background: var(--bg-soft); min-height: 64px; }
  .ph.lit { background: #EAF3FB; border-color: #BFDDF3; }
  .ph .ph-n { font-family: Aptos, sans-serif; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--slate); margin-bottom: 4px; }
  .ph .ph-s { font-family: "Cascadia Mono", monospace; font-size: 11px; color: var(--ms-blue-dark); font-weight: 700; }
  .ph .ph-x { color: var(--slate-light); font-size: 11px; }
  /* step rows */
  .srow { display: grid; grid-template-columns: 34px 1fr auto; gap: 10px; align-items: start; padding: 8px 0; border-bottom: 1px dotted var(--border); font-size: 13px; }
  .srow:last-child { border-bottom: none; }
  .snum { font-family: "Cascadia Mono", monospace; font-weight: 700; color: #fff; background: var(--ms-blue); border-radius: 5px; text-align: center; padding: 2px 0; font-size: 12px; }
  .snum.nv { background: var(--nv-green-dark); } .snum.rust { background: var(--rust); } .snum.amber { background: var(--amber); } .snum.gov { background: #64748B; }
  .stitle { font-family: Aptos, sans-serif; color: var(--navy); font-weight: 600; }
  .ssum { font-size: 11.5px; color: var(--slate); }
  .stools { font-family: "Cascadia Mono", monospace; font-size: 10.5px; color: var(--slate-light); margin-top: 2px; }
  .badge { font-family: Aptos, sans-serif; font-size: 9.5px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; padding: 3px 8px; border-radius: 999px; white-space: nowrap; }
  .badge.ok { background: #DCFCE7; color: #15803D; }
  .badge.info { background: #DBEAFE; color: var(--ms-blue-dark); }
  .handoff { display: flex; justify-content: space-between; gap: 12px; font-family: Aptos, sans-serif; font-size: 12px; }
  .handoff .ho { background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; flex: 1; }
  .handoff .ho .lbl { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--slate-light); font-weight: 700; }
  .handoff .ho .val { color: var(--navy); font-weight: 600; }
  .plist { display: flex; gap: 8px; flex-wrap: wrap; }
  .pchip { font-family: Aptos, sans-serif; font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--ms-blue); color: var(--ms-blue-dark); background: #fff; text-decoration: none; }
  .pchip:hover { background: #EAF3FB; }
  .invariant { font-family: Aptos, sans-serif; font-size: 12px; color: var(--slate); margin-top: 4px; }
  .invariant b { color: var(--navy); }
  footer { margin-top: 40px; padding: 22px 32px; background: var(--bg-soft); border-top: 2px solid var(--border); font-family: Aptos, sans-serif; font-size: 12px; color: var(--slate); text-align: center; }
  footer strong { color: var(--text); }
  @media print {
    .classification { background:#fff; color:#000; border-bottom:1px solid #000; }
    header.cover { background:#fff; color:#000; border-bottom:2px solid #000; }
    header.cover h1, header.cover .subtitle, header.cover .meta strong, header.cover .eyebrow { color:#000; }
    .tab-nav { display:none; }
    .tab-panel { display:block !important; }
    .portal { page-break-inside: avoid; }
  }
  </style>
</head>
<body>
"""

_TAB_VMARK = {"": "", "nv": " nv", "rust": " rust", "amber": " amber", "gov": " gov"}


def _render_phase_strip(view: LaneView) -> str:
    owned = {c.step for c in view.cells}
    cells_html: list[str] = []
    for name, lo, hi in PHASES:
        in_phase = sorted(s for s in owned if lo <= s <= hi)
        lit = "ph lit" if in_phase else "ph"
        if in_phase:
            steps_txt = "".join(f'<div class="ph-s">[{s}]</div>' for s in in_phase)
        else:
            steps_txt = '<div class="ph-x">—</div>'
        cells_html.append(
            f'<div class="{lit}"><div class="ph-n">{escape(name)}</div>{steps_txt}</div>'
        )
    return f'<div class="phases">{"".join(cells_html)}</div>'


def _render_steps(view: LaneView) -> str:
    cls = view.color or ""
    rows: list[str] = []
    for c in view.cells:
        seal = (
            '<span class="badge ok">sealed</span>'
            if c.sealed
            else '<span class="badge info">always-on</span>'
        )
        tools = f'<div class="stools">{escape(" · ".join(c.tools))}</div>' if c.tools else ""
        rows.append(
            f'<div class="srow">'
            f'<span class="snum {cls}">{c.step}</span>'
            f'<span><span class="stitle">{escape(c.title)}</span>'
            f'<div class="ssum">{escape(c.summary)}</div>{tools}</span>'
            f"{seal}</div>"
        )
    return "".join(rows)


def _render_kpis(view: LaneView) -> str:
    tiles: list[str] = []
    for k in view.kpis:
        color = f" {k.color}" if k.color else ""
        delta = f'<div class="kpi-delta {k.tone}">{escape(k.delta)}</div>' if k.delta else ""
        tiles.append(
            f'<div class="kpi{color}"><div class="kpi-val">{escape(k.value)}</div>'
            f'<div class="kpi-lbl">{escape(k.label)}</div>{delta}</div>'
        )
    return f'<div class="kpi-grid">{"".join(tiles)}</div>'


def _render_lane(view: LaneView, *, active: bool) -> str:
    cls = view.color or ""
    top_cls = f"portal-top {cls}".strip()
    av_cls = f"avatar {cls}".strip()
    personas = "".join(
        f'<a class="pchip" href="{_PERSONA_PORTALS}#{pid}">{escape(label)}</a>'
        for label, pid in view.personas
    )
    span = f"steps {min(view.steps)}–{max(view.steps)}" if view.steps else "always-on"
    return f"""<div class="tab-panel{" active" if active else ""}" data-panel="{view.id}" role="tabpanel">
  <h2>{escape(view.name)} · {escape(view.owner)}</h2>
  <p class="lead">{escape(view.scope)}</p>
  <div class="portal">
    <div class="{top_cls}">
      <div class="portal-id"><div class="{av_cls}">{escape(view.initials)}</div>
        <div><h3>{escape(view.name)}</h3><div class="role">{escape(view.owner)} · {span}</div></div></div>
      <div class="portal-scope">{escape(view.invariant)}</div>
    </div>
    <div class="portal-body">
      {_render_kpis(view)}
      <div class="panels">
        <div class="panel span2">
          <div class="panel-title">Phase coverage <span class="meta">Detect → Act · this lane lit</span></div>
          {_render_phase_strip(view)}
        </div>
        <div class="panel span2">
          <div class="panel-title">Steps this lane owns <span class="meta">live · sealed to audit ledger</span></div>
          {_render_steps(view)}
        </div>
        <div class="panel span2">
          <div class="panel-title">Lane handoff <span class="meta">where it sits in the chain</span></div>
          <div class="handoff">
            <div class="ho"><div class="lbl">Receives</div><div class="val">{escape(view.receives)}</div></div>
            <div class="ho"><div class="lbl">Hands to</div><div class="val">{escape(view.hands_to)}</div></div>
          </div>
          <p class="invariant"><b>Invariant:</b> {escape(view.invariant)}</p>
        </div>
        <div class="panel span2">
          <div class="panel-title">Personas in this lane <span class="meta">links to persona portals</span></div>
          <div class="plist">{personas}</div>
        </div>
      </div>
    </div>
  </div>
</div>"""


def render_swimlane_views_html(result: ChainResult | None = None) -> str:
    """Render the standalone Swim Lane Views portal from a live chain run."""
    if result is None:
        result = WarrantyRootCauseChain(generate().medallion).run()
    views = build_lane_views(result)

    tabs = "".join(
        f'<button class="tab-btn{" active" if i == 0 else ""}" data-tab="{v.id}">'
        f'<span class="vmark{_TAB_VMARK.get(v.color, "")}"></span>{escape(v.name)}</button>'
        for i, v in enumerate(views)
    )
    panels = "".join(_render_lane(v, active=(i == 0)) for i, v in enumerate(views))

    cover = f"""<div class="classification">Reference document · Generated from a live chain run · Reference figures (synthetic)</div>
<header class="cover">
  <div class="eyebrow">Pre-Conversation Reference · Swim Lane Views</div>
  <h1>Zero Day Warranty Agentic Scenario</h1>
  <div class="subtitle">Swim lane views — one investigation, seen from each lane's seat</div>
  <div class="meta">
    <span><strong>Trace:</strong> {escape(result.trace_id)}</span>
    <span><strong>Suspect lot:</strong> {escape(result.suspect_lot)}</span>
    <span><strong>Hot station / tool:</strong> {escape(result.hot_station)} / {escape(result.hot_tool)}</span>
    <span><strong>Audit rows:</strong> {len(result.ledger)} · chain {"VERIFIED" if result.ledger.verify_chain() else "BROKEN"}</span>
    <span><strong>Companion to:</strong> <a href="{_SWIMLANES}">Capability Swim Lanes</a> · <a href="{_PERSONA_PORTALS}">Persona Portals</a></span>
  </div>
</header>"""

    nav = f'<nav class="tab-nav" role="tablist" aria-label="Swim lane views">{tabs}</nav>'
    intro = (
        '<p class="lead" style="margin-top:16px;">The capability swim lanes show every lane at '
        "once across the seven phases; these are the drill-downs. Each tab takes the same "
        "investigation and shows it as that lane experiences it — the steps it owns, the live "
        "decision output it sealed to the audit ledger, its KPIs, and how it hands off to the next "
        "lane. Figures are generated from an actual chain run. Use the tabs to switch lanes "
        "(print shows all).</p>"
    )
    footer = (
        "<footer><strong>Zero Day Warranty</strong> · Swim Lane Views · generated by "
        "<code>zdw lanes --write</code> from a live 24-step chain run · synthetic reference "
        "figures.</footer>"
    )
    script = """<script>
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.getAttribute('data-tab');
      document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
      document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
      btn.classList.add('active');
      document.querySelector('.tab-panel[data-panel="' + id + '"]').classList.add('active');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
</script>"""
    return (
        _HEAD
        + cover
        + nav
        + "<main>"
        + intro
        + panels
        + "</main>"
        + footer
        + script
        + "\n</body>\n</html>\n"
    )


def render_swimlane_views_md(result: ChainResult | None = None) -> str:
    """Render the diffable Markdown twin of the Swim Lane Views portal."""
    if result is None:
        result = WarrantyRootCauseChain(generate().medallion).run()
    views = build_lane_views(result)
    verified = "VERIFIED" if result.ledger.verify_chain() else "BROKEN"
    out: list[str] = [
        "# Zero Day Warranty — Swim Lane Views",
        "",
        "One investigation, seen from each lane's seat. The "
        "[capability swim lanes](../design/ZeroDayWarranty_Capability_SwimLanes.html) show "
        "every lane at once across the seven phases; this is the drill-down — for each lane, "
        "the steps it owns, the live decision output sealed to the audit ledger, its KPIs, and "
        "its handoffs. The polished portal is "
        "[`../design/ZeroDayWarranty_SwimLane_Views.html`]"
        "(../design/ZeroDayWarranty_SwimLane_Views.html); regenerate both with "
        "`zdw lanes --write`.",
        "",
        f"**Run:** trace `{result.trace_id}` · suspect lot **{result.suspect_lot}** · "
        f"hot station/tool {result.hot_station} / {result.hot_tool} · "
        f"{len(result.ledger)} audit rows · chain {verified}.",
        "",
    ]
    for v in views:
        span = f"steps {min(v.steps)}–{max(v.steps)}" if v.steps else "always-on"
        out += [
            f"## {v.name} · {v.owner}",
            "",
            f"_{v.scope}_",
            "",
            "| KPI | Value |",
            "|---|---|",
        ]
        out += [f"| {k.label} | {k.value} |" for k in v.kpis]
        out += [
            "",
            f"**Phase span:** {span} · **Receives:** {v.receives} · **Hands to:** {v.hands_to}",
            "",
            f"**Invariant:** {v.invariant}",
            "",
            "| Step | Title | Output | Audit |",
            "|---|---|---|---|",
        ]
        for c in v.cells:
            seal = "sealed" if c.sealed else "always-on"
            summary = c.summary.replace("|", "\\|")
            out.append(f"| {c.step} | {c.title} | {summary} | {seal} |")
        personas = ", ".join(label for label, _ in v.personas)
        out += ["", f"**Personas in this lane:** {personas}", ""]
    return "\n".join(out) + "\n"


__all__ = [
    "LANE_SPECS",
    "PHASES",
    "Kpi",
    "LaneView",
    "StepCell",
    "build_lane_views",
    "render_swimlane_views_html",
    "render_swimlane_views_md",
]
