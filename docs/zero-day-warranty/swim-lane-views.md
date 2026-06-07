# Zero Day Warranty — Swim Lane Views

One investigation, seen from each lane's seat. The [capability swim lanes](../design/ZeroDayWarranty_Capability_SwimLanes.html) show every lane at once across the seven phases; this is the drill-down — for each lane, the steps it owns, the live decision output sealed to the audit ledger, its KPIs, and its handoffs. The polished portal is [`../design/ZeroDayWarranty_SwimLane_Views.html`](../design/ZeroDayWarranty_SwimLane_Views.html); regenerate both with `zdw lanes --write`.

**Run:** trace `zdw-trace-0001` · suspect lot **LOT-7743** · hot station/tool STATION-07 / TOOL-TQ-07 · 24 audit rows · chain VERIFIED.

## Consumption & Detection · Power BI · Teams

_Where the signal is seen and the result lands — warranty-cost heatmaps raise the cluster, recovery KPIs roll up the outcome._

| KPI | Value |
|---|---|
| Claims in signal | 117 |
| Cohort VINs | 117 |
| Recovery target | $2,822,040 |
| Evidence confidence | 99% |

**Phase span:** steps 1–24 · **Receives:** — · **Hands to:** Agent Orchestration →

**Invariant:** Identity-scoped Power BI Direct Lake surfaces; no row leaves the Gold view.

| Step | Title | Output | Audit |
|---|---|---|---|
| 1 | Receive warranty claim cluster signal | signal: warranty_cluster_threshold_breach · total claims: 117 | sealed |
| 24 | Notify downstream owners (CAPA, dealer advisories) | downstream notified: CAPA, supplier_quality, dealer_advisories | sealed |

**Personas in this lane:** VP Quality, Warranty Analyst

## Data Plane · Microsoft Fabric · medallion

_The per-VIN join. Bronze→Silver→Gold makes build, warranty, quality and telemetry answerable as one classification-aware view._

| KPI | Value |
|---|---|
| VINs joined (Gold) | 117 |
| Hot build weeks | 2 |
| Supplier lots traced | 23 |
| Exposure composed | $4,212,000 |

**Phase span:** steps 3–19 · **Receives:** ← Consumption (cohort signal) · **Hands to:** Agent Orchestration · Accelerated Analytics →

**Invariant:** VIN-conformed, tokenized Silver; sensitivity labels propagate to Gold.

| Step | Title | Output | Audit |
|---|---|---|---|
| 3 | Pull VIN list for affected cohort | cohort size: 117 | sealed |
| 4 | Join VIN list to build records | joined vins: 117 | sealed |
| 5 | Extract build-week distribution of affected VINs | build week claim counts: {11: 12, 12: 26, 13: 29} | sealed |
| 6 | Identify over-represented build weeks vs. baseline | hot weeks: 12, 13 | sealed |
| 7 | Extract station / tool / shift distribution | station distribution: {STATION-07: 36, STATION-06: 2, STATION-09: 2} · tool distribution: {TOOL-TQ-07: 36, TOOL-TQ-06: 2, TOOL-TQ-09: 2} | sealed |
| 9 | Join to quality event records | quality events joined: 1200 | sealed |
| 11 | Join to assembly telemetry | telemetry traces joined: 1200 | sealed |
| 13 | Extract supplier lot codes in hot VIN population | lot codes in hot population: {LOT-7743: 32, LOT-1386: 1, LOT-1002: 1} | sealed |
| 19 | Compute chargeback dollar exposure per supplier lot | attributable usd: 4212000.0 · agentic recovery usd: 2822040.0 · manual baseline usd: 631800.0 | sealed |

**Personas in this lane:** IT / Data Eng, Supplier Quality

## Agent Orchestration · Agent Framework · Foundry

_The 24-step orchestrator. Typed tool-calling on-behalf-of the invoking identity, sealing one audit row per step._

| KPI | Value |
|---|---|
| Steps orchestrated | 24 |
| Owned steps sealed | 15/15 |
| HITL gate | approved |
| Hypothesis confidence | 99% |

**Phase span:** steps 1–24 · **Receives:** ← Data Plane (Gold view) · **Hands to:** Accelerated Analytics · Human-in-the-Loop →

**Invariant:** Per-agent managed identity (OBO); single HITL gate at step 22.

| Step | Title | Output | Audit |
|---|---|---|---|
| 1 | Receive warranty claim cluster signal | signal: warranty_cluster_threshold_breach · total claims: 117 | sealed |
| 2 | Scope the claim cohort by part, failure mode, severity | part number: PN-48820-BRK · failure modes: brake_actuator_premature_wear | sealed |
| 3 | Pull VIN list for affected cohort | cohort size: 117 | sealed |
| 4 | Join VIN list to build records | joined vins: 117 | sealed |
| 5 | Extract build-week distribution of affected VINs | build week claim counts: {11: 12, 12: 26, 13: 29} | sealed |
| 6 | Identify over-represented build weeks vs. baseline | hot weeks: 12, 13 | sealed |
| 7 | Extract station / tool / shift distribution | station distribution: {STATION-07: 36, STATION-06: 2, STATION-09: 2} · tool distribution: {TOOL-TQ-07: 36, TOOL-TQ-06: 2, TOOL-TQ-09: 2} | sealed |
| 17 | Generate root-cause hypothesis with confidence intervals | hypothesis: Supplier lot LOT-7743, installed at STATION-07 on TOOL-TQ-07 … · confidence: 0.99 | sealed |
| 18 | Build evidence package: cohort, tests, raw data | evidence package keys: confidence, hot_station, hot_tool, hot_weeks, root_cause_hypo… | sealed |
| 19 | Compute chargeback dollar exposure per supplier lot | attributable usd: 4212000.0 · agentic recovery usd: 2822040.0 · manual baseline usd: 631800.0 | sealed |
| 20 | Generate supplier chargeback documentation | chargeback documentation: drafted · recovery target usd: 2822040.0 | sealed |
| 21 | Trigger NHTSA Early Warning Reporting check | nhtsa ewr check: applicable | sealed |
| 22 | Route to Quality Director for human review & approval | decision: approve_chargeback · approver: quality.director@toyota.example · recovery target usd: 2822040.0 | sealed |
| 23 | Write decision & rationale to audit ledger | ledger rows written: 23 · chain verified: True | sealed |
| 24 | Notify downstream owners (CAPA, dealer advisories) | downstream notified: CAPA, supplier_quality, dealer_advisories | sealed |

**Personas in this lane:** Quality Analyst, Quality Director

## Accelerated Analytics · NVIDIA · optional

_The statistical core — interaction tests, SPC/drift correlation, supplier-lot attribution graph and RCA reasoning. Runs on CPU without GPUs._

| KPI | Value |
|---|---|
| Warranty-rate ratio | 2.43× |
| Significance p | 1.0e-06 |
| SPC anomalies | 304 |
| Tool drift | 8.93% |

**Phase span:** steps 8–18 · **Receives:** ← Agent Orchestration (cohort) · **Hands to:** Agent Orchestration (evidence) →

**Invariant:** GPU acceleration is optional; the same math and audit contract hold on CPU.

| Step | Title | Output | Audit |
|---|---|---|---|
| 8 | Statistical test: cohort × station × tool × shift | hot station: STATION-07 · hot tool: TOOL-TQ-07 · station rate: 0.0619 | sealed |
| 10 | Identify SPC anomalies preceding the hot build weeks | spc anomalies at hot station: 304 | sealed |
| 12 | Correlate tool calibration drift with hot-station defects | hot tool: TOOL-TQ-07 · avg calibration drift pct: 8.93 | sealed |
| 14 | Compute supplier-lot warranty rate vs. baseline | suspect lot: LOT-7743 · lot warranty rate: 0.0615 · baseline warranty rate: 0.0253 | sealed |
| 15 | Statistical test: supplier-lot attribution significance | z score: 4.891 · p value: 1e-06 · significant: True | sealed |
| 16 | Rank cohort × station × supplier-lot interactions | ranked interactions: {'interaction': 'week×STATION-07×LOT-7743', 'rate_ratio': 2.43} | sealed |
| 17 | Generate root-cause hypothesis with confidence intervals | hypothesis: Supplier lot LOT-7743, installed at STATION-07 on TOOL-TQ-07 … · confidence: 0.99 | sealed |
| 18 | Build evidence package: cohort, tests, raw data | evidence package keys: confidence, hot_station, hot_tool, hot_weeks, root_cause_hypo… | sealed |

**Personas in this lane:** Mfg Engineering, Supplier Quality

## Human-in-the-Loop · Quality Director · Teams

_The single human gate. The evidence package arrives as a Teams Adaptive Card; approve / amend / deny — the decision is sealed._

| KPI | Value |
|---|---|
| Decision | approve chargeback |
| Recovery approved | $2,822,040 |
| Evidence confidence | 99% |
| Adaptive Card | generated |

**Phase span:** steps 22–22 · **Receives:** ← Agent Orchestration (evidence package) · **Hands to:** Downstream Action →

**Invariant:** Exactly one approval gate; the decision and approver are sealed at step 22.

| Step | Title | Output | Audit |
|---|---|---|---|
| 22 | Route to Quality Director for human review & approval | decision: approve_chargeback · approver: quality.director@toyota.example · recovery target usd: 2822040.0 | sealed |

**Personas in this lane:** Quality Director, VP Quality

## Downstream Action · CAPA · Supplier · Dealer · NHTSA

_Turning the approved decision into action — NHTSA EWR check, supplier chargeback docs, CAPA / SCAR / dealer advisories._

| KPI | Value |
|---|---|
| NHTSA EWR | applicable |
| Recovery target | $2,822,040 |
| Downstream owners | 3 |
| Chargeback docs | drafted |

**Phase span:** steps 20–24 · **Receives:** ← Human-in-the-Loop (approval) · **Hands to:** Consumption (KPI rollup) →

**Invariant:** Every dispatched action references the trace; downstream effects are logged.

| Step | Title | Output | Audit |
|---|---|---|---|
| 20 | Generate supplier chargeback documentation | chargeback documentation: drafted · recovery target usd: 2822040.0 | sealed |
| 21 | Trigger NHTSA Early Warning Reporting check | nhtsa ewr check: applicable | sealed |
| 24 | Notify downstream owners (CAPA, dealer advisories) | downstream notified: CAPA, supplier_quality, dealer_advisories | sealed |

**Personas in this lane:** Compliance, Plant Ops

## Governance Foundation · Entra · Purview · Audit ledger · Defender

_Cross-cutting under every phase — identity, DLP/DSPM, the 14-field hash-chained audit row per step, and OT security._

| KPI | Value |
|---|---|
| Audit rows sealed | 24 |
| Hash chain | VERIFIED |
| Coverage | 1 / step |
| Sensitivity labels | 2 |

**Phase span:** steps 1–24 · **Receives:** underlies every lane · **Hands to:** regulator-replayable record

**Invariant:** Tamper-evident hash chain; one sealed 14-field row per step; verifiable.

| Step | Title | Output | Audit |
|---|---|---|---|
| 1 | Receive warranty claim cluster signal | signal: warranty_cluster_threshold_breach · total claims: 117 | sealed |
| 2 | Scope the claim cohort by part, failure mode, severity | part number: PN-48820-BRK · failure modes: brake_actuator_premature_wear | sealed |
| 3 | Pull VIN list for affected cohort | cohort size: 117 | sealed |
| 4 | Join VIN list to build records | joined vins: 117 | sealed |
| 5 | Extract build-week distribution of affected VINs | build week claim counts: {11: 12, 12: 26, 13: 29} | sealed |
| 6 | Identify over-represented build weeks vs. baseline | hot weeks: 12, 13 | sealed |
| 7 | Extract station / tool / shift distribution | station distribution: {STATION-07: 36, STATION-06: 2, STATION-09: 2} · tool distribution: {TOOL-TQ-07: 36, TOOL-TQ-06: 2, TOOL-TQ-09: 2} | sealed |
| 8 | Statistical test: cohort × station × tool × shift | hot station: STATION-07 · hot tool: TOOL-TQ-07 · station rate: 0.0619 | sealed |
| 9 | Join to quality event records | quality events joined: 1200 | sealed |
| 10 | Identify SPC anomalies preceding the hot build weeks | spc anomalies at hot station: 304 | sealed |
| 11 | Join to assembly telemetry | telemetry traces joined: 1200 | sealed |
| 12 | Correlate tool calibration drift with hot-station defects | hot tool: TOOL-TQ-07 · avg calibration drift pct: 8.93 | sealed |
| 13 | Extract supplier lot codes in hot VIN population | lot codes in hot population: {LOT-7743: 32, LOT-1386: 1, LOT-1002: 1} | sealed |
| 14 | Compute supplier-lot warranty rate vs. baseline | suspect lot: LOT-7743 · lot warranty rate: 0.0615 · baseline warranty rate: 0.0253 | sealed |
| 15 | Statistical test: supplier-lot attribution significance | z score: 4.891 · p value: 1e-06 · significant: True | sealed |
| 16 | Rank cohort × station × supplier-lot interactions | ranked interactions: {'interaction': 'week×STATION-07×LOT-7743', 'rate_ratio': 2.43} | sealed |
| 17 | Generate root-cause hypothesis with confidence intervals | hypothesis: Supplier lot LOT-7743, installed at STATION-07 on TOOL-TQ-07 … · confidence: 0.99 | sealed |
| 18 | Build evidence package: cohort, tests, raw data | evidence package keys: confidence, hot_station, hot_tool, hot_weeks, root_cause_hypo… | sealed |
| 19 | Compute chargeback dollar exposure per supplier lot | attributable usd: 4212000.0 · agentic recovery usd: 2822040.0 · manual baseline usd: 631800.0 | sealed |
| 20 | Generate supplier chargeback documentation | chargeback documentation: drafted · recovery target usd: 2822040.0 | sealed |
| 21 | Trigger NHTSA Early Warning Reporting check | nhtsa ewr check: applicable | sealed |
| 22 | Route to Quality Director for human review & approval | decision: approve_chargeback · approver: quality.director@toyota.example · recovery target usd: 2822040.0 | sealed |
| 23 | Write decision & rationale to audit ledger | ledger rows written: 23 · chain verified: True | sealed |
| 24 | Notify downstream owners (CAPA, dealer advisories) | downstream notified: CAPA, supplier_quality, dealer_advisories | sealed |

**Personas in this lane:** Compliance, IT / Security

## Day-0 Prevention · NVIDIA Metropolis · edge

_Catch the defect at the station so it never becomes a claim — inline vision, edge inference, jidoka stop, per-VIN inspection record._

| KPI | Value |
|---|---|
| Units inspected | 100% |
| Inspection records | 1200 |
| Edge inference | ~5 ms |
| On FAIL | jidoka |

**Phase span:** steps 9–9 · **Receives:** continuous · at the build station · **Hands to:** Data Plane (inspection record) →

**Invariant:** Every unit inspected (no sampling); per-VIN evidence persisted to Bronze.

| Step | Title | Output | Audit |
|---|---|---|---|
| 9 | Join to quality event records | quality events joined: 1200 | sealed |

**Personas in this lane:** Line Operator, Quality / Agent

