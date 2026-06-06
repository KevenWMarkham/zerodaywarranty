# Changelog

All notable changes to the Zero Day Warranty solution are documented here.

## [Unreleased]

### Added

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
