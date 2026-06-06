# AXLE-WARRANTY-01 · Zero Day Warranty root-cause investigation

Service definition for the Zero Day Warranty scenario, following the APEX
service convention (practice **axle** — Automotive · Aftermarket · Mobility).

## Contents

| Path | What it is |
|---|---|
| `scenario.yaml` | The 24-step chain manifest (7 functional clusters, 7 agents) |
| `agents/<role>/agent.yaml` | One manifest per cluster agent |
| `agents/<role>/prompts/<role>.md` | The agent's authored system prompt |
| `use-cases/_default/use-case.yaml` | Adapter wiring · personas · KPIs · HITL thresholds · smoke test |
| `use-cases/_default/DESIGN.md` | Narrative design |
| `config/hitl-thresholds.yaml` | HITL gating thresholds enforced at step 22 |
| `_gold/axle_warranty_01_root_cause.gold.yaml` | The per-VIN Gold-view contract |

## Agents (one per cluster)

| Role | Cluster | Steps | HITL | Key tools |
|---|---|---|---|---|
| `detect` | 1 · Detect & Scope | 1–3 | — | `axle_warranty.pull_vins` |
| `context` | 2 · Build context | 4–7 | — | `fabric.gold.per_vin_view` |
| `stattest` | 3 · Statistical tests | 8 | — | `rapids.cuml.proportion_test` |
| `quality` | 4 · Quality + Telemetry | 9–12 | — | `triton.spc_anomaly`, `triton.drift_correlation` |
| `supplier` | 5 · Supplier attribution | 13–16 | — | `rapids.cugraph.lot_attribution` |
| `hypothesis` | 6 · Hypothesis + Evidence | 17–20 | — | `nim.rca_reasoner`, `nemo.retriever` |
| `compliance` | 7 · Compliance + HITL | 21–24 | ✅ | `teams.adaptive_card`, `compliance.nhtsa_ewr` |

Only the `compliance` agent declares a HITL gate and `operator_obo_required`,
and it is the only agent that produces external effects — all gated by the
Quality Director's recorded approval.

## Validate

```bash
python zdw.py validate
```

Loads `scenario.yaml`, validates all seven `agent.yaml` manifests, runs the
chain on the synthetic dataset, and verifies the 24-row hash-chained ledger.
