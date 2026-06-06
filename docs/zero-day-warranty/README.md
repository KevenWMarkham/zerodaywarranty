# Zero Day Warranty — documentation (Markdown)

Text-native companions to the HTML design pack in [`../design/`](../design/).
Same content, readable and diffable on GitHub.

| Doc | What it covers |
|---|---|
| [00 · Overview](00-overview.md) | The scenario in one read — the moment, the solution, the value, personas, KPIs. |
| [01 · Design](01-design.md) | Architecture, the four data domains, the 24-step / 7-cluster chain, the audit ledger, capability swim lanes, persona views. |
| [01a · Data model](data.md) | Full ERD + data dictionary — entities, attributes, keys, relationships, medallion mapping, audit schema, classification. |
| [01b · Capability swim lanes](capability-swim-lanes.md) | Every capability by owner × phase, the Day-0 prevention lane, and the full capability catalog (component · step · persona). |
| [02 · Deployment](02-deployment.md) | The self-contained Azure deployment in `Agentic-Automotives` — resources, identity/RBAC, data plane, model mapping, secrets, deploy sequence. |
| [03 · Plan](03-plan.md) | Roadmap (4 phases / 12 sprints), the sprint orchestrator, and the deployment validation gates. |
| [04 · Experts Panel](04-experts-panel.md) | Ten-expert design review, coverage matrix, and prioritized gap log. |

Reference implementation: [`../../src/zero_day_warranty/`](../../src/zero_day_warranty/) ·
Service: [`../../service/AXLE-WARRANTY-01/`](../../service/AXLE-WARRANTY-01/) ·
Backlog: [`../../backlog/roadmap.yaml`](../../backlog/roadmap.yaml).

> All currency/impact figures are **reference-scenario figures** — synthetic,
> derived from public industry benchmarks. Not Toyota baseline claims.
