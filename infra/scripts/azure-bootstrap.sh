#!/usr/bin/env bash
#
# One-time setup so the gated CD workflow (.github/workflows/deploy.yml) can
# deploy to Azure via Entra OIDC — no client secrets stored anywhere.
#
# Creates: an Entra app registration + service principal, two federated
# credentials (main branch + the `production` environment), an Owner role
# assignment on the subscription, the GitHub `production` environment, and the
# repo secrets the workflow reads.
#
# Run it where you are logged into BOTH:
#   az login --tenant <tenant>          (Azure CLI, with rights to create app + assign roles)
#   gh auth login                       (GitHub CLI, admin on the repo)
#
#   bash infra/scripts/azure-bootstrap.sh
#
# Idempotent: re-running reuses the existing app and updates secrets.
set -euo pipefail

# --- configuration (override via env) --------------------------------------
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-3c8215d1-350c-4b83-bb7f-b5d26b4280f6}"
TENANT_ID="${TENANT_ID:-2da40318-46be-402c-ba75-cfb1f656567d}"
GH_REPO="${GH_REPO:-KevenWMarkham/zerodaywarranty}"
APP_NAME="${APP_NAME:-zdw-deployer}"
ENVIRONMENT="${ENVIRONMENT:-production}"
ROLE="${ROLE:-Owner}"   # Owner: needed because the deployment creates role assignments
# Postgres admin password seeded into the repo secret (override before running):
PG_ADMIN_PASSWORD="${PG_ADMIN_PASSWORD:-}"

echo "==> Subscription : $SUBSCRIPTION_ID"
echo "==> Tenant       : $TENANT_ID"
echo "==> Repo         : $GH_REPO"
echo "==> App          : $APP_NAME   (role: $ROLE)"

command -v az >/dev/null || { echo "az CLI not found"; exit 1; }
command -v gh >/dev/null || { echo "gh CLI not found"; exit 1; }

az account set --subscription "$SUBSCRIPTION_ID"

# --- 1. App registration + service principal -------------------------------
APP_ID="$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv)"
if [[ -z "$APP_ID" ]]; then
  echo "==> Creating app registration $APP_NAME"
  APP_ID="$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)"
else
  echo "==> Reusing app $APP_NAME ($APP_ID)"
fi
az ad sp show --id "$APP_ID" >/dev/null 2>&1 || az ad sp create --id "$APP_ID" >/dev/null
SP_OBJECT_ID="$(az ad sp show --id "$APP_ID" --query id -o tsv)"

# --- 2. Federated credentials (OIDC, no secrets) ---------------------------
add_fic () {
  local name="$1" subject="$2"
  if ! az ad app federated-credential list --id "$APP_ID" --query "[].name" -o tsv | grep -qx "$name"; then
    echo "==> Federated credential: $name  ($subject)"
    az ad app federated-credential create --id "$APP_ID" --parameters "$(cat <<JSON
{ "name": "$name",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "$subject",
  "audiences": ["api://AzureADTokenExchange"] }
JSON
)" >/dev/null
  else
    echo "==> Federated credential exists: $name"
  fi
}
add_fic "gh-main"        "repo:${GH_REPO}:ref:refs/heads/main"
add_fic "gh-env-${ENVIRONMENT}" "repo:${GH_REPO}:environment:${ENVIRONMENT}"

# --- 3. Role assignment on the subscription --------------------------------
echo "==> Assigning $ROLE on the subscription to the service principal"
az role assignment create --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "$ROLE" --scope "/subscriptions/$SUBSCRIPTION_ID" >/dev/null 2>&1 || \
  echo "    (role assignment already exists or insufficient rights — verify in portal)"

# --- 4. GitHub environment + secrets ---------------------------------------
echo "==> Ensuring GitHub environment '$ENVIRONMENT'"
gh api -X PUT "repos/${GH_REPO}/environments/${ENVIRONMENT}" >/dev/null

echo "==> Setting repo secrets"
gh secret set AZURE_CLIENT_ID       --repo "$GH_REPO" --body "$APP_ID"
gh secret set AZURE_TENANT_ID       --repo "$GH_REPO" --body "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --repo "$GH_REPO" --body "$SUBSCRIPTION_ID"
if [[ -n "$PG_ADMIN_PASSWORD" ]]; then
  gh secret set PG_ADMIN_PASSWORD   --repo "$GH_REPO" --body "$PG_ADMIN_PASSWORD"
else
  echo "    PG_ADMIN_PASSWORD not provided — set it before deploying:"
  echo "      gh secret set PG_ADMIN_PASSWORD --repo $GH_REPO --body '<strong-secret>'"
fi

cat <<DONE

==> Done. OIDC is wired (client id ${APP_ID}).
    Deploy with what-if first, then a real apply:
      gh workflow run "Deploy (Agentic-Automotives)" --repo $GH_REPO -f confirm=what-if-only
      gh workflow run "Deploy (Agentic-Automotives)" --repo $GH_REPO -f confirm=DEPLOY -f image_tag=0.1.0
    Then approve the 'production' environment when prompted, and watch:
      gh run watch --repo $GH_REPO
DONE
