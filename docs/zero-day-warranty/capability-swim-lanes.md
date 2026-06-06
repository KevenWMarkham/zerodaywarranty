# Zero Day Warranty — Capability Swim Lanes

Every capability the solution ships, organized by **owner** (lane) across the
seven **phases** of one investigation, over an always-on governance foundation.
The polished diagrams are in
[`../design/ZeroDayWarranty_Capability_SwimLanes.html`](../design/ZeroDayWarranty_Capability_SwimLanes.html);
this is the text-native version. Steps in `[n]` reference the 24-step chain.

## How to read

Rows = capability owners. Columns = the seven phases (Detect → Context →
Analyze → Attribute → Hypothesis → Decide → Act). Each cell is a capability.
The governance foundation underlies every cell. NVIDIA lanes are optional
acceleration (the chain runs on CPU without them).

## Master capability swim lane (owners × phases)

| Lane / owner | Detect `1-3` | Context `4-7` | Analyze `8-12` | Attribute `13-16` | Hypothesis `17-20` | Decide `21-22` | Act `23-24` |
|---|---|---|---|---|---|---|---|
| **Consumption & Detection** (Power BI · Teams) | Warranty-cost heatmap → cluster signal `[1]` | | | | | Decision pushed to dashboards | Recovery KPI rollups `[24]` |
| **Data Plane** (Microsoft Fabric · medallion) | Cohort VIN query `[3]` | Per-VIN build join · Gold view `[4-7]` | Quality + telemetry join `[9·11]` | Supplier-lot trace `[13]` | Chargeback exposure compose `[19]` | | |
| **Agent Orchestration** (Agent Framework · Foundry) | Detect & Scope agent `[1-3]` | Build Context agent `[4-7]` | | | Hypothesis & Evidence agent `[17-20]` | Compliance agent routing `[21-24]` | |
| **Accelerated Analytics** (NVIDIA · optional) | | | Stats · SPC · drift — cuML / Triton `[8·10·12]` | Lot attribution graph + significance — cuGraph `[14·15]` | RCA reasoning + RAG — NIM / NeMo `[17·18]` | | |
| **Human-in-the-Loop** (Quality Director · Teams) | | | | | | Review & decide — approve / amend / deny `[22]` | |
| **Downstream Action** (CAPA · Supplier · Dealer · NHTSA) | | | | | | NHTSA EWR check `[21]` | CAPA · SCAR · dealer advisories `[24]` |

**Governance foundation — cross-cutting, every phase:** Microsoft Entra ID
(per-agent managed identity · on-behalf-of) · Microsoft Purview (DLP · DSPM for
AI · sensitivity labels · lineage) · the 14-field hash-chained audit ledger (one
row per step `[23]`) · Microsoft Defender for IoT (OT security). Identity-scoped,
classification-aware Gold views; a regulator-replayable, tamper-evident chain.

## Day-0 prevention lane (build-station capabilities)

The second reading of "Zero Day Warranty" — catch the defect at the source so it
never becomes a claim. Station-local, on NVIDIA Metropolis, feeding the same
medallion + audit foundation.

| Capture | Infer (edge) | Verdict | Persist / feed forward |
|---|---|---|---|
| Multi-camera capture · every unit, no sampling | DeepStream pipeline · Metropolis models · ~5 ms/unit | **PASS** → continue · **FAIL** → jidoka line stop, rework | Per-VIN inspection record → Bronze; lifetime quality evidence in Purview `[9]` |

## Capability catalog (all capabilities)

Each capability mapped to its platform component, the agent-chain step(s) it
serves, and the primary persona consumer.

| Lane / owner | Capability | Platform component | Steps | Persona |
|---|---|---|---|---|
| **Consumption & Detection** | Warranty-cost heatmap & build-week cost | Power BI · Direct Lake | — | Warranty Analyst |
| | Cluster-signal threshold detection | Power BI alert · Eventstream | 1 | Warranty Analyst |
| | Chargeback-recovery & KPI dashboards | Power BI semantic model | 24 | VP Quality |
| **Data Plane** | Bronze raw landing (4 domains) | Fabric OneLake · Real-Time Hub | — | IT / Data Eng |
| | Silver canonical · VIN-conformed · tokenized | Fabric Lakehouse · Delta | — | IT / Data Eng |
| | Gold per-VIN joinable view | Fabric Direct Lake | 4-7 | Agent / all |
| | Cohort VIN resolution | Gold view · MCP tool | 3 | Agent |
| | Supplier-lot trace lookup | Gold view · MCP tool | 13 | Supplier Quality |
| | Chargeback-exposure composition | Gold view · measures | 19 | Supplier Quality |
| **Agent Orchestration** | Detect & Scope cluster | Agent Framework · Foundry | 1-3 | Quality Analyst |
| | Build-context join & hot-week detection | Agent Framework | 4-7 | Plant Ops |
| | Hypothesis & evidence-package assembly | Agent Framework | 17-20 | Quality Director |
| | Compliance routing & notification | Agent Framework | 21-24 | Compliance |
| | Typed tool-calling (OBO) & tool-approval | Foundry tool catalog | all | — |
| **Accelerated Analytics** (NVIDIA) | Cohort × station × tool × shift stats | RAPIDS cuML | 8 | Mfg Engineering |
| | SPC anomaly + tool-drift correlation | Triton Inference Server | 10·12 | Mfg Engineering |
| | Supplier-lot attribution graph + significance | RAPIDS cuGraph / cuML | 14·15 | Supplier Quality |
| | RCA specialist reasoning + RAG | NIM · NeMo Retriever | 17·18 | Quality Director |
| **Human-in-the-Loop** | Evidence-package review (approve/amend/deny) | Teams Adaptive Card | 22 | Quality Director |
| | Escalation routing & SLA | Teams · Power Automate | 22 | VP Quality |
| **Downstream Action** | NHTSA Early Warning Reporting check | Compliance tool · 49 CFR 579 | 21 | Compliance |
| | Supplier chargeback documentation | Agent + draft schema | 20 | Supplier Quality |
| | CAPA · SCAR · dealer-advisory dispatch | Teams channel · connectors | 24 | Plant Ops / Dealer |
| **Governance Foundation** | Per-agent managed identity · OBO passthrough | Microsoft Entra ID | all | IT / Security |
| | DLP · DSPM for AI · sensitivity labels · lineage | Microsoft Purview | all | Compliance |
| | 14-field hash-chained audit row per step | Audit ledger · Purview echo | 23 | Compliance / Audit |
| | OT security across plants | Microsoft Defender for IoT | — | IT / Security |
| **Day-0 Prevention** | Inline multi-camera vision capture | Metropolis · cameras | — | Line Operator |
| | Edge defect inference + jidoka stop | Jetson · DeepStream | — | Line Operator |
| | Per-VIN inspection record to medallion | Fabric Real-Time Hub | 9 | Quality / Agent |

## Reading the catalog

Capabilities with a step number are exercised inside one investigation run;
those marked `—` are always-on (data landing, dashboards, identity, OT security)
or continuous (Day-0 vision). The persona column is the primary consumer — see
[Design · persona views](01-design.md#persona-views) and the persona portals for
each role's tailored view into these capabilities.
