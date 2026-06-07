# Zero Day Warranty — Azure deployment (reference IaC)

Design-as-code for deploying the Zero Day Warranty solution **self-contained**
into the **`Agentic-Automotives`** resource group in the
**<subscription-name>** subscription. Every resource is project-owned and
created fresh — **nothing is shared** with another resource group.

> **Status: design only — not yet applied.** These templates encode the
> deployment design in [`docs/design/ZeroDayWarranty_Azure_Deployment.html`](../docs/design/ZeroDayWarranty_Azure_Deployment.html).
> The Experts Panel ([`docs/design/ZeroDayWarranty_Experts_Panel.html`](../docs/design/ZeroDayWarranty_Experts_Panel.html))
> reviews this design and tracks the open gaps.

## Target environment

| Setting | Value |
|---|---|
| Subscription | `<subscription-name>` · `<subscription-id>` |
| Tenant | `<tenant-id>` |
| Resource group (create) | `Agentic-Automotives` · `eastus2` |
| Sharing | none — all resources created in this RG |

## Resources created (all in Agentic-Automotives)

Managed identity `id-zdw-warranty-agent` · Key Vault `kv-zero-day-warranty` ·
Log Analytics `log-zdw-agentic` · Application Insights `appi-zdw-agentic` ·
Container Registry `acrzdwagentic<uniq>` (Basic, keyless pull) · Azure OpenAI
`aoai-zdw-agentic` (+ `gpt-4.1-mini`, `text-embedding-3-small`, keyless) ·
Postgres flexible `pg-zdw-agentic<uniq>` (db `zdw`) · Container Apps env
`cae-zdw-agentic` · Container Apps `ca-zdw-orchestrator`, `ca-zdw-mcp-warranty`,
`ca-zdw-mcp-ledger` · Postgres schemas `zdw_bronze/silver/gold`.

Globally-unique names (ACR, AOAI, Postgres) take a deterministic 6-char
`uniqueString()` suffix.

## Files

| File | Declares |
|---|---|
| `main.bicep` | subscription scope — creates the RG, invokes the project module |
| `modules/project.bicep` | identity · KV (+secrets) · Log Analytics · App Insights · ACR · Azure OpenAI (+deployments) · Postgres (+db) · Container Apps env · 3 Container Apps · local RBAC |
| `main.parameters.json` | the environment values (no secrets) |
| `scripts/postgres-schemas.sql` | medallion schemas + append-only audit ledger |

## Identity & RBAC

One user-assigned managed identity is the principal for all three apps; every
role assignment is **local to this RG**:

- **AcrPull** on `acrzdwagentic<uniq>` — pull images
- **Cognitive Services OpenAI User** on `aoai-zdw-agentic` — keyless model calls
- **Key Vault Secrets User** on `kv-zero-day-warranty` — read secrets

No AOAI key is stored (account has local auth disabled).

## Deploy (when authorized)

```bash
# 1. Auth + select subscription
az login --tenant <tenant-id>
az account set -s <subscription-id>

# 2. Deploy everything (RG + ACR + AOAI + Postgres + CAE + KV + identity + apps + RBAC)
az deployment sub create -l eastus2 \
  -f infra/main.bicep \
  -p infra/main.parameters.json \
  -p pgAdminPassword='<strong-secret>'

# 3. Build + push images to the project ACR (login server from deployment output)
ACR=$(az deployment sub show -n main --query properties.outputs.acrLoginServer.value -o tsv)
az acr login -n "${ACR%%.*}"
docker build -t "$ACR/zdw/orchestrator:0.1.0" .   # + mcp-warranty, mcp-ledger
docker push "$ACR/zdw/orchestrator:0.1.0"

# 4. Create medallion schemas + append-only audit table
DB_URL=$(az keyvault secret show --vault-name kv-zero-day-warranty -n database-url --query value -o tsv)
psql "$DB_URL" -f infra/scripts/postgres-schemas.sql
```

## Validate the template (when az/bicep is available)

```bash
az bicep build --file infra/main.bicep
az deployment sub validate -l eastus2 -f infra/main.bicep -p infra/main.parameters.json -p pgAdminPassword=dummy
az deployment sub what-if  -l eastus2 -f infra/main.bicep -p infra/main.parameters.json -p pgAdminPassword=dummy
```

## Deploy-time dependencies & hardening

- **AOAI quota.** Creating the account + deployments needs model quota for the
  subscription in `eastus2`. Request an increase or pin to a region with capacity.
- **Model versions.** `aoaiChatModelVersion` / `aoaiEmbedModelVersion` must be
  versions available in the region; adjust the parameters if a deploy validation
  reports an unavailable version.
- **Hardening for stage/prod.** Private endpoints (KV, ACR, AOAI, Postgres) +
  internal-only ingress; Entra DB auth instead of the password connection string;
  customer-managed keys; Postgres HA/geo-redundant backup; Microsoft Purview
  audit echo; production data plane on Microsoft Fabric OneLake. See the Experts
  Panel gap log.
