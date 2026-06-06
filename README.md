# Zero Day Warranty

An agentic automotive warranty **root-cause investigation**. A single
orchestrator agent joins connected-vehicle warranty claims back to factory build
history per VIN, surfaces the statistically significant
`cohort × station × tool × supplier-lot` interactions that drive a warranty
cluster, and produces a supplier **chargeback evidence package** — collapsing an
8–12 week / 6-team / ~440 person-hour manual RCA into roughly **12 minutes**.

> Reference-scenario outcome: **$4.2M** attributable warranty exposure →
> **$2.8M** recovered (~**340%** over the manual chargeback baseline), with a
> 100% hash-chained audit ledger and a Quality-Director human-in-the-loop gate.
>
> All currency figures are *reference-scenario figures* — synthetic, derived
> from public industry benchmarks. They are not Toyota claims.

This solution follows the conventions of the
[APEX](https://github.com/KevenWMarkham/apex) delivery accelerator (medallion
data plane, 14-field hash-chained audit ledger, YAML scenario/agent manifests,
seven-cluster agent chain).

## Start here

```bash
python zdw.py                # framework overview
python zdw.py run            # run the 24-step chain on the synthetic dataset
python zdw.py run --json     # emit the evidence package + ledger as JSON
python zdw.py calc           # print the reference-scenario calculations
python zdw.py validate       # validate manifests + verify the hash chain
python zdw.py roadmap        # phases + sprint progress (from the backlog)
python zdw.py sprints        # every backlog story as a checkbox
python zdw.py checklist      # deployment validation matrix (built/deployed/tested)
```

Delivery is planned in `backlog/roadmap.yaml` (4 phases / 12 sprints) and driven
by the sprint orchestrator above; see [`docs/design/ZeroDayWarranty_Roadmap.html`](docs/design/ZeroDayWarranty_Roadmap.html).

### Spin up the next scenario

To generate another Service-Scenario in this pattern, give Claude
[`docs/SCENARIO_PLAYBOOK.md`](docs/SCENARIO_PLAYBOOK.md) plus a one-line idea —
it has the full context (conventions, the canonical 24-step chain, the artifact
inventory, and the scenario library in [`docs/reference/`](docs/reference/)) to
build the rest.

`python zdw.py run` prints the discovered suspect supplier lot, the hot
station/tool, the significance test, the root-cause hypothesis, the chargeback
financials, and the audit-ledger status.

### Develop

```bash
uv venv && uv pip install pydantic pyyaml pytest mypy ruff types-PyYAML
pytest                  # 50 tests
ruff check . && ruff format --check .
mypy src
```

## The two readings of "Zero Day Warranty"

1. **Zero-day investigation latency** — when a warranty cluster emerges,
   identify the root cause in minutes rather than weeks. *Served by the 24-step
   agent chain in this repo.*
2. **Day-0 detection** — catch the defect at the build floor before the vehicle
   ships (NVIDIA Metropolis + DeepStream + Jetson inline vision). *Described in
   the architecture; out of scope for this reference implementation.*

## The 24-step chain · seven functional clusters

| # | Cluster | Steps | Platform component |
|---|---|---|---|
| 1 | Detect & Scope | 1–3 | Microsoft Agent Framework |
| 2 | Build context | 4–7 | Microsoft Fabric · Gold views |
| 3 | Statistical tests | 8 | NVIDIA RAPIDS cuML *(GPU)* |
| 4 | Quality + Telemetry | 9–12 | NVIDIA Triton *(GPU)* |
| 5 | Supplier attribution | 13–16 | NVIDIA RAPIDS cuGraph *(GPU)* |
| 6 | Hypothesis + Evidence | 17–20 | Agent Framework + NVIDIA NIM / NeMo Retriever |
| 7 | Compliance + HITL | 21–24 | Teams Adaptive Card + Microsoft Purview |

The GPU-marked steps run on CPU in the reference implementation; NVIDIA AI
Enterprise on Azure accelerates them in production. The logic and the audit
contract are unchanged.

## The four data domains

The agent reads a single per-VIN **Gold** view joined across four domains:

1. **Build records** — per-VIN factory history (plant, line, station, tool,
   shift, operator, supplier lot).
2. **Connected-vehicle warranty data** — field claims and failure modes per VIN.
3. **Quality events** — inspections, SPC measurements, defects per station/VIN.
4. **Assembly telemetry** — tool torque/angle traces, calibration drift,
   environmental conditions.

## Repo layout

```
zdw.py                              # top-level CLI entry point (start here)
src/zero_day_warranty/
  domains.py                        # the four data-domain models + VIN key
  medallion.py                      # Bronze->Silver->Gold per-VIN join view
  audit.py                          # 14-field hash-chained decision ledger
  stats.py                          # two-proportion z-test (no heavy deps)
  calculations.py                   # the $4.2M / $2.8M / 340% reference math
  synthetic.py                      # synthetic reference dataset generator
  chain.py                          # the 24-step / 7-cluster agent chain
  manifest.py                       # scenario / agent manifest loaders
  cli.py                            # zdw CLI
service/AXLE-WARRANTY-01/           # the service definition (APEX convention)
  scenario.yaml                     # the 24-step chain manifest
  agents/<role>/agent.yaml          # 7 agent manifests + prompts/
  use-cases/_default/               # use-case envelope + DESIGN.md
  config/hitl-thresholds.yaml       # HITL gating thresholds
  _gold/                            # Gold-view contract
catalog/agents/                     # reusable AgentSpec catalog entries
docs/
  architecture.md                   # architecture & process writeup
  design/                           # the original design pack (HTML)
tests/                              # 50 tests (pytest)
```

## Platform components

First-party Microsoft spine — Microsoft Fabric (OneLake medallion), Microsoft
Agent Framework on Azure AI Foundry (orchestration + Tool-Approval HITL),
Microsoft Purview (audit/lineage), Microsoft Entra ID (per-agent identity),
Microsoft Teams (Adaptive Card HITL), Power BI (heatmaps). NVIDIA AI Enterprise
on Azure (RAPIDS, Triton, NIM, NeMo Retriever, Metropolis) plugs in as optional
acceleration. See [`docs/architecture.md`](docs/architecture.md).

## Status

Discovery-stage reference solution · laptop substrate · mock mode.
