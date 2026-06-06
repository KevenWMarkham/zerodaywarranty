# Zero Day Warranty — Design Pack

The discovery-stage design pack for the Zero Day Warranty agentic scenario. All
documents are self-contained HTML; open them in a browser. All currency figures
are reference-scenario figures (synthetic) — not Toyota baseline claims.

| Document | What it covers |
|---|---|
| [`ZeroDayWarranty_Architecture_Diagrams.html`](ZeroDayWarranty_Architecture_Diagrams.html) | End-to-end component architecture, the Day-0 prevention layer, and current-state vs. agentic-state process flows. Tabs for the Microsoft and NVIDIA stacks. |
| [`ZeroDayWarranty_Calculations_and_References.html`](ZeroDayWarranty_Calculations_and_References.html) | How every figure is derived and its source — the $88K manual baseline, the ~12 min agent wall-clock, and the $4.2M / $2.8M / ~340% chargeback scenario. |
| [`ZeroDayWarranty_Capability_SwimLanes.html`](ZeroDayWarranty_Capability_SwimLanes.html) | **Swim lanes of all capabilities** — owners × phases master lane, the Day-0 prevention lane, and a full capability catalog (30+ capabilities with platform component, agent step, and persona owner). |
| [`ZeroDayWarranty_Persona_Portals.html`](ZeroDayWarranty_Persona_Portals.html) | **Persona portals** — a tailored view into the solution for each of nine personas (VP Quality, Quality Director, Supplier Quality, Warranty Analyst, Plant Ops, Mfg Engineering, IT/Data Eng, Compliance, Line Operator / Day-0). |
| [`ZeroDayWarranty_Azure_Deployment.html`](ZeroDayWarranty_Azure_Deployment.html) | **Azure deployment design** — deploys into resource group `Agentic-Automotives` (Global_RnD_Agentic_MERCH subscription), reusing the shared `rg-iot-visionkit` platform (ACR, Container Apps env, Azure OpenAI, Postgres). Topology, create/reuse, identity & RBAC, medallion-on-Postgres, model mapping, secrets, deploy sequence. Reference Bicep in [`../../infra/`](../../infra/). |

## Reading order

1. **Architecture** — what the components are and how the process flows.
2. **Capability swim lanes** — every capability, mapped to owner and phase.
3. **Persona portals** — what each role sees and decides.
4. **Calculations & references** — the math and the sources.

A `docs/architecture.md` summary and a runnable reference implementation also
live in this repository (see the top-level `README.md`).
