# Zero Day Warranty — Azure Deployment

**Self-contained** in a single resource group, **`Agentic-Automotives`**
(eastus2), in the **Global_RnD_Agentic_MERCH** subscription. Every resource is
project-owned and created fresh — **no shared dependencies**. Reference IaC in
[`../../infra/`](../../infra/); design-as-code, **not yet applied**.

## Target environment

| Setting | Value |
|---|---|
| Subscription | `Global_RnD_Agentic_MERCH` · `3c8215d1-350c-4b83-bb7f-b5d26b4280f6` |
| Tenant | `2da40318-46be-402c-ba75-cfb1f656567d` |
| Resource group (create) | `Agentic-Automotives` · `eastus2` |
| Sharing | none — all resources created in this RG |

## Resources created (all in this RG)

| Resource | Name | Type / notes |
|---|---|---|
| Managed identity | `id-zdw-warranty-agent` | user-assigned, per-agent, keyless |
| Key Vault | `kv-zero-day-warranty` | RBAC, soft-delete + purge protection |
| Log Analytics | `log-zdw-agentic` | Container Apps + agent logs |
| Application Insights | `appi-zdw-agentic` | agent traces / metrics |
| Container Registry | `acrzdwagentic<uniq>` | Basic, MI pull (admin disabled) |
| Azure OpenAI | `aoai-zdw-agentic` | S0, keyless (Entra only) |
| ↳ chat deployment | `gpt-4.1-mini` | cap 30 |
| ↳ embed deployment | `text-embedding-3-small` | cap 50 |
| Postgres Flexible | `pg-zdw-agentic<uniq>` | Burstable B1ms, PG16, db `zdw` |
| Container Apps env | `cae-zdw-agentic` | logs → Log Analytics |
| Container Apps | `ca-zdw-orchestrator` (external), `ca-zdw-mcp-warranty`, `ca-zdw-mcp-ledger` (internal) | Consumption |
| Postgres schemas | `zdw_bronze / zdw_silver / zdw_gold` | medallion + audit ledger |

Globally-unique names (ACR, AOAI, Postgres) take a deterministic 6-char
`uniqueString()` suffix. The only external touchpoint is the Microsoft 365 Teams
surface for the HITL approval.

## Identity & RBAC

One user-assigned managed identity is the principal for all three apps; every
assignment is **local to this RG**:

| Role | Scope | Why |
|---|---|---|
| AcrPull | `acrzdwagentic<uniq>` | pull images |
| Cognitive Services OpenAI User | `aoai-zdw-agentic` | keyless model calls |
| Key Vault Secrets User | `kv-zero-day-warranty` | read secrets |

No AOAI key is stored (local auth disabled). *Hardening:* replace the Postgres
password connection string with Entra DB auth.

## Data plane

The project Postgres is the RnD lakehouse substrate; the medallion maps to
schemas in db `zdw`. The append-only audit ledger
(`zdw_gold.audit_ledger`) blocks `UPDATE`/`DELETE` via trigger (WORM-style); the
HMAC signing key lives in `kv-zero-day-warranty/audit-ledger-signing-key`. DDL:
[`../../infra/scripts/postgres-schemas.sql`](../../infra/scripts/postgres-schemas.sql).
Production target remains Microsoft Fabric OneLake (same schema names + Gold
contract).

## Model mapping

| Chain use | AOAI deployment | Cap | Steps |
|---|---|---|---|
| Orchestration + hypothesis | `gpt-4.1-mini` | 30 | all · 17–18 |
| RAG over bulletins/specs | `text-embedding-3-small` | 50 | 18 |

Model pins resolve to the AOAI deployment name at **deploy** time (app setting),
not in source. *Deploy dependency:* model quota must be available in `eastus2`.

## Secrets · `kv-zero-day-warranty`

`database-url` (composed from the new server) · `audit-ledger-signing-key`
(generated) · `aoai-endpoint` · `teams-webhook-url`. App settings reference these
as Key Vault references via the managed identity.

## Deploy sequence

```bash
# 1. Auth + select subscription
az login --tenant 2da40318-46be-402c-ba75-cfb1f656567d
az account set -s 3c8215d1-350c-4b83-bb7f-b5d26b4280f6

# 2. Deploy everything (RG + ACR + AOAI + Postgres + CAE + KV + identity + apps + RBAC)
az deployment sub create -l eastus2 -f infra/main.bicep \
  -p infra/main.parameters.json -p pgAdminPassword='<strong-secret>'

# 3. Build + push images to the project ACR (login server from output)
#    docker build/push zdw/orchestrator, zdw/mcp-warranty, zdw/mcp-ledger

# 4. Create medallion schemas + append-only audit table
psql "$(az keyvault secret show --vault-name kv-zero-day-warranty -n database-url --query value -o tsv)" \
  -f infra/scripts/postgres-schemas.sql

# 5. Smoke test -> expect 24 audit rows, chain VERIFIED
```

### Recommended path · OIDC + GitHub Actions

The supported way to provision is the gated workflow
[`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) — keyless via
Entra OIDC — after a one-time bootstrap:

```bash
# one-time: create the deployer service principal + federated creds + repo secrets
#   (run where you're logged into az AND gh)
PG_ADMIN_PASSWORD='<strong-secret>' bash infra/scripts/azure-bootstrap.sh

# then deploy: what-if first, then a real apply (approve 'production' when prompted)
gh workflow run "Deploy (Agentic-Automotives)" -f confirm=what-if-only
gh workflow run "Deploy (Agentic-Automotives)" -f confirm=DEPLOY -f image_tag=0.1.0
```

The workflow: what-if/validate → **production** environment approval → deploy
(Bicep) → build & push the three images → apply schema → smoke test. The
container images come from the multi-stage [`Dockerfile`](../../Dockerfile)
(targets `orchestrator`, `mcp-warranty`, `mcp-ledger`), each running the
stdlib HTTP app in [`server.py`](../../src/zero_day_warranty/server.py).

CI: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
(lint/type/test/validate) runs on every push/PR.

### Container app endpoints (post-deploy verification)

| App | Endpoint | Returns |
|---|---|---|
| `ca-zdw-orchestrator` | `GET /health` · `GET /run` | config booleans · full chain result (24 audit rows, `chain_verified`) |
| `ca-zdw-mcp-warranty` | `GET /tools` · `GET /gold/summary` | Gold-view tools · per-VIN summary |
| `ca-zdw-mcp-ledger` | `GET /tools` · `GET /verify` | ledger tools · hash-chain verification |

## Hardening for stage / prod

Private endpoints (KV/ACR/AOAI/PG) + internal-only ingress · Entra DB auth ·
customer-managed keys · Postgres HA/geo-redundancy · Purview audit echo + WORM
export of the ledger · data plane on Microsoft Fabric. Tracked in the
[Experts Panel gap log](04-experts-panel.md#gap-log) and sprints S11.
