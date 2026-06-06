# Zero Day Warranty — Experts Panel

Ten domain experts reviewed the design (architecture, capabilities, persona
portals, deployment). **Consensus: proceed with the discovery-stage RnD pilot.**
The spine is sound; the gaps are the expected maturity deltas between an RnD
pilot and production — **12 items, 4 High** — none blocking for RnD.

## The panel

| Expert | Focus | Verdict |
|---|---|---|
| Lena Hoffmann · Solution Architect | coherence, portability, runtime choice | sound |
| Raj Patel · Cloud Platform | RG isolation, IaC, networking, CI/CD | conditional |
| Aisha Bello · Security | least privilege, keyless, tamper-evidence | conditional |
| Marco Rossi · Data | per-VIN join, tokenization, scale | conditional |
| Wei Chen · AI / MLOps | model choice, eval, RAG, guardrails | conditional |
| Dr. Elena Vasquez · Responsible AI & Compliance | HITL, EWR, audit durability | conditional |
| Sam Okafor · FinOps / Capacity | AOAI quota, cost guardrails | conditional |
| Priya Menon · SRE / Reliability | observability, SLOs, idempotency, DR | conditional |
| Yuki Tanaka · Automotive Quality SME | RCA validity, multiple-testing, chargeback realism | conditional |
| Diego Santos · Integration | source connectors, schema drift | conditional |

## Coverage matrix

| Dimension | Status |
|---|---|
| Identity & access | ✅ Covered |
| Secrets management | ✅ Covered (rotation to add) |
| Data plane / medallion | ✅ Covered |
| Audit & tamper-evidence | ✅ Covered |
| Human-in-the-loop | ✅ Covered |
| Regulatory (NHTSA EWR) | ✅ Covered |
| Observability | ✅ Covered |
| PII / data tokenization | 🟡 Partial |
| Statistical rigor | ✅ Covered (multiple-testing correction added) |
| Reliability / DR | 🟡 Partial |
| Cost / capacity | 🟡 Partial (AOAI quota dependency) |
| Integration / ingestion | 🟡 Partial |
| Scalability | 🟡 Partial |
| Model evaluation / RAI guardrails | 🟥 Gap |
| CI/CD | ✅ Covered (CI + gated CD added) |
| Private networking / CMK | ⬜ RnD-scoped |
| NVIDIA GPU acceleration | ⬜ RnD-scoped |

## Gap log

Prioritized actions to close before stage/production. None block the RnD pilot.

| # | Gap | Sev | Recommendation | Target |
|---|---|---|---|---|
| 1 | Model-evaluation harness | High | eval set + offline scoring; feed sampled audit rows back as eval cases | stage (S10) |
| 2 | Multiple-testing inflation | High | Bonferroni / Benjamini-Hochberg before declaring attribution — **done** in `stats.py` | pilot |
| 3 | No CI/CD | High | GitHub Actions build + what-if/validate gate — **done** (`ci.yml` + `deploy.yml`) | stage |
| 4 | Audit durability + private networking | High | WORM export + Purview echo; private endpoints on KV/ACR/AOAI/PG | prod (S11) |
| 5 | PII tokenization at Bronze→Silver | Med | format-preserving tokenization; no raw PII in Silver | stage |
| 6 | DB password auth | Med | Entra DB authentication via the managed identity | stage |
| 7 | Secret rotation | Med | rotation policy + alerting on signing key / db-url | stage |
| 8 | Signal idempotency / dedupe | Med | idempotency key per cluster signal | pilot |
| 9 | Real source connectors | Med | MES/ERP/Connected/QMS/SCADA adapters + drift handling | stage (S9) |
| 10 | Postgres scale ceiling | Med | size up PG or move data plane to Fabric | stage |
| 11 | Prompt-injection guardrails | Med | content filtering on retrieved docs + tool outputs | stage |
| 12 | Token budget / cost guardrail | Low | per-run token cap + cost alerting | pilot |

## Round-table verdict

**Proceed with the RnD pilot.** Before stage/production, close the four High
items (1–4; #2 and #3 already done in this build). Every currency figure must
also be re-derived against the client's actual baseline in a Business Value
Assessment (sprint S12).

## Validated complete (the "not missing anything" checklist)

- Four data domains + per-VIN Gold join + medallion mapping (laptop → Postgres → Fabric).
- 24-step / 7-cluster chain, each step owned by an agent and emitting an audit row.
- A single, enforceable HITL gate before any external effect (SLA + escalation).
- 14-field, append-only, hash-chained audit ledger — regulator-replayable.
- NHTSA EWR step + supplier-chargeback evidence package.
- Per-persona views (nine portals) + full capability swim lanes.
- Self-contained, reproducible Azure deployment (single RG, IaC, identity,
  secrets, observability).
- All currency figures labelled synthetic, with parameterized inputs.
