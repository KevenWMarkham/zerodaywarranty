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
# --- deployment target (optional; only when you intend to deploy) ---
RESOURCE GROUP:  <e.g. Agentic-Healthcare>                     # the new RG to create
SUBSCRIPTION:    <name or GUID>                                # target subscription
REGION:          <e.g. eastus2>
NETWORKING:      <public | private>                            # private for governed tenants (see §9)
```

If only the idea is given, Claude **infers** the rest from the taxonomy (§4) and
the scenario library (`docs/reference/scenario-library.csv`), states its
assumptions in one short paragraph, then generates everything in §3.

> **Non-technical teammates:** open **`docs/scenario-builder.html`** in a browser
> — it's a form that produces this exact `intake` block as a downloadable
> `scenario-request-*.md`. Hand that file to Claude Code with this playbook and
> say "build this per the playbook." (Serve the page over http to enable the
> library search; it works offline otherwise.)

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

### 3d. Infra — `infra/` (two deploy variants, both create their own RG)
- **Public** (ungoverned subs): `main.bicep` + `modules/project.bicep` —
  identity, KV, observability, ACR (Basic), AOAI, Postgres, Container Apps env +
  apps, local data-role RBAC. `main.parameters.json`.
- **Private / landing-zone-compliant** (governed subs that require private
  endpoints — e.g. Deloitte RnD APEX-M): `main-private.bicep` +
  `modules/network.bicep` + `modules/project-private.bicep` — VNet + private DNS,
  KV/ACR(**Premium**)/AOAI with public access disabled + private endpoints,
  Postgres VNet injection, VNet-integrated Container Apps env.
  `main-private.parameters.json`.
- Shared: `scripts/postgres-schemas.sql` (medallion + append-only audit),
  `scripts/azure-bootstrap.sh` (OIDC setup — only for the GitHub Actions path),
  `README.md`.
- CI/CD: `.github/workflows/ci.yml`, `deploy.yml` (gated OIDC deploy),
  `images.yml` (build → GHCR, for private-ACR import).

**See §9 for which variant to use and the exact deploy runbook** — it captures
hard-won lessons from deploying into a governed tenant.

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
  no shared dependencies; keyless identity; secrets in Key Vault. In governed
  tenants use the **private** variant (§9) so it complies with deny policies.
- **No secrets in the repo, or in chat.** Pass passwords/keys at deploy time.
  Never paste a real token/password into a prompt — if you do, revoke it.
- **Keep the invariants** in §4 — they are what make the solution auditable and
  deployable, not optional decoration.

---

## 9. Deploying to Azure — the runbook (lessons learned)

This section is the distilled, battle-tested way to actually stand a scenario up
in Azure, including the snags hit deploying Zero Day Warranty into a governed
Deloitte RnD subscription. **Read it before deploying a new RG/scenario.**

### 9.1 Choose the deploy *identity* (this is the big one)
- **Recommended: deploy as *yourself* from Azure Cloud Shell.** Your user
  account already has the rights to create resources (it's how you deploy other
  projects). This sidesteps the service-principal machinery entirely.
- **OIDC + GitHub Actions (`deploy.yml`) only works if you can create a service
  principal *and* grant it Owner.** In many enterprise tenants an **ABAC
  condition blocks assigning Owner/Contributor to a service principal**
  (`AuthorizationFailed … roleAssignments/write … ABAC condition not fulfilled`).
  If you hit that, **stop and use deploy-as-user** — don't fight it.

### 9.2 Use **Azure Cloud Shell** (`https://shell.azure.com`, Bash)
- Native, **pre-authenticated** `az`; has `az acr build` / `az acr import`; no
  `sudo`, no device-code, no WSL quirks.
- **Do not run `az` from the Windows CLI under WSL** — WSL invokes the Windows
  `az.exe`, which returns empty Microsoft Graph responses and crashes
  `az ad sp create` with `JSONDecodeError: Expecting value: line 1 column 1`.
  Cloud Shell (Linux-native az) does not have this bug.
- If you need `gh` in Cloud Shell (no sudo): download the tarball to `~/bin`, or
  authenticate non-interactively with `export GH_TOKEN=<PAT repo+workflow>`.

### 9.3 Pick the networking variant — check policy first
```bash
az policy assignment list --query "[?contains(displayName,'APEX')].displayName" -o tsv
# (drop the filter to see all). Look for "Require private endpoint" /
# "publicNetworkAccess Disabled" deny policies.
```
- **No such deny policies** → use the **public** variant (`infra/main.bicep`).
- **Deny policies present** (governed landing zone) → use the **private** variant
  (`infra/main-private.bicep`). Public-endpoint resources are rejected with
  `RequestDisallowedByPolicy`.

### 9.4 Parameterize for the new RG + scenario
Edit the parameters file you'll use (`infra/main.parameters.json` or
`infra/main-private.parameters.json`):
- `resourceGroupName` → the new RG (e.g. `Agentic-Healthcare`)
- `location` → region with AOAI quota
- `keyVaultName`, `managedIdentityName`, `containerAppsEnvName`,
  `logAnalyticsName`, `appInsightsName` → project-unique names (KV ≤ 24 chars)
- `aoaiName`, `aoaiChatDeployment`/`aoaiChatModelVersion`,
  `aoaiEmbedDeployment`/`…Version` → confirm the model **version exists in the
  region** (`az cognitiveservices account list-models` after the account exists,
  or check quota first)
- ACR / Postgres names get a deterministic `uniqueString` suffix automatically.

### 9.5 Run it (Cloud Shell, deploy-as-user)
```bash
git clone https://github.com/<owner>/<repo>.git && cd <repo>
az account set -s <subscription>

# 1) Provision (pick ONE template)
az deployment sub create -n <name> --location <region> \
  --template-file infra/main-private.bicep \           # or infra/main.bicep
  --parameters infra/main-private.parameters.json \
  --parameters pgAdminPassword='<strong-secret>'

# 2) Images
#   Public ACR:  az acr build --registry <acr> --image zdw/<svc>:<tag> --target <svc> .
#   Private ACR: build on GitHub then import server-side (a private ACR can't be
#   pushed from a public shell):
gh workflow run "Build images (GHCR)" --repo <owner>/<repo> -f image_tag=<tag>
#   (make the 3 GHCR packages public first, or pass --username/--password)
ACRNAME=$(az acr list -g <RG> --query "[0].name" -o tsv)   # robust; deployment output can be empty
for s in orchestrator mcp-warranty mcp-ledger; do
  az acr import --name "$ACRNAME" --source ghcr.io/<owner-lower>/zdw-$s:<tag> --image zdw/$s:<tag>
done
az acr repository list --name "$ACRNAME" -o tsv            # verify the 3 images landed

# 3) Roll the apps to the images + smoke test
for s in orchestrator mcp-warranty mcp-ledger; do
  az containerapp update -g <RG> -n "ca-zdw-$s" --image "$ACR/zdw/$s:<tag>"
done
FQDN=$(az containerapp show -g <RG> -n ca-zdw-orchestrator --query properties.configuration.ingress.fqdn -o tsv)
curl -s "https://$FQDN/run"        # expect: "ledger_rows": 24, "chain_verified": true

# 4) (optional) data plane: apply the medallion + audit schema
#    psql "$DATABASE_URL" -f infra/scripts/postgres-schemas.sql
```
The `/run` smoke test uses the built-in **synthetic** dataset, so it proves the
app without the database. Then flip the `built/deployed/tested` flags in
`backlog/roadmap.yaml` and confirm `python zdw.py checklist` shows green.

### 9.6 Gotchas → fixes (the hard-won list)
| Symptom | Cause | Fix |
|---|---|---|
| `az ad sp create` → `JSONDecodeError: Expecting value` | Windows `az.exe` under WSL | run in **Cloud Shell** |
| `AuthorizationFailed … roleAssignments/write … ABAC` | tenant blocks granting Owner to an SP | **deploy as yourself**, skip OIDC |
| `No subscriptions found for ***` in the OIDC run | the SP has no role on the subscription | admin grants the SP Owner, or deploy-as-user |
| `RequestDisallowedByPolicy` (KV/ACR/AOAI public) | governed landing zone | use the **private** variant (§9.3) |
| can't push image to ACR from Cloud Shell | private ACR (public disabled) | build on GitHub → `az acr import` (§9.5) |
| ACR private endpoint won't create | ACR is Basic | ACR must be **Premium** for PE (the private module sets this) |
| Bicep `BCP178` in the apps `for`-loop | iterated array referenced a runtime prop (`acr…loginServer`) | keep the array static; build the value in the loop body |
| AOAI deploy fails on model version | version not available in region | set `aoaiChatModelVersion` to an available one |
| `MANIFEST_UNKNOWN: …:<tag> is not found` on the apps | apps are created in the same deploy that creates the ACR, before images exist | **two-phase**: deploy `-p deployApps=false`, build+import images, then redeploy (`deployApps` defaults true) |
| AOAI `AccountProvisioningStateInvalid … state Accepted` | Cognitive Services provisioning race | re-run the deployment (idempotent) |
| `az acr import` → 401/403 `DENIED` from ghcr | the GHCR package is private | make the 3 packages public, or `az acr import … --username <gh-user> --password <PAT read:packages>` |
| `Registry names may contain only alphanumeric…` on import | `acrLoginServer` deployment output came back empty | get the name directly: `ACRNAME=$(az acr list -g <RG> --query "[0].name" -o tsv)` |
| container app revision won't start (private) | app reads KV secrets at startup; VNet→KV private link not resolving | verify KV private endpoint + DNS, or make those secrets optional for a synthetic-only smoke test |
| `gh` device-code never arrives | it's terminal-based, not a phone push | type the `XXXX-XXXX` from the terminal, or use `GH_TOKEN` |

### 9.7 New-deployment checklist
- [ ] Cloud Shell open, `az account set -s <sub>`
- [ ] policies checked → variant chosen (public / private)
- [ ] parameters file updated (RG, names, region, model version)
- [ ] `az deployment sub create` succeeded
- [ ] images built (GHCR) + imported (or `az acr build` for public ACR)
- [ ] apps rolled to the image; `curl /run` → `chain_verified: true`
- [ ] backlog gates flipped; `zdw checklist` green
- [ ] (prod) Postgres schema applied; secrets rotation + Purview audit export planned
