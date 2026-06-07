# Changelog

All notable changes to the Zero Day Warranty solution are documented here.

## [Unreleased]

### Added

- **Demo walk-through script** — `docs/DEMO_WALKTHROUGH.md`, a presenter's script
  for demoing the deployed solution end to end: pre-flight (warm the
  scale-to-zero app), the live `/run`, a tab-by-tab tour of the live `/portal`
  Swim Lane Views, the persona portals, the HITL Adaptive Card (`/hitl-card`) and
  the VERIFIED audit chain, the value table (~12 min vs 8–12 weeks, $4.2M
  exposure, $2.8M / +347% recovery), and the build/extensibility act. Includes a
  live-command cheat-sheet (against the deployed Azure endpoint), a local
  fallback, an objections FAQ, and reset notes. Figures verified against an actual
  chain run.
- **Swim Lane Views served live by the orchestrator** — the orchestrator
  Container App now serves the Swim Lane Views portal as HTML at `GET /portal`
  (aliases `/lanes`, `/swim-lanes`, `/swimlanes`), rendered from a fresh chain run
  on each request so the deployed app is self-documenting. The handler returns
  `text/html`; `/health` on the orchestrator advertises `"portal": "/portal"`.
  No new Azure resources — reuses the existing external ingress. `server.py`
  `html_route` + tests in `tests/test_server.py`.
- **Swim Lane Views** — per-lane drill-down companion to the (whole-picture)
  Capability Swim Lanes. `lanes.py` builds one view per lane (Consumption &
  Detection, Data Plane, Agent Orchestration, Accelerated Analytics,
  Human-in-the-Loop, Downstream Action, Governance Foundation, Day-0 Prevention)
  from a **live chain run** — each view shows the steps that lane owns, its KPIs,
  the live decision output it sealed to the audit ledger, its phase coverage, and
  its handoffs, with links into the matching Persona Portals. Rendered as a
  standalone design-pack portal (`docs/design/ZeroDayWarranty_SwimLane_Views.html`,
  shared visual system + tabs) and a diffable Markdown twin
  (`docs/zero-day-warranty/swim-lane-views.md`). New CLI `zdw lanes [--write]`
  regenerates both; `tests/test_lanes.py` asserts step coverage, live figures,
  and that the committed artifacts stay in sync with the generator. Cross-linked
  with the Capability Swim Lanes doc and folded into `SCENARIO_PLAYBOOK.md` §3c so
  every future scenario generates them too.
- **HITL Teams Adaptive Card (S8-2)** — `notify.py` builds the Quality-Director
  approval Adaptive Card (schema 1.5) from the chargeback evidence package
  (`build_adaptive_card`), wraps it in the Teams Incoming-Webhook envelope
  (`teams_envelope`), and posts it best-effort (`post_to_teams`, never raises;
  no-op when no webhook is configured). The card carries the suspect lot, hot
  station/tool, affected weeks, warranty-rate ratio, significance, confidence,
  attributable exposure, and recovery target, plus Approve/Amend/Deny
  `Action.Submit` actions (each carrying `{decision, trace_id}`). Wired into
  `chain.py` step 22 (`ChainConfig.teams_webhook_url`): the card is attached to
  the evidence package and step 22 records `teams_card_generated` /
  `teams_card_posted` in the sealed audit row. `server.py` exposes
  `GET /hitl-card` (orchestrator) and reads `TEAMS_WEBHOOK_URL` from the env.
  `tests/test_notify.py` + a `/hitl-card` server test added. Backlog: S8-2 done,
  S8 done.
- **Container apps + images** — `server.py` (stdlib HTTP app serving three roles:
  orchestrator `/run`, mcp-warranty `/tools` + `/gold/summary`, mcp-ledger
  `/tools` + `/verify`) and a multi-stage `Dockerfile` (targets `orchestrator`,
  `mcp-warranty`, `mcp-ledger`) + `.dockerignore`. Clean `pip install .` build and
  the server entrypoint verified locally; `tests/test_server.py` added.
- **Health probes** — liveness / readiness / startup probes on `/health:8080` for
  all three Container Apps (Bicep) + a Docker `HEALTHCHECK`.
- **OIDC deploy bootstrap** — `infra/scripts/azure-bootstrap.sh` creates the
  deployer Entra app + federated credentials (main + `production`) + subscription
  role assignment + GitHub environment and secrets, so the gated `deploy.yml`
  runs keyless. Backlog: S7-1/S7-4 done, S5-3 done.
- **Data model doc** `docs/zero-day-warranty/data.md` — full ERD (Mermaid) + data
  dictionary: the four source entities, the Gold view, and the audit ledger with
  attributes/types/keys/relationships, medallion mapping, enums, and
  classification (derived from `domains.py` / `medallion.py` / `audit.py` /
  `postgres-schemas.sql`).
- **`zdw scenarios`** — search the scenario library (`--search` / `--industry` /
  `--domain` / `--show`) and register the repo's own `service/*/scenario.yaml`
  into the library (`--check` / `--sync`) when missing, updating both the CSV and
  the Excel workbook (`scenarios.py` + tests). Registered
  `axle-warranty-zero-day-root-cause` into the library (now 762).
- **Scenario playbook** `docs/SCENARIO_PLAYBOOK.md` — single-context document to
  generate a new Service-Scenario from a one-line idea, plus reference data
  (`docs/reference/APEX-Scenario-Chains.xlsx`, `scenario-library.csv`) and the
  canonical chain template `templates/canonical-24-step-chain.yaml`.
- **Gated CD workflow** `.github/workflows/deploy.yml` — what-if/validate →
  environment approval → deploy → build/push → schema → smoke test (gap #5 / S4-5).
- **Sprint orchestrator** `roadmap.py` + `backlog/roadmap.yaml` (4 phases / 12
  sprints) with the `zdw roadmap` / `sprints` / `checklist` commands. Deployments
  are gated **built → deployed → tested**; `checklist` exits non-zero while any
  gate is open.
- **Multiple-testing correction** in `stats.py` (`bonferroni`,
  `benjamini_hochberg`) — closes Experts-Panel High gap #2.
- **CI workflow** `.github/workflows/ci.yml` (ruff · mypy · pytest · `zdw
  validate`) — closes High gap #3.
- **Roadmap design doc** `docs/design/ZeroDayWarranty_Roadmap.html` with the
  phase/sprint roadmap, the orchestrator, and the deployment validation matrix.
- Tests: `test_roadmap.py`, `test_stats.py` (now 62 tests).

### Changed

- Azure deployment made **fully self-contained** in `Agentic-Automotives`
  (no shared resources); added Log Analytics + Application Insights.
- Added the **Experts Panel** design review and gap log.

## [0.1.0] — 2026-06-06

Initial reference implementation.

### Added

- **Core package** `zero_day_warranty` (src layout):
  - `domains.py` — the four warranty data domains (build records, warranty
    claims, quality events, assembly telemetry) as VIN-keyed Pydantic models.
  - `medallion.py` — Bronze→Silver→Gold per-VIN join (`GoldVehicleView`).
  - `audit.py` — 14-field, append-only, **hash-chained** decision ledger with
    HMAC-SHA256 signing and full-chain verification.
  - `stats.py` — dependency-free two-proportion z-test.
  - `calculations.py` — parameterized reference math (manual $88K baseline,
    ~12 min wall-clock, $4.2M / $2.8M / ~340% chargeback scenario).
  - `synthetic.py` — deterministic reference dataset embedding the planted
    signal (suspect lot, hot station/tool, affected build weeks).
  - `chain.py` — the 24-step / 7-cluster `WarrantyRootCauseChain` orchestrator,
    emitting one audit row per step with a Quality-Director HITL gate at step 22.
  - `cli.py` + top-level `zdw.py` — `run` · `calc` · `validate` commands.
- **Service definition** `service/AXLE-WARRANTY-01/` — `scenario.yaml`, seven
  agent manifests with authored prompts, `use-cases/_default/`, HITL thresholds,
  and the Gold-view contract.
- **Catalog** `catalog/agents/` — reusable `AgentSpec` entries.
- **Tests** — 50 pytest tests (domains, medallion, audit, calculations, chain,
  manifests). ruff + mypy clean.
- **Docs** — `docs/architecture.md` and the original design pack under
  `docs/design/`.
