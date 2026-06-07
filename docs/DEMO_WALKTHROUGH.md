# Zero Day Warranty — Demo Walk-Through Script

A presenter's script for demoing the **deployed** Zero Day Warranty solution end
to end: the live portal in Azure, the 24-step agent chain, the human approval
gate, and the tamper-evident audit trail.

| | |
|---|---|
| **Audience** | Quality / engineering leadership + their data & platform partners |
| **Duration** | 15–20 min (core) · 30 min with the build/extensibility act |
| **Format** | Live — one browser tab + one terminal |
| **Status** | Discovery · all figures synthetic (reference scenario, not client data) |

> **Live portal:**
> `https://ca-zdw-orchestrator.<env>.eastus2.azurecontainerapps.io/portal`
>
> The app scales to zero — **warm it 30s before you start** (open the link or
> `curl` `/health`) so the first click isn't a cold start.

---

## Pre-flight (do this before the room is watching)

```bash
# the deployed orchestrator
export ZDW_URL="https://ca-zdw-orchestrator.<env>.eastus2.azurecontainerapps.io"

# 1) warm the app + confirm the live build (look for "portal":"/portal")
curl -s "$ZDW_URL/health" | python -m json.tool

# 2) pre-open these browser tabs:
#    - $ZDW_URL/portal                      (Swim Lane Views — live)
#    - docs/design/ZeroDayWarranty_Persona_Portals.html
#    - docs/design/ZeroDayWarranty_Architecture_Diagrams.html
#    - docs/design/ZeroDayWarranty_Roadmap.html

# 3) (optional) have the local CLI ready as a fallback if Wi-Fi dies
.venv/bin/python zdw.py run
```

Checklist: portal loads · `/health` shows `"portal":"/portal"` · terminal has
`$ZDW_URL` set · design-pack tabs open.

---

## Act 1 — The moment (2 min) · *set the stakes before any tech*

> "A warranty cluster just lit up — a brake-actuator failure mode trending on
> connected vehicles. Today, finding the root cause means **6 teams, 8–12 weeks,
> and ~$88K of investigation cost per cluster** — pulling claims, matching VINs
> to build records, chasing station and supplier-lot data across systems. By the
> time you have proof, the chargeback window may be closing and more cars have
> shipped."

> "Watch what happens when a single governed agent does that join in minutes —
> with the evidence sealed so a regulator could replay it."

**Talking point:** the name is a double meaning — *zero-day* recovery of warranty
exposure, **and** Day-0 prevention at the build station so the defect never
becomes a claim.

---

## Act 2 — The live run (3 min) · *prove it runs, in Azure, right now*

Run the deployed chain:

```bash
curl -s "$ZDW_URL/run" | python -m json.tool
```

Narrate the result as it returns (these are the figures it produces):

- **Suspect lot:** `LOT-7743` · **hot station / tool:** `STATION-07 / TOOL-TQ-07`
  · **build weeks:** 12–13
- **Warranty rate:** **6.15% vs 2.53% baseline — a 2.4× rate**,
  **p = 1.0e-06** (significant)
- **Confidence:** 99% · **wall-clock:** ~12 min (vs 8–12 weeks)
- **Ledger:** 24 sealed rows, **hash chain VERIFIED**

> "That's the whole investigation — detect, join build context, run the
> statistics, attribute the supplier lot, build the evidence package, price the
> chargeback — collapsed from a quarter of work into one traceable run."

*(Prefer a script over JSON? `\.venv/bin/python zdw.py run` prints the same as a
clean summary.)*

---

## Act 3 — The Swim Lane Views portal (5 min) · *the heart of the demo*

Open **`$ZDW_URL/portal`**. This page is rendered **live from the run you just
triggered** — every number is the real output, sealed to the audit ledger.

> "One investigation, eight lanes — each tab is the same case seen from that
> owner's seat: the steps it owns, its KPIs, the decision it sealed, and how it
> hands off to the next lane."

Click through the tabs (≈30s each — hit the highlighted ones if short on time):

1. **Consumption & Detection** — where the signal is seen and the recovery KPI
   lands. *117 claims in the cluster → cohort scoped.*
2. **Data Plane** *(highlight)* — the per-VIN join. Bronze→Silver→Gold makes
   build, warranty, quality and telemetry answerable as one classification-aware
   view. *117 VINs joined; exposure composed.*
3. **Agent Orchestration** *(highlight)* — the 24-step orchestrator, **one sealed
   audit row per step**, single human gate at step 22.
4. **Accelerated Analytics** — the statistical core: the **2.4× rate ratio**,
   p-value, 304 SPC anomalies, 8.9% tool drift. *(NVIDIA-optional — same math on
   CPU.)*
5. **Human-in-the-Loop** *(highlight)* — the single approval gate; the decision
   and approver are sealed.
6. **Downstream Action** — NHTSA EWR check, supplier chargeback docs, CAPA / SCAR
   / dealer advisories.
7. **Governance Foundation** *(highlight)* — identity, Purview, and the **24-row,
   hash-chained, VERIFIED** audit trail under every step.
8. **Day-0 Prevention** — inline vision + jidoka at the station, feeding the same
   medallion.

> "Notice the phase strip on each lane — Detect → Act — lights up only the steps
> that lane owns. That's the same picture as the master swim-lane diagram, but
> drilled into one lane at a time."

---

## Act 4 — Personas (3 min) · *who lives in this every day*

Open **`ZeroDayWarranty_Persona_Portals.html`**. Hit 3–4 tabs:

- **VP Quality** — program ROI across the plant network (recovery, throughput,
  trust).
- **Quality Director** *(highlight)* — the HITL approval queue; each evidence
  package arrives as a Teams Adaptive Card.
- **Supplier Quality Engineer** — attribution + chargeback / SCAR pipeline.
- **Compliance & Regulatory Officer** — the audit ledger and NHTSA EWR queue.

> "Same governed solution, a tailored surface for each role — every view is an
> identity-scoped slice of the same Gold view and the same evidence."

---

## Act 5 — Trust: the human gate + the sealed record (3 min) · *the differentiator*

**The approval card** — show the exact Adaptive Card the Quality Director sees:

```bash
curl -s "$ZDW_URL/hitl-card" | python -m json.tool
```

> "Nothing acts on the company's behalf without a human. The agent assembles the
> evidence and hands the director an approve / amend / deny card — and the
> decision itself becomes part of the record."

**The audit chain** — every one of the 24 steps writes a 14-field,
hash-chained row (model, prompt, policy versions, inputs, tools, the decision,
the approver). The portal's **Governance** tab shows it **VERIFIED** — tamper any
row and the chain breaks. *"That's what makes this regulator-replayable."*

---

## Act 6 — The value (1 min) · *land the number*

| | Manual today | Zero Day Warranty |
|---|---|---|
| Time to evidence | 8–12 weeks | **~12 minutes** |
| Investigation cost | ~$88K / cluster | one governed run |
| Attributable exposure | — | **$4,212,000** |
| Recovery target | $631,800 (baseline) | **$2,822,040 — +347%** |
| Auditability | spreadsheets & email | **24-row hash-chained ledger, VERIFIED** |

> "Faster, larger, and provable — and the same platform prevents the next one at
> the build station."

---

## Act 7 — How it's built & extended (optional, 5 min) · *for the technical buyer*

- **Architecture** — open `ZeroDayWarranty_Architecture_Diagrams.html`: Agent
  Framework / Foundry orchestration, Microsoft Fabric medallion, Azure OpenAI,
  optional NVIDIA acceleration, Teams + Purview.
- **Runs in your Azure** — self-contained resource group, managed identity
  (keyless / on-behalf-of), private networking; the portal you just used is a
  Container App in that RG.
- **Repeatable factory** — `docs/SCENARIO_PLAYBOOK.md` + `scenario-builder.html`
  + the 760+ scenario library: drop in a new Service-Scenario idea and the same
  24-step pattern, design pack, infra, and swim-lane views are generated.
- **Delivery plan** — open `ZeroDayWarranty_Roadmap.html`: 4 phases / 12 sprints
  with built → deployed → tested gates (all green).

> "This isn't a one-off demo — it's an accelerator. The same pattern spins up the
> next scenario in your portfolio."

---

## Appendix A — Live command cheat-sheet

```bash
export ZDW_URL="https://ca-zdw-orchestrator.<env>.eastus2.azurecontainerapps.io"

curl -s "$ZDW_URL/health"     | python -m json.tool   # config + portal marker
curl -s "$ZDW_URL/run"        | python -m json.tool   # full 24-step run
curl -s "$ZDW_URL/hitl-card"  | python -m json.tool   # the Teams approval card
open  "$ZDW_URL/portal"                                # Swim Lane Views (live)
```

Local fallback (no network needed):

```bash
.venv/bin/python zdw.py run        # the chain, as a summary
.venv/bin/python zdw.py validate   # manifests valid + ledger VERIFIED
.venv/bin/python zdw.py lanes      # the swim-lane views as Markdown
```

## Appendix B — Likely questions

- **"Is this our data?"** No — fully synthetic reference scenario; the figures are
  illustrative, the mechanics are real.
- **"How does it not act on its own?"** Single HITL gate at step 22; nothing
  downstream fires without an approve.
- **"How do we trust the output?"** Every step is a sealed, hash-chained audit row
  — show the Governance tab / `/hitl-card`.
- **"Do we need NVIDIA GPUs?"** No — acceleration is optional; the same math and
  audit contract run on CPU.
- **"Can it do *our* scenario?"** Yes — that's the playbook + scenario builder;
  the pattern is the product.

## Appendix C — Reset between runs

The run is deterministic on the synthetic dataset, so you can re-run freely —
every `/run` and `/portal` load reproduces the same figures. If the app cold-
starts (scale-to-zero), the first request waits ~10–15s; just refresh once.
