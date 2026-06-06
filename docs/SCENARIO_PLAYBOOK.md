# APEX Service-Scenario Playbook

**Give Claude this file plus a one-line scenario idea, and it generates a
complete, runnable Service-Scenario solution** that mirrors the Zero Day
Warranty reference build (this repository). It is the single context document for
spinning up the next scenario from `docs/reference/APEX-Scenario-Chains.xlsx`.

---

## 1. How to use this (the simple part)

Fill in the intake block — at minimum the **idea** — and hand it to Claude with
this file:

```intake
SCENARIO IDEA:   <one or two sentences: the moment + the agentic solution>
INDUSTRY:        <rc | hls | er | axle | tmt | th | ice>      # optional — infer if blank
SERVICE CODE:    <e.g. AXLE-QMS-02>                            # optional — infer/assign if blank
DOMAIN:          <e.g. Quality & Compliance>                   # optional
PERSONA (HITL):  <who approves at the gate>                    # optional
KPI / OUTCOME:   <the measurable result>                       # optional
DEVICE(S):       <edge/vision/none>                            # optional
```

If only the idea is given, Claude **infers** the rest from the taxonomy (§4) and
the scenario library (`docs/reference/scenario-library.csv`), states its
assumptions in one short paragraph, then generates everything in §3.

Search the library first to reuse a service code or avoid a duplicate:

```bash
python zdw.py scenarios --search <term>      # free-text across id/title/brief/kpi
python zdw.py scenarios --industry axle      # filter by service-code prefix
python zdw.py scenarios --show <scenario_id> # full detail for one
```

After generating a scenario, register it back into the library so the workbook
stays the source of truth:

```bash
python zdw.py scenarios --check   # is the repo scenario in the library? (exit 1 if not)
python zdw.py scenarios --sync    # append missing repo scenarios to the CSV + xlsx
```

> Example one-liner: *"A grid-reliability agent that traces transformer failures
> back to load history and weather to recommend predictive maintenance."* →
> Claude maps this to industry `er`, a Network/Asset domain, derives a service
> code, and builds the full solution.

---

## 2. What "done" means (definition of done)

A generated scenario is complete when **all** of these are true — the same gates
this repo holds itself to:

- `ruff check .` clean · `ruff format --check` clean · `mypy src` clean
- `pytest` green (new tests included)
- `python zdw.py validate` passes (manifests load; 24 audit rows; hash chain VERIFIED)
- `python zdw.py roadmap` / `checklist` render (a backlog entry exists)
- The design pack renders (HTML opens; tags balanced)
- All currency/impact figures are clearly labelled **synthetic reference
  figures**, parameterized in the calculation module

Deployments are gated **built → deployed → tested** in the backlog and only count
when all three are checked (see `backlog/roadmap.yaml` + `zdw checklist`).

---

## 3. What Claude generates (artifact inventory)

Mirror this repository's structure, substituting the new scenario's names.
`<pkg>` = product name in snake_case; `<CODE>` = service code; `<scenario_id>` =
`<industry>-<area>-<slug>`.

### 3a. Runnable package — `src/<pkg>/`
Clone-and-adapt the Zero Day Warranty modules (they are the template):

| File | Adapt to the new scenario |
|---|---|
| `domains.py` | the scenario's **source domains** as typed Pydantic models + the **join key** |
| `medallion.py` | Bronze→Silver→Gold join keyed on that entity |
| `audit.py` | reuse **as-is** (14-field, hash-chained, append-only ledger) |
| `stats.py` | reuse + add scenario-specific tests; keep multiple-testing correction |
| `calculations.py` | the scenario's reference math (baseline cost, wall-clock, ROI) — parameterized |
| `synthetic.py` | deterministic dataset that **plants the signal** the chain must find |
| `chain.py` | the **24-step orchestrator**, one audit row per step, a single HITL gate |
| `manifest.py` | reuse **as-is** (scenario/agent/catalog loaders + validators) |
| `roadmap.py` | reuse **as-is** (sprint orchestrator) |
| `cli.py` + top-level `<cli>.py` | `run · calc · validate · roadmap · sprints · checklist` |

### 3b. Service definition — `service/<CODE>/`
- `scenario.yaml` — 24-step chain (§5) + the agents list
- `agents/<role>/agent.yaml` + `prompts/<role>.md` — one per cluster/role; only
  the gate agent sets `hitl_gate: true` and `operator_obo_required: true`
- `use-cases/_default/use-case.yaml` + `DESIGN.md` — adapters, personas, KPIs,
  HITL thresholds, smoke test
- `config/hitl-thresholds.yaml` · `_gold/<code>_*.gold.yaml`
- `catalog/agents/*.yaml` — reusable `AgentSpec` entries

### 3c. Design pack — `docs/design/` (HTML, shared visual system)
Reuse the CSS/header/footer from the existing docs. Produce the set:
Architecture · Calculations & References · Capability Swim Lanes · Persona
Portals · Azure Deployment · Experts Panel · Roadmap. Keep the
classification banner and the "synthetic / not client claims" footer.

### 3d. Infra — `infra/` (design-as-code; not applied)
`main.bicep` (sub-scope, creates the RG) + `modules/project.bicep`
(self-contained: identity, KV, observability, ACR, AOAI, Postgres, Container
Apps env + apps, local RBAC) + `main.parameters.json` +
`scripts/postgres-schemas.sql` (medallion + append-only audit) + `README.md`.

### 3e. Plan — `backlog/roadmap.yaml`
4 phases / ~12 sprints; fold the Experts-Panel gaps in as stories; add the P3
deployment gates (built/deployed/tested) per component.

### 3f. CI/CD + tests
`.github/workflows/ci.yml` (ruff/mypy/pytest/validate) and `deploy.yml` (gated).
`tests/` mirroring the reference suite (domains/medallion, audit, calculations,
chain, manifests, roadmap, stats).

---

## 4. Conventions & taxonomy (from the workbook)

**Industries (service-code prefix):** `rc` Retail & Consumer · `hls` Health &
Life Sciences · `er` Energy & Resources · `axle` Automotive/Aftermarket/Mobility
· `tmt` Tech/Media/Telecom · `th` Travel & Hospitality · `ice` Industrial/
Connected Equipment.

**Domains (pick one):** Pricing & Revenue · Customer Experience · Operations &
Workforce · Risk · Fraud · Security · Quality & Compliance · Marketing & Growth ·
Clinical Care · Network & Infrastructure · Asset Maintenance · Supply Chain ·
Engineering & R&D · Channel · Partner · Dealer.

**Naming**
- Service code: `{INDUSTRY}-{AREA}-{NN}` (e.g. `AXLE-QMS-02`). Reuse an existing
  code from the library when the scenario fits one; otherwise assign the next.
- `scenario_id`: `{industry}-{slug}` (kebab-case), matching the library style.
- Agent id (catalog): `apex.{industry}.agents.{slug}`.
- Agent roles: present-tense verbs / functional cluster names (the reference uses
  `detect · context · stattest · quality · supplier · hypothesis · compliance`;
  the generic APEX set is `assess · classify · quantify · decide · act · learn`).

**Model tiers (Azure OpenAI):** chat `gpt-4.1-mini` (default), embeddings
`text-embedding-3-small`; escalate to `gpt-4o` only for heavy reasoning, `gpt-4o-mini`
for lightweight classification. Pin the model at **deploy** time, not in source.

**Always-on invariants (do not omit):** per-agent managed identity (keyless,
OBO) · 14-field hash-chained audit row per step · a single enforceable HITL gate
before any external effect · classification-aware Gold views · all figures
synthetic and labelled.

Lookups: `docs/reference/scenario-library.csv` (every scenario: id, title,
service code, domain, brief, KPI, device) and the workbook's *Featured Chains*
sheet (the richest field set — maps 1:1 to `scenario.yaml`: moment/solution/
use_case/service/personas/kpi/waves).

---

## 5. The canonical 24-step chain

Every scenario uses the same 24-step backbone — three waves. The skeleton (keys,
titles, layers, kinds) is in `templates/canonical-24-step-chain.yaml`; specialize
the titles/purposes to the scenario.

- **W1 Foundation (1–10):** SOR → Real-Time Hub → Bronze → Tokenizer → Silver
  (canonical) → Gold (semantic) → MCP server → Entra identity → LEDGER audit row
  → HITL surface.
- **W2 Pilot (11–18):** event trigger → orchestrator → Assess → Classify →
  Quantify → **HITL gate** → Act + Evidence-Write → KPI rollup.
- **W3 Scale & Fuse (19–24):** scale → fuse adjacent → fuse cross-practice →
  Purview lineage → LEDGER feedback loop → enterprise KPI.

In code, `scenario.yaml` tags each step with `cluster` (1–7) and `agent_role`,
and `chain.py` emits one audit row per step. You may **specialize** the chain
into domain clusters (as Zero Day Warranty does) as long as it stays 24 steps,
1..24, with the single HITL gate and per-step audit rows.

---

## 6. Generation procedure (what Claude does, in order)

1. **Parse the intake**; infer any blanks from §4 + the library. State
   assumptions in ≤5 lines. Derive `scenario_id`, `<CODE>`, `<pkg>`, persona,
   KPI, the source domains + join key, and which cluster holds the HITL gate.
2. **Scaffold** the package by cloning the reference modules (§3a) and adapting
   `domains.py`, `synthetic.py`, `calculations.py`, and `chain.py` to the
   scenario. Reuse `audit.py`, `manifest.py`, `roadmap.py`, `stats.py` verbatim.
3. **Author** `service/<CODE>/` (§3b): `scenario.yaml` (24 steps + agents), the
   per-role `agent.yaml` + authored prompts (>500 chars, no "TBD"), the
   use-case, HITL thresholds, Gold contract, catalog entries.
4. **Generate the design pack** (§3c) in the shared visual system.
5. **Write infra** (§3d) self-contained for the project resource group.
6. **Write the backlog** (§3e) and confirm `zdw roadmap`/`checklist` render.
7. **Add tests** (§3f) and run the gates in §2 until green.
8. **Commit** with a clear message; push to the working branch. Do **not** open a
   PR or deploy unless asked.

---

## 7. Worked example (the reference)

This repository **is** the worked example. Idea → *"A single agent joins
connected-vehicle warranty claims to factory build history per VIN and produces a
supplier chargeback evidence package."* → industry `axle`, service
`AXLE-WARRANTY-01`, `scenario_id` `axle-warranty-zero-day-root-cause`, package
`zero_day_warranty`, four domains (build/warranty/quality/telemetry) joined on
VIN, HITL gate in the `compliance` cluster, reference figures
$4.2M/$2.8M/~340%. Read these as the template to copy:
`src/zero_day_warranty/`, `service/AXLE-WARRANTY-01/`, `docs/design/`, `infra/`,
`backlog/roadmap.yaml`.

---

## 8. Guardrails

- **Synthetic only.** Never embed real client data or claims; label every figure
  a reference-scenario figure and keep the math parameterized for a later BVA.
- **Self-contained deployment.** One project resource group owns its resources;
  no shared dependencies; keyless identity; secrets in Key Vault.
- **No secrets in the repo.** Pass passwords/keys at deploy time.
- **Keep the invariants** in §4 — they are what make the solution auditable and
  deployable, not optional decoration.
