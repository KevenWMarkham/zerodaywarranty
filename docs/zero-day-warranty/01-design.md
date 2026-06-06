# Zero Day Warranty — Design

Architecture, data plane, the agent chain, governance, capabilities, and the
per-persona views. The polished diagrams live in
[`../design/ZeroDayWarranty_Architecture_Diagrams.html`](../design/ZeroDayWarranty_Architecture_Diagrams.html)
and the swim-lane / portal HTML; this is the text-native version.

## 1. The four data domains

The agent reads one **per-VIN Gold view** joined across four source domains —
each already exists in a typical OEM estate; what's missing is the joinable view.

| Domain | Contents | Source |
|---|---|---|
| **Build records** | per-VIN factory history: plant, line, station, tool, shift, operator, supplier lot, build week | MES · ERP |
| **Connected-vehicle warranty** | claims, failure modes, fault codes, build-to-claim months, cost | Toyota Connected · Azure |
| **Quality events** | inspections, SPC measurements, defects, holds, rework (per station/VIN) | QMS · plant systems |
| **Assembly telemetry** | tool torque/angle traces, calibration drift, cycle times, environment | SCADA · historian · IoT |

VIN is the single conformed join key.

## 2. Medallion data plane

```
Source systems         Bronze              Silver                   Gold
(MES/ERP, Connected, → raw landing     →   canonical, VIN-      →   per-VIN joinable view
 QMS, SCADA)           (schema-on-read)     conformed, typed         Build × Warranty
                                            (PII tokenized)          × Quality × Telemetry
```

- **Bronze** — raw, immutable landing.
- **Silver** — canonical, VIN-conformed, typed models (`domains.py`).
- **Gold** — agent-safe, classification-aware per-VIN view
  (`medallion.py → GoldVehicleView`). Production target: Microsoft Fabric
  OneLake Direct Lake; RnD substrate: Postgres schemas `zdw_bronze/silver/gold`.

## 3. The 24-step agent chain · seven clusters

A single orchestrator drives 24 steps in seven functional clusters. Each step
emits one 14-field audit row; the chain pauses at step 22 for the HITL gate.

| # | Cluster | Steps | Platform component |
|---|---|---|---|
| 1 | Detect & Scope | 1–3 | Microsoft Agent Framework |
| 2 | Build context | 4–7 | Microsoft Fabric · Gold views |
| 3 | Statistical tests | 8 | NVIDIA RAPIDS cuML *(GPU)* |
| 4 | Quality + Telemetry | 9–12 | NVIDIA Triton *(GPU)* |
| 5 | Supplier attribution | 13–16 | NVIDIA RAPIDS cuGraph *(GPU)* |
| 6 | Hypothesis + Evidence | 17–20 | Agent Framework + NVIDIA NIM / NeMo Retriever |
| 7 | Compliance + HITL | 21–24 | Teams Adaptive Card + Microsoft Purview |

The 24 steps map onto the APEX canonical chain (W1 foundation 1–10, W2 pilot
11–18, W3 scale 19–24 — see [`../../templates/canonical-24-step-chain.yaml`](../../templates/canonical-24-step-chain.yaml)).
GPU-marked steps run on CPU in the reference; the logic and audit contract are
identical. Statistical attribution applies a multiple-testing correction
(Bonferroni / Benjamini-Hochberg) so a claim survives the family of
week × station × lot tests, not just one.

## 4. The audit ledger

Every step produces a **14-field decision row** (APEX Sellers Guide §11.2) plus
an explicit **hash chain**: each sealed row carries `prev_link` (the previous
row's HMAC-SHA256 signature). `verify_chain()` confirms every signature and that
the chain is unbroken — tampering with any row breaks it from that point forward.
Append-only; overwrites refused. Production: a Delta/WORM table with the signing
key in Key Vault, echoed to Microsoft Purview.

## 5. Human-in-the-loop

One enforceable gate (step 22): the evidence package is delivered to the Quality
Director as a Microsoft Teams Adaptive Card — **approve / amend / deny** — before
any external effect (chargeback issuance, downstream notification). Identity
passthrough (OBO) scopes downstream calls to the originating user. Thresholds in
[`../../service/AXLE-WARRANTY-01/config/hitl-thresholds.yaml`](../../service/AXLE-WARRANTY-01/config/hitl-thresholds.yaml).

## 6. Capability swim lanes

Capabilities organized by **owner** (rows) across the seven **phases** (columns),
over an always-on governance foundation:

- **Consumption & Detection** — Power BI heatmap → cluster signal; KPI dashboards.
- **Data Plane** — Bronze/Silver/Gold; cohort VIN resolution; supplier-lot trace.
- **Agent Orchestration** — the four cluster agents on Agent Framework.
- **Accelerated Analytics** — RAPIDS / Triton / NIM (optional NVIDIA).
- **Human-in-the-Loop** — Teams review + escalation.
- **Downstream Action** — NHTSA EWR check, chargeback docs, CAPA/SCAR/dealer.
- **Governance foundation** (cross-cutting) — Entra identity (OBO), Purview
  DLP/lineage, the hash-chained audit ledger, Defender for IoT.
- **Day-0 prevention** — Metropolis + DeepStream + Jetson at the build station.

Full capability catalog (30+ capabilities → component, step, persona) in
[`../design/ZeroDayWarranty_Capability_SwimLanes.html`](../design/ZeroDayWarranty_Capability_SwimLanes.html).

## 7. Persona views

Nine tailored portals (mockups in
[`../design/ZeroDayWarranty_Persona_Portals.html`](../design/ZeroDayWarranty_Persona_Portals.html)):

| Persona | Their view |
|---|---|
| VP Quality | program ROI rollup across plants |
| Quality Director | HITL approval queue + evidence + approve/amend/deny |
| Supplier Quality | attributed lots, SCAR pipeline, recovery |
| Warranty Analyst | warranty-cost heatmap + live cluster feed |
| Plant Ops | station / tool / shift hot-spots |
| Mfg Engineering | calibration drift + SPC anomalies |
| IT / Data Eng | medallion freshness + MCP tool catalog |
| Compliance | NHTSA EWR queue + audit-ledger explorer |
| Line Operator (Day-0) | live jidoka pass/fail verdict feed |

## 8. Platform components

First-party Microsoft spine — Fabric (OneLake medallion), Agent Framework on
Azure AI Foundry (orchestration + Tool-Approval HITL), Purview (audit/lineage),
Entra ID (per-agent identity), Teams (Adaptive Card), Power BI (heatmaps).
Optional NVIDIA AI Enterprise on Azure (RAPIDS, Triton, NIM, NeMo Retriever,
Metropolis) accelerates the analyze/attribute/hypothesis/Day-0 paths. All
components run inside the customer's Azure tenant.
