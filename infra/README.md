# Zero Day Warranty — Azure deployment (reference IaC)

Design-as-code for deploying the Zero Day Warranty solution into the
**`Agentic-Automotives`** resource group in the **Global_RnD_Agentic_MERCH**
subscription, reusing the shared RnD platform in `rg-iot-visionkit`.

> **Status: design only — not yet applied.** These templates encode the
> deployment design in [`docs/design/ZeroDayWarranty_Azure_Deployment.html`](../docs/design/ZeroDayWarranty_Azure_Deployment.html).

## Target environment

| Setting | Value |
|---|---|
| Subscription | `Global_RnD_Agentic_MERCH` · `3c8215d1-350c-4b83-bb7f-b5d26b4280f6` |
| Tenant | `2da40318-46be-402c-ba75-cfb1f656567d` |
| Resource group (create) | `Agentic-Automotives` · `eastus2` |
| Shared platform (reuse) | `rg-iot-visionkit` · `eastus2` |

## Create vs. reuse

**Created** in `Agentic-Automotives`: Key Vault `kv-zero-day-warranty`, managed
identity `id-zdw-warranty-agent`, and three Container Apps
(`ca-zdw-orchestrator`, `ca-zdw-mcp-warranty`, `ca-zdw-mcp-ledger`), plus the
`zdw_bronze/silver/gold` Postgres schemas.

**Reused** from `rg-iot-visionkit`: ACR `acrvisionkit4459`, Container Apps env
`cae-visionkit`, Azure OpenAI `aoai-apex-demo` (chat `gpt-4.1-mini`, embed
`text-embedding-3-small`), Postgres `pg-visionkit-4459` (db `visionkit`).

## Files

| File | Declares |
|---|---|
| `main.bicep` | subscription scope — creates the RG, invokes the project + shared-RBAC modules |
| `modules/project.bicep` | managed identity, Key Vault (+ secrets), 3 Container Apps |
| `modules/rbac.bicep` | AcrPull + Cognitive Services OpenAI User on the shared ACR / AOAI |
| `main.parameters.json` | the environment values (no secrets) |
| `scripts/postgres-schemas.sql` | medallion schemas + append-only audit ledger |

## Identity & RBAC

One user-assigned managed identity is the principal for all three apps:

- **AcrPull** on `acrvisionkit4459` — pull images
- **Cognitive Services OpenAI User** on `aoai-apex-demo` — keyless model calls
- **Key Vault Secrets User** on `kv-zero-day-warranty` — read secrets

No AOAI key is stored. App settings reference Key Vault secrets via managed
identity.

## Deploy (when authorized)

```bash
# 1. Auth + select subscription
az login --tenant 2da40318-46be-402c-ba75-cfb1f656567d
az account set -s 3c8215d1-350c-4b83-bb7f-b5d26b4280f6

# 2. Build + push images to the shared ACR
az acr login -n acrvisionkit4459
docker build -t acrvisionkit4459.azurecr.io/zdw/orchestrator:0.1.0 .   # + mcp-warranty, mcp-ledger
docker push acrvisionkit4459.azurecr.io/zdw/orchestrator:0.1.0

# 3. Deploy (creates RG + project resources + shared RBAC)
DB_URL=$(az keyvault secret show --vault-name kv-home-agent -n database-url --query value -o tsv)
az deployment sub create -l eastus2 \
  -f infra/main.bicep \
  -p infra/main.parameters.json \
  -p databaseUrl="$DB_URL"

# 4. Create the medallion schemas + append-only audit table
psql "$DB_URL" -f infra/scripts/postgres-schemas.sql
```

## Validate the template (when az/bicep is available)

```bash
az bicep build --file infra/main.bicep
az deployment sub validate -l eastus2 -f infra/main.bicep -p infra/main.parameters.json -p databaseUrl=dummy
az deployment sub what-if  -l eastus2 -f infra/main.bicep -p infra/main.parameters.json -p databaseUrl=dummy
```

## Hardening for stage / prod

- Private endpoints on Key Vault, ACR, AOAI, and Postgres; internal-only
  Container Apps ingress.
- Replace the `database-url` password with Entra DB authentication (token via the
  managed identity).
- Customer-managed keys; Microsoft Purview audit echo; Defender for Cloud.
- Production data plane on Microsoft Fabric OneLake instead of Postgres.
