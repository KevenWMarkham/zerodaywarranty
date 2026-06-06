"""Zero Day Warranty command-line interface.

``zdw`` is the canonical entry point. Subcommands:

- (no args) — framework overview
- ``run``      — execute the 24-step agent chain on the synthetic dataset
- ``calc``     — print the reference-scenario calculations
- ``validate`` — load + validate every manifest and verify the audit chain
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zero_day_warranty import __version__
from zero_day_warranty.calculations import (
    agent_chain_wall_clock_minutes,
    chargeback_scenario,
    manual_rca_baseline,
)
from zero_day_warranty.chain import STEP_CATALOG, ChainConfig, WarrantyRootCauseChain
from zero_day_warranty.manifest import load_agent, load_scenario
from zero_day_warranty.roadmap import (
    load_roadmap,
    render_checklist,
    render_roadmap,
    render_sprints,
)
from zero_day_warranty.synthetic import generate

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = REPO_ROOT / "service" / "AXLE-WARRANTY-01"
BACKLOG = REPO_ROOT / "backlog" / "roadmap.yaml"

OVERVIEW = f"""\
Zero Day Warranty · v{__version__}
Agentic automotive warranty root-cause investigation · APEX-pattern accelerator

  A single orchestrator agent joins connected-vehicle warranty claims back to
  factory build history per VIN, finds the cohort × station × tool × supplier-lot
  interactions behind a warranty cluster, and produces a chargeback evidence
  package — 8-12 weeks / 6 teams collapsed to ~12 minutes.

The 24-step chain · 7 functional clusters
  1 Detect & Scope        steps 1-3    Microsoft Agent Framework
  2 Build context         steps 4-7    Microsoft Fabric · Gold views
  3 Statistical tests     step  8      NVIDIA RAPIDS cuML            [GPU]
  4 Quality + Telemetry   steps 9-12   NVIDIA Triton                 [GPU]
  5 Supplier attribution  steps 13-16  NVIDIA RAPIDS cuGraph         [GPU]
  6 Hypothesis + Evidence steps 17-20  Agent Framework + NVIDIA NIM
  7 Compliance + HITL     steps 21-24  Teams Adaptive Card + Purview

Commands
  zdw run         execute the chain on the synthetic reference dataset
  zdw run --json  emit the evidence package + ledger as JSON
  zdw calc        print the reference-scenario calculations
  zdw validate    validate manifests and verify the hash-chained ledger
  zdw roadmap     phases + sprint progress (from the backlog)
  zdw sprints     every backlog story as a checkbox
  zdw checklist   deployment validation matrix (built/deployed/tested)
  zdw --help      argparse help

Design pack: docs/design/  ·  Service: service/AXLE-WARRANTY-01/  ·  Backlog: backlog/roadmap.yaml
"""


def _fmt_usd(x: float) -> str:
    return f"${x:,.0f}"


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the chain and print results."""
    dataset = generate()
    config = ChainConfig(auto_approve_hitl=not args.hold_hitl)
    result = WarrantyRootCauseChain(dataset.medallion, config).run()

    if args.json:
        payload = {
            "evidence_package": result.evidence_package,
            "wall_clock_minutes": result.wall_clock_minutes,
            "hitl_status": result.hitl_status.value,
            "ledger_rows": result.ledger.rows(),
            "chain_verified": result.ledger.verify_chain(),
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0

    f = result.financials
    print(f"Zero Day Warranty · run {result.trace_id}\n" + "-" * 60)
    print(f"  Affected build weeks : {result.affected_weeks}")
    print(f"  Hot station / tool   : {result.hot_station} / {result.hot_tool}")
    print(f"  Suspect supplier lot : {result.suspect_lot}")
    print(
        f"  Lot warranty rate    : {result.lot_test.rate_a:.2%} "
        f"vs {result.lot_test.rate_b:.2%} baseline "
        f"({result.lot_test.rate_ratio:.1f}x)"
    )
    print(
        f"  Significance p-value : {result.lot_test.p_value:.2e} "
        f"({'significant' if result.lot_test.significant else 'not significant'})"
    )
    print(f"  Confidence           : {result.confidence:.1%}")
    print(f"\n  Root-cause hypothesis:\n    {result.hypothesis}")
    print("\n  Chargeback financials (reference scenario):")
    print(f"    Attributable exposure : {_fmt_usd(f.attributable_usd)}")
    print(f"    Agentic recovery      : {_fmt_usd(f.agentic_recovery_usd)}")
    print(f"    Manual baseline       : {_fmt_usd(f.manual_recovery_usd)}")
    print(f"    Improvement           : {f.improvement_pct:.0f}%")
    print(f"\n  Wall-clock            : ~{result.wall_clock_minutes:.0f} min")
    print(f"  HITL decision         : {result.hitl_status.value}")
    print(
        f"  Audit ledger rows     : {len(result.ledger)} "
        f"(chain {'VERIFIED' if result.ledger.verify_chain() else 'BROKEN'})"
    )
    return 0


def cmd_calc(_args: argparse.Namespace) -> int:
    """Print the reference-scenario calculations."""
    baseline = manual_rca_baseline()
    scenario = chargeback_scenario()
    print("Reference-scenario calculations (synthetic · not Toyota claims)\n" + "-" * 60)
    print("Calculation A · manual RCA baseline")
    print(
        f"  {baseline.total_hours} hrs x ${baseline.cost_per_investigation / baseline.total_hours:.0f}/hr "
        f"= {_fmt_usd(baseline.cost_per_investigation)} / investigation"
    )
    print(
        f"  {baseline.investigations_per_year}/yr = {_fmt_usd(baseline.annual_cost)} annual RCA labor"
    )
    print("\nCalculation B · agent-chain wall-clock")
    print(f"  24 steps x ~30s = ~{agent_chain_wall_clock_minutes():.0f} min")
    print("\nCalculations C1-C3 · chargeback scenario")
    print(f"  C1 attributable : {_fmt_usd(scenario.attributable_usd)}")
    print(f"  C2 agentic 67%  : {_fmt_usd(scenario.agentic_recovery_usd)}")
    print(
        f"  C3 improvement  : {scenario.improvement_pct:.0f}% over {_fmt_usd(scenario.manual_recovery_usd)} manual"
    )
    return 0


def cmd_validate(_args: argparse.Namespace) -> int:
    """Validate manifests and verify the audit chain."""
    ok = True
    scenario_path = SERVICE_DIR / "scenario.yaml"
    try:
        scenario = load_scenario(scenario_path)
        print(
            f"[ok] scenario.yaml — {scenario.scenario_id} "
            f"({len(scenario.chain_24)} steps, {len(scenario.agents)} agents)"
        )
    except Exception as exc:
        print(f"[FAIL] scenario.yaml — {exc}")
        return 1

    for ref in scenario.agents:
        agent_path = SERVICE_DIR / ref.config
        try:
            agent = load_agent(agent_path)
            tag = "HITL" if agent.hitl_gate else "    "
            print(f"[ok] {ref.config} — {agent.role} [{tag}] model={agent.model}")
        except Exception as exc:
            print(f"[FAIL] {ref.config} — {exc}")
            ok = False

    dataset = generate()
    result = WarrantyRootCauseChain(dataset.medallion).run()
    verified = result.ledger.verify_chain()
    print(
        f"[{'ok' if verified else 'FAIL'}] audit ledger — {len(result.ledger)} rows, "
        f"hash chain {'verified' if verified else 'BROKEN'}"
    )
    ok = ok and verified and len(result.ledger) == len(STEP_CATALOG)

    print("\nVALIDATION PASSED" if ok else "\nVALIDATION FAILED")
    return 0 if ok else 1


def cmd_roadmap(_args: argparse.Namespace) -> int:
    """Print the phase + sprint roadmap overview."""
    print(render_roadmap(load_roadmap(BACKLOG)))
    return 0


def cmd_sprints(args: argparse.Namespace) -> int:
    """Print every backlog story as a checkbox, optionally filtered by phase."""
    print(render_sprints(load_roadmap(BACKLOG), phase=args.phase))
    return 0


def cmd_checklist(_args: argparse.Namespace) -> int:
    """Print the deployment validation matrix; non-zero exit if any gate is open."""
    rm = load_roadmap(BACKLOG)
    print(render_checklist(rm))
    summary = rm.deployment_summary()
    return 0 if summary["validated"] == summary["total"] else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="zdw", description="Zero Day Warranty CLI")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="execute the 24-step agent chain")
    p_run.add_argument("--json", action="store_true", help="emit JSON")
    p_run.add_argument(
        "--hold-hitl",
        action="store_true",
        help="leave the HITL gate pending instead of auto-approving",
    )
    p_run.set_defaults(func=cmd_run)

    sub.add_parser("calc", help="print reference calculations").set_defaults(func=cmd_calc)
    sub.add_parser("validate", help="validate manifests + verify ledger").set_defaults(
        func=cmd_validate
    )
    sub.add_parser("roadmap", help="phases + sprint progress").set_defaults(func=cmd_roadmap)
    p_sprints = sub.add_parser("sprints", help="backlog stories as checkboxes")
    p_sprints.add_argument("--phase", help="filter to one phase id (e.g. P3)")
    p_sprints.set_defaults(func=cmd_sprints)
    sub.add_parser("checklist", help="deployment validation matrix").set_defaults(
        func=cmd_checklist
    )

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        print(OVERVIEW)
        return 0
    func = args.func
    return int(func(args))


if __name__ == "__main__":
    sys.exit(main())
