# Zero Day Warranty — Release Plan (v0.1 → v1.0)

How the solution gets from the **reference/demo build** it is today to a
**production-grade v1.0**. Each rung below is a shippable milestone with a clear
theme, the concrete steps to complete it, and the exit criteria that let you call
it "done." The version numbers overlay the existing delivery backlog
(`backlog/roadmap.yaml`, phases **P1–P4**) — see the *Maps to* line on each rung.

> **Read this as a ladder, not a calendar.** Sizes are relative effort
> (S / M / L), not dates. Re-baseline to real dates with the team once a pilot
> client and start date are fixed (that is itself milestone **v0.8 / v0.9**).

---

## Where we are today

The current build is a **mock-mode reference implementation**, deployed and
demoable:

- The 24-step / 7-cluster chain runs **deterministically against a synthetic
  Gold view** (it reproduces the reference figures: LOT-7743, 2.4× rate,
  $4.2M / $2.8M, chain VERIFIED). It does **not yet call a live LLM** or read
  real source systems.
- The **audit ledger is in-memory** (14-field, hash-chained, HMAC-SHA256). The
  durable Postgres/Delta DDL exists but the reference run seals to memory.
- It is **deployed to Azure** in a self-contained resource group
  (`Agentic-Automotives`) and serves live pages (`/portal`, `/process-3d`,
  `/agents`, `/ledger`) — all 12 deployment gates validated.
- The **design pack, CLI, CI/CD, and tests** are complete and green.

That places us at roughly **v0.3** on the ladder below. Everything from **v0.4**
on is net-new engineering toward production.

| Version | Theme | Maps to | Status |
|---|---|---|---|
| **v0.1** | Reference engine & design pack | P1 (S1–S2) | ✅ done |
| **v0.2** | Design validated & hardening plan | P2 (S3–S4) | ✅ mostly done |
| **v0.3** | Deployed reference + live demo | P3 (S5–S8) | ✅ done — **we are here** |
| **v0.4** | Real intelligence (live LLM + Teams) | new (extends S8) | ⬜ next |
| **v0.5** | Real data connectors | P4 · S9 | ⬜ todo |
| **v0.6** | Evaluation & guardrails | P4 · S10 | ⬜ todo |
| **v0.7** | Security hardening to prod bar | P4 · S11 | ⬜ todo |
| **v0.8** | Business Value Assessment | P4 · S12 | ⬜ todo |
| **v0.9** | Pilot (one real cluster, client in the loop) | new | ⬜ todo |
| **v1.0** | Production GA | new | ⬜ todo |

---

## The big shift: "reference" → "production"

Five things change on the way to 1.0. Every rung below advances one or more of
these tracks; keep them in view so nothing is skipped:

1. **Intelligence** — deterministic mock logic → real Agent Framework / Foundry
   orchestration calling Azure OpenAI (and optionally NVIDIA) for the
   reasoning-heavy steps (hypothesis, RCA, evidence narrative), under the *same*
   audit contract.
2. **Data** — embedded synthetic Gold view → real source connectors landing
   Bronze, conformed through the Fabric medallion to the Gold per-VIN view.
3. **Durability** — in-memory audit ledger → WORM Delta/Postgres store with the
   key in Key Vault and a Purview lineage echo.
4. **Security** — demo-grade access → private endpoints, Entra (keyless) DB auth,
   secret rotation, and a passed security review.
5. **Value & evidence** — reference figures → client-baselined BVA, an evaluation
   harness proving accuracy, and a pilot that ran a real case end to end.

---

## v0.4 — Real intelligence (live LLM + Teams)  ·  size M
**Goal:** the chain *thinks* with a real model and the human gate is real.
**Maps to:** extends P3 / S8.

**Steps**
1. Introduce a model-call boundary in `chain.py` (an `LLMClient` interface) so
   the reasoning steps (17 hypothesis, 18 evidence, 20 chargeback draft) can be
   served either by the deterministic mock (offline/tests) **or** Azure OpenAI
   (`gpt-4.1-mini`) via the deployed managed identity (keyless, on-behalf-of).
2. Keep the statistical steps (8, 14, 15) deterministic — they are math, not
   generation — but let the model *narrate* them into the evidence package.
3. Wire **real Teams delivery**: set `TEAMS_WEBHOOK_URL` (Key Vault secret) on
   the orchestrator Container App; confirm the Adaptive Card posts and the
   approve/amend/deny callback seals to the ledger.
4. Validate the **NVIDIA-optional** path is a clean no-op when GPUs are absent
   (already true) and a measured speed-up when present.

**Exit criteria**
- `GET /run` produces an evidence package whose hypothesis/narrative came from a
  live AOAI call, with `model_version` recorded on every audit row.
- A real Teams card is approved by a human and the decision is sealed + verified.
- All tests still green with the mock client (CI stays offline-deterministic).

---

## v0.5 — Real data connectors  ·  size L
**Goal:** real warranty/build/quality/telemetry data flows in, not synthetic.
**Maps to:** P4 · **S9**.

**Steps**
1. Build source adapters for the four domains — MES/ERP (build), connected-
   vehicle warranty stream, QMS (quality events), SCADA/telemetry — landing raw
   to **Bronze** (Fabric OneLake / Real-Time Hub).
2. Conform Bronze → **Silver** (VIN-conformed, tokenized, sensitivity-labelled) →
   **Gold** per-VIN view; point the chain's Gold reader at Fabric instead of the
   embedded synthetic dataset.
3. Handle **schema drift + late-arriving data**: dead-letter queue, reconcile
   job, and freshness SLAs on the Gold view.
4. Keep the synthetic dataset as the **CI fixture** (tests never depend on live
   sources).

**Exit criteria**
- A cluster signal on *real* data resolves to VINs, joins build/quality/
  telemetry, and yields an evidence package — same 24-step contract.
- Gold-view freshness + pipeline-success SLOs are defined and monitored.

---

## v0.6 — Evaluation & guardrails  ·  size M
**Goal:** prove the agent is accurate and safe before it touches money.
**Maps to:** P4 · **S10** (and closes S4-3).

**Steps**
1. Curate an **eval set** of labelled historical clusters (known root cause /
   known lot) and an **offline scoring** harness (precision/recall on
   attribution, calibration of confidence, $ error vs. settled chargebacks).
2. Wire an **audit-row feedback loop** — sealed decisions + human
   amend/deny outcomes become new eval cases.
3. Add **prompt-injection / content guardrails** on the RAG and tool surfaces
   (input/output filters, allow-listed tools, OBO scope checks).
4. Define **SLOs**: time-to-evidence, decision-SLA, eval-score floor that gates
   releases.

**Exit criteria**
- An eval report meets the agreed score floor on the held-out set.
- Guardrail tests pass (injection attempts blocked, tools scoped).

---

## v0.7 — Security hardening to production bar  ·  size M
**Goal:** meet the landing-zone / governed-tenant security requirements.
**Maps to:** P4 · **S11** (and closes S4-4).

**Steps**
1. Deploy the **private variant by default** (`infra/main-private.bicep`):
   private endpoints for KV / ACR / AOAI, VNet-injected Postgres, VNet-integrated
   Container Apps — no public data-plane. (The Bicep exists; make it the deployed
   default and validate the deny-policy passes.)
2. **Entra DB auth** — drop the Postgres password in favour of managed-identity
   token auth.
3. **Secret rotation** policy + **WORM audit export** to Delta with a Purview
   lineage echo (production audit durability).
4. Pass an internal **security review** (threat model, data classification, DLP /
   DSPM for AI on the Gold views).

**Exit criteria**
- No public network access on any data service; security review signed off.
- Audit rows are written to immutable storage and externally verifiable.

---

## v0.8 — Business Value Assessment  ·  size S
**Goal:** replace reference figures with client-true numbers.
**Maps to:** P4 · **S12**.

**Steps**
1. With client Finance/Quality, re-derive the manual baseline and the agentic
   recovery from **their** actuals (claims volume, chargeback rates, cycle time).
2. Commit a **KPI envelope** (recovery %, time-to-evidence, clusters/quarter,
   audit completeness) that the pilot will be measured against.

**Exit criteria**
- A signed BVA; all currency/percentage figures in the design pack updated to
  client-baselined values (the design pages flag everything currently synthetic).

---

## v0.9 — Pilot  ·  size L
**Goal:** run one real cluster, end to end, with the client persona in the loop.
**Maps to:** new (operational readiness).

**Steps**
1. Pick a real, bounded scope (one plant / one part family) and run a live
   investigation; a real **Quality Director approves** the chargeback.
2. **Operational readiness**: runbooks, on-call, alerting, Power BI executive +
   director dashboards, cost guardrails (scale-to-zero vs. warm SLAs).
3. **UAT** with the nine personas against their portals; collect feedback into
   the backlog.

**Exit criteria**
- A real chargeback recovered (or formally recommended) through the system, fully
  audited; UAT sign-off; operational runbooks in place.

---

## v1.0 — Production GA  ·  size M (gate, not new build)
**Goal:** general availability for the engagement scope.

**Definition of Done — all must be true**
- [ ] Real LLM-driven reasoning under the audit contract (**v0.4**)
- [ ] Real connectors + medallion freshness SLOs (**v0.5**)
- [ ] Eval score floor met + guardrails enabled (**v0.6**)
- [ ] Private networking, Entra DB auth, WORM audit, security review signed
      (**v0.7**)
- [ ] Client-baselined BVA + committed KPI envelope (**v0.8**)
- [ ] Pilot recovered a real case, UAT signed, runbooks live (**v0.9**)
- [ ] SLOs green for N consecutive weeks; DR/backup tested
- [ ] **Operate handoff package** delivered (support model, ownership, change
      process)

When every box is checked, tag **v1.0** and cut over from pilot to production.

---

## Sequencing & dependencies

```
v0.3 (here)
   └─ v0.4 real LLM + Teams ─┬─ v0.6 eval & guardrails ─┐
   └─ v0.5 real connectors  ─┘                          ├─ v0.9 pilot ─ v1.0 GA
        v0.7 security hardening ───────────────────────┤
        v0.8 BVA (parallel, needs client Finance) ──────┘
```

- **v0.4 and v0.5 can run in parallel** (different teams: app vs. data).
- **v0.6 depends on v0.4+v0.5** (need real reasoning + real data to evaluate).
- **v0.7 can start immediately** (Bicep private variant already exists) and must
  land before pilot.
- **v0.8 (BVA)** is gated by client Finance availability, not engineering — start
  the conversation early.
- **v0.9 pilot** needs v0.4–v0.8 in place; **v1.0** is the GA gate, not new build.

## How to track it

This ladder maps 1:1 onto `backlog/roadmap.yaml`. Use the orchestrator to watch
progress as the P4 sprints (S9–S12) and the new app/eval work move:

```bash
zdw roadmap     # phases + sprint progress
zdw sprints     # every story as a checkbox
zdw checklist   # deployment validation matrix (built / deployed / tested)
```

> All figures and data are **synthetic reference values** until **v0.8** signs the
> client-baselined BVA. The design pack labels everything accordingly.
