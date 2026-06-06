# Zero Day Warranty — Delivery Plan

Four phases / twelve sprints, driven by a single backlog
([`../../backlog/roadmap.yaml`](../../backlog/roadmap.yaml)) and a sprint
**orchestrator**. Every deployable component is gated **built → deployed →
tested**; "done" is provable, not asserted.

## The orchestrator

```bash
python zdw.py roadmap     # phases + sprint progress bars
python zdw.py sprints     # every story as a checkbox  ([--phase P3])
python zdw.py checklist   # deployment validation matrix (exits non-zero while any gate is open)
```

Checkbox legend: `[x]` done · `[~]` in progress · `[ ]` todo · `[!]` blocked.

## Roadmap

| Phase | Sprints | Status |
|---|---|---|
| **P1 · Foundation & Reference Build** | S1 Core engine · S2 Manifests & design pack | ✅ done |
| **P2 · Design Validation & Hardening** | S3 Experts panel · S4 Hardening designs | 🟡 in progress |
| **P3 · Azure Deployment** (Agentic-Automotives) | S5 Foundation · S6 Platform · S7 App & data · S8 E2E validation | ☐ todo |
| **P4 · Pilot Readiness** | S9 Connectors · S10 Eval & guardrails · S11 Security hardening · S12 BVA | ☐ todo |

Overall stories complete: ~50% (P1–P2 deliver the design; P3 deploys; P4 reaches
pilot readiness).

### P3 sprints carry deployment gates

| Sprint | Deployments gated (built → deployed → tested) |
|---|---|
| S5 Foundation | RG · managed identity · Key Vault · Log Analytics + App Insights |
| S6 Platform | ACR · Azure OpenAI (+deployments) · Postgres (+db) · Container Apps env |
| S7 App & data | container images · Container Apps · medallion + audit schemas |
| S8 E2E validation | end-to-end run (signal → evidence → HITL → audit) |

## Deployment validation matrix

Twelve deployable components, each validated only when **all three** gates are
checked. All gates are currently open (nothing deployed):

| Sprint | Component | Built | Deployed | Tested |
|---|---|:--:|:--:|:--:|
| S5 | Resource group Agentic-Automotives | ☐ | ☐ | ☐ |
| S5 | Managed identity id-zdw-warranty-agent | ☐ | ☐ | ☐ |
| S5 | Key Vault kv-zero-day-warranty | ☐ | ☐ | ☐ |
| S5 | Log Analytics + Application Insights | ☐ | ☐ | ☐ |
| S6 | Container Registry acrzdwagentic | ☐ | ☐ | ☐ |
| S6 | Azure OpenAI aoai-zdw-agentic + deployments | ☐ | ☐ | ☐ |
| S6 | Postgres pg-zdw-agentic + db zdw | ☐ | ☐ | ☐ |
| S6 | Container Apps env cae-zdw-agentic | ☐ | ☐ | ☐ |
| S7 | Container images (orchestrator + 2 MCP) | ☐ | ☐ | ☐ |
| S7 | Container Apps (ca-zdw-*) | ☐ | ☐ | ☐ |
| S7 | Medallion schemas + audit ledger | ☐ | ☐ | ☐ |
| S8 | End-to-end run | ☐ | ☐ | ☐ |

**Definition of validated:** *Built* = artifact exists (image pushed / Bicep
what-if clean); *Deployed* = applied to Agentic-Automotives; *Tested* = the
post-deploy check passed (`zdw validate` against the live resource / smoke test).
Flip the flags in `backlog/roadmap.yaml` as work lands; `zdw checklist`
recomputes "validated" automatically and CI/CD can block on it.

## High-gap closure (from the Experts Panel)

| Gap (High) | Sprint | Status | Artifact |
|---|---|---|---|
| CI pipeline | S4-1 | ✅ done | `.github/workflows/ci.yml` |
| Multiple-testing correction | S4-2 | ✅ done | `stats.bonferroni / benjamini_hochberg` + tests |
| CD pipeline (what-if gate) | S4-5 | ✅ done | `.github/workflows/deploy.yml` |
| Model-evaluation harness | S4-3 → S10 | 🟡 in progress | designed; build in S10 |
| Audit durability + private networking | S4-4 → S11 | ☐ todo | designed; build in S11 |

See the full gap log in [Experts Panel](04-experts-panel.md#gap-log).
