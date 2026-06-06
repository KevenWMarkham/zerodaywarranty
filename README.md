# Zero Day Warranty

An agentic automotive warranty **root-cause investigation** scenario. A single
orchestrator agent joins connected-vehicle warranty claims back to factory build
history per VIN, surfaces the statistically significant
`cohort × station × tool × supplier-lot` interactions that drive a warranty
cluster, and produces a supplier **chargeback evidence package** — collapsing an
8–12 week / 6-team / ~440 person-hour manual RCA into roughly **12 minutes**.

> Reference scenario outcome: **$4.2M** attributable warranty exposure →
> **$2.8M** recovered (~**340%** over the manual chargeback baseline), with a
> hash-chained audit ledger and a Quality-Director human-in-the-loop gate.

This repository follows the conventions of the
[APEX](https://github.com/KevenWMarkham/apex) delivery accelerator.

## Design documents

The authoritative design lives under [`docs/design/`](docs/design/):

- **Architecture & Process Diagrams** — end-to-end component architecture, the
  Day-0 prevention layer, current-state vs. agentic-state process flows.
- **Calculations & References** — how every figure is derived and its source.

## Status

Discovery-stage reference solution. Build in progress.
