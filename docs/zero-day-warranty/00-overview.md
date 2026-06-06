# Zero Day Warranty — Overview

**Service:** `AXLE-WARRANTY-01` · **Scenario:** `axle-warranty-zero-day-root-cause`
· **Domain:** Quality & Warranty · **Industry:** Automotive (`axle`)

## The one paragraph

A single AI agent joins connected-vehicle warranty claims back to factory build
history **per VIN**, surfaces the statistically significant
`cohort × station × tool × supplier-lot` interactions that drive a warranty
cluster, and produces a supplier **chargeback evidence package** — collapsing an
**8–12 week, 6-team, ~440 person-hour** manual root-cause investigation into
roughly **12 minutes**, paused only for a Quality-Director human approval.

## The moment

A connected-vehicle warranty cluster breaches its volume threshold for a part /
failure-mode pairing. Today this triggers a manual RCA across six teams (Quality
Assurance, Manufacturing Engineering, Plant Operations, Supplier Quality,
Warranty / After-Sales, IT / Data Engineering). The wall-clock is dominated by
cross-system data reconciliation and sequential handoff queues — not the
analysis itself.

## The solution

A single orchestrator agent runs a **24-step chain** across the four warranty
data domains, isolates the responsible supplier lot with statistical
significance, and assembles a defensible chargeback package — gated by one
human-in-the-loop approval and sealed to a hash-chained audit ledger.

## Two readings of "Zero Day Warranty"

1. **Zero-day investigation latency** — when a cluster emerges, find the root
   cause in minutes, not weeks. *(The agent chain — implemented in this repo.)*
2. **Day-0 detection** — catch the defect at the build station before the vehicle
   ships (NVIDIA Metropolis inline vision). *(Described in the design; out of
   scope for the reference implementation.)*

## The value (reference scenario)

| Metric | Current state (manual) | Agentic state |
|---|---|---|
| Wall-clock | 8–12 weeks | ~12 minutes |
| Teams involved | 6 (sequential handoffs) | 1 orchestrator + 1 HITL approver |
| Person-hours | ~440 | < 5 |
| Cost / investigation | ~$88,000 | ~$1,000 |
| Audit-ledger completeness | manual / variable | 100% · hash-chained |
| Chargeback recovery | ~15% (~$0.63M) | ~67% (~$2.8M) |

Headline reference outcome per cluster: **$4.2M** attributable warranty exposure
→ **$2.8M** recovered = **~340%** improvement over the manual chargeback baseline.

## Personas

- **Quality Director** (primary, HITL approver) — approves / amends / denies the
  chargeback at the gate; the recorded decision is sealed to the ledger.
- **Supplier Quality Engineer** — takes the attribution finding into a SCAR.
- **Warranty / After-Sales Analyst** — owns the heatmap that fires the cluster signal.
- Plant Operations, Manufacturing Engineering, IT/Data Engineering, Compliance,
  and (for Day-0) the Line Quality Operator — see [Design · persona views](01-design.md#persona-views).

## KPIs

| KPI | Target |
|---|---|
| Time-to-evidence-package | < 30 min |
| Person-hours per RCA | < 50 |
| Chargeback recovery rate | +25% vs. 12-month baseline |
| Audit-ledger completeness | 100% |

## Try it

```bash
python zdw.py run        # run the chain on the synthetic reference dataset
python zdw.py calc       # the reference calculations
python zdw.py validate   # manifests + hash-chained audit ledger
```

Continue to [Design](01-design.md) · [Deployment](02-deployment.md) ·
[Plan](03-plan.md) · [Experts Panel](04-experts-panel.md).
