# AXLE-WARRANTY-01 · Default use case · Design

## The moment

A connected-vehicle warranty cluster breaches its volume threshold for a
part / failure-mode pairing. Today this triggers a manual root-cause
investigation: six teams (Quality Assurance, Manufacturing Engineering, Plant
Operations, Supplier Quality, Warranty / After-Sales, IT / Data Engineering)
work sequentially across 8–12 weeks and ~440 person-hours. The wall-clock is
dominated by cross-system data reconciliation and handoff queue time, not by the
analysis itself.

## The solution

A single orchestrator agent (Microsoft Agent Framework on Azure AI Foundry) runs
the 24-step chain against the per-VIN Fabric Gold view, isolates the responsible
supplier lot with statistical significance, and produces a chargeback evidence
package — paused only for the Quality Director's HITL approval. ~12 minutes,
< 5 person-hours, 100% audit coverage.

## Personas

- **Quality Director** (primary) — receives the evidence package as a Teams
  Adaptive Card and approves / amends / denies the chargeback at step 22. The
  recorded approval converts a defensible evidence package into a recoverable
  supplier claim.
- **Supplier Quality Engineer** — consumes the attribution finding and opens the
  supplier corrective action (SCAR).
- **Warranty / After-Sales Analyst** — monitors the warranty-cost heatmap that
  triggers the cluster detection.

## KPIs

| KPI | Target | How measured |
|---|---|---|
| Time-to-evidence-package | < 30 min | Audit-ledger timestamps |
| Person-hours per RCA | < 50 | Time tracking across the six teams |
| Chargeback recovery rate | +25% vs. 12-month baseline | Finance reconciliation |
| Audit-ledger completeness | 100% | Purview audit-row inspection |

## HITL design

The `compliance` agent (cluster 7) enforces `config/hitl-thresholds.yaml`. Any
chargeback exposure over the threshold, any potential NHTSA EWR-reportable
cluster, or any low-confidence hypothesis routes to the Quality Director before
any external effect. Identity passthrough (OBO) means downstream tool calls run
under the originating user's permissions, not a service principal.

## Adapter wiring (replace at deployment)

The `client_approved_architecture` block lists the bronze source adapters to
replace with the client's MES/ERP, Toyota Connected, QMS, and SCADA/historian
connectors. Identity → Entra Agent ID; audit → Purview; HITL → Teams; bus →
Eventstream. NVIDIA AI Enterprise on Azure is optional acceleration.

## Smoke test

```bash
python zdw.py validate
```

Generates the synthetic reference dataset, runs the chain, and asserts: 24 audit
rows, hash chain verified, suspect lot found at significance, HITL gate present.
