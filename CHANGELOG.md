# Changelog

All notable changes to the Zero Day Warranty solution are documented here.

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
