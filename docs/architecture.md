# Zero Day Warranty — Architecture & Process

This document summarizes the architecture implemented in this repository and
how it maps to the design pack under [`design/`](design/) (the
*Architecture & Process Diagrams* and *Calculations & References* HTML
companions). It follows the APEX delivery-accelerator patterns.

## 1. What the solution does

When a connected-vehicle warranty cluster breaches its volume threshold, a
single orchestrator agent runs a 24-step investigation that joins warranty
claims back to per-VIN factory build history, isolates the responsible supplier
lot with statistical significance, and produces a chargeback evidence package
gated by a Quality-Director human-in-the-loop (HITL) approval.

| Metric | Current state (manual) | Agentic state |
|---|---|---|
| Wall-clock | 8–12 weeks | ~12 minutes |
| Teams involved | 6 (sequential handoffs) | 1 orchestrator + 1 HITL approver |
| Person-hours | ~440 | < 5 |
| Cost / investigation | ~$88,000 | ~$1,000 |
| Audit-ledger completeness | manual / variable | 100% · hash-chained |
| Chargeback recovery (reference) | ~15% (~$0.63M) | ~67% (~$2.8M) |

## 2. The four data domains and the medallion

The agent reads one per-VIN **Gold** view joined across four source domains.
Each already exists somewhere in a typical OEM data estate; the missing piece is
the per-VIN joinable view across all four.

```
Source systems            Bronze            Silver                 Gold
(MES/ERP, Connected,  ->  raw landing  ->   canonical, VIN-    ->  per-VIN joinable
 QMS, SCADA/historian)    (schema-on-read)  conformed, typed       Build x Warranty
                                                                   x Quality x Telemetry
```

- **Bronze** — raw, immutable landing (source-native shapes).
- **Silver** — the canonical, VIN-conformed, typed models in
  [`domains.py`](../src/zero_day_warranty/domains.py).
- **Gold** — the agent-safe, classification-aware per-VIN view assembled by
  [`medallion.py`](../src/zero_day_warranty/medallion.py)
  (`Medallion.gold_per_vin()` → `GoldVehicleView`). In production these are
  Microsoft Fabric OneLake Delta tables exposed as Direct Lake Gold views.

VIN is the single conformed join key across all four domains.

## 3. The 24-step agent chain

Implemented in [`chain.py`](../src/zero_day_warranty/chain.py) as
`WarrantyRootCauseChain`. Seven functional clusters, each mapped to an agent
role and a platform component:

1. **Detect & Scope** (1–3) — confirm the cluster signal, scope the cohort by
   part / failure mode / severity, pull the VIN list.
2. **Build context** (4–7) — join VINs to build records, compute the build-week
   distribution, flag over-represented (hot) weeks, extract station/tool/shift
   distribution.
3. **Statistical tests** (8) — two-proportion test on the
   `cohort × station` interaction *(RAPIDS cuML in prod)*.
4. **Quality + Telemetry** (9–12) — join quality events and telemetry, find SPC
   anomalies and tool calibration drift at the hot station *(Triton in prod)*.
5. **Supplier attribution** (13–16) — extract lot codes, compute the suspect-lot
   warranty rate vs. baseline, test significance, rank interactions
   *(RAPIDS cuGraph/cuML in prod)*.
6. **Hypothesis + Evidence** (17–20) — generate the root-cause hypothesis with
   confidence, assemble the evidence package, compute chargeback exposure, draft
   the chargeback documentation *(NIM + NeMo Retriever in prod)*.
7. **Compliance + HITL** (21–24) — NHTSA EWR check, Quality-Director approval via
   a Teams Adaptive Card, write the decision to the audit ledger, notify
   downstream owners (CAPA, dealer advisories).

Every step emits exactly one 14-field audit row. The chain pauses at step 22 for
the HITL gate; nothing with an external effect proceeds without the recorded
approval.

## 4. The audit ledger

[`audit.py`](../src/zero_day_warranty/audit.py) implements the 14-field decision
row (APEX Sellers Guide §11.2) plus an explicit **hash chain**: each sealed row
carries `prev_link` (the previous row's HMAC-SHA256 signature). `verify_chain()`
confirms every signature and that the chain is unbroken — tampering with any row
breaks the chain from that row forward. The ledger is append-only and refuses
overwrites. In production this is a Delta table under a WORM policy with the
signing key in Key Vault (keyed by `tenant_id`), echoed to Microsoft Purview.

## 5. The reference calculations

[`calculations.py`](../src/zero_day_warranty/calculations.py) makes the design
pack's math executable and parameterized:

- **Calculation A** — manual RCA baseline: 440 hrs × $200/hr = **$88,000** /
  investigation.
- **Calculation B** — agent wall-clock: 24 steps × ~30s = **~12 minutes**.
- **Calculations C1–C3** — chargeback scenario: **$4.2M** attributable →
  **$2.8M** recovered (67%) vs. **$0.63M** manual (15%) = **~340%** improvement.

All inputs are swappable (`ScenarioInputs`) so a Business Value Assessment can
re-derive every figure against a client's actual cost base without changing the
structure.

## 6. Platform mapping

| Role | Microsoft component | NVIDIA acceleration (optional) |
|---|---|---|
| Unified data layer | Microsoft Fabric · OneLake medallion | RAPIDS cuDF on Gold |
| Agent reasoning / orchestration | Microsoft Agent Framework on Azure AI Foundry | NIM · NeMo Retriever (step 17–18) |
| Accelerated statistics | — | RAPIDS cuML/cuGraph (steps 8, 14, 15); Triton (steps 10, 12) |
| Governance / audit / lineage | Microsoft Purview | — |
| Identity & access | Microsoft Entra ID (per-agent managed identity, OBO) | — |
| HITL surface | Microsoft Teams (Adaptive Card) | — |
| Consumption | Power BI (heatmaps, dashboards) | Omniverse investigation cockpit |
| Day-0 prevention | Microsoft Fabric Real-Time Hub | Metropolis + DeepStream + Jetson at the station |

All components run inside the customer's Azure tenant. The architecture is
viable end-to-end on Microsoft components alone; NVIDIA additions plug in
through NVIDIA AI Enterprise on Azure.

## 7. Mapping to the service definition

The runnable engine above is declared as an APEX service under
[`service/AXLE-WARRANTY-01/`](../service/AXLE-WARRANTY-01/):

- `scenario.yaml` — the 24-step chain and its seven agents.
- `agents/<role>/agent.yaml` + `prompts/<role>.md` — one manifest and prompt per
  cluster agent.
- `use-cases/_default/use-case.yaml` — the adapter wiring, personas, KPIs, HITL
  thresholds, and a smoke test.
- `_gold/axle_warranty_01_root_cause.gold.yaml` — the Gold-view contract.
- `config/hitl-thresholds.yaml` — the HITL gating thresholds enforced at step 22.

`python zdw.py validate` loads and validates every manifest and verifies the
hash chain end-to-end.
