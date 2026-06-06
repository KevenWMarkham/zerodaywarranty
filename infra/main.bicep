// Zero Day Warranty — Azure deployment (reference IaC · design-as-code)
//
// Subscription-scoped: creates the project resource group `Agentic-Automotives`
// and deploys the project resources into it, then grants the project managed
// identity the roles it needs on the SHARED platform resources in
// `rg-iot-visionkit` (ACR + Azure OpenAI).
//
// This template is present for review. It has not been applied.
//
//   az deployment sub create -l eastus2 \
//     -f infra/main.bicep -p infra/main.parameters.json \
//     -p databaseUrl='<from kv-home-agent/database-url>'

targetScope = 'subscription'

@description('Region for the project RG and resources. Co-located with the shared platform.')
param location string = 'eastus2'

@description('Project resource group to CREATE.')
param resourceGroupName string = 'Agentic-Automotives'

@description('Shared platform resource group to REUSE (ACR, Container Apps env, AOAI, Postgres).')
param sharedResourceGroupName string = 'rg-iot-visionkit'

@description('Project Key Vault (created per APEX-M guide §3).')
param keyVaultName string = 'kv-zero-day-warranty'

@description('Project user-assigned managed identity (the per-agent identity).')
param managedIdentityName string = 'id-zdw-warranty-agent'

@description('Shared Azure Container Registry name.')
param acrName string = 'acrvisionkit4459'

@description('Shared ACR login server.')
param acrLoginServer string = 'acrvisionkit4459.azurecr.io'

@description('Shared Container Apps environment to bind to.')
param containerAppsEnvName string = 'cae-visionkit'

@description('Shared Azure OpenAI account name.')
param aoaiName string = 'aoai-apex-demo'

@description('Shared Azure OpenAI endpoint.')
param aoaiEndpoint string = 'https://aoai-apex-demo.openai.azure.com/'

@description('AOAI chat deployment the agent uses (recommended: gpt-4.1-mini).')
param aoaiChatDeployment string = 'gpt-4.1-mini'

@description('AOAI embedding deployment for the RAG step.')
param aoaiEmbedDeployment string = 'text-embedding-3-small'

@description('Image tag for the zdw containers in ACR.')
param imageTag string = '0.1.0'

@description('Postgres connection string (source: kv-home-agent/database-url). Passed at deploy.')
@secure()
param databaseUrl string

@description('HMAC key sealing each audit row. Defaults to a generated value for RnD.')
@secure()
param auditSigningKey string = base64(newGuid())

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
}

module project 'modules/project.bicep' = {
  name: 'zdw-project'
  scope: rg
  params: {
    location: location
    keyVaultName: keyVaultName
    managedIdentityName: managedIdentityName
    sharedResourceGroupName: sharedResourceGroupName
    containerAppsEnvName: containerAppsEnvName
    acrLoginServer: acrLoginServer
    aoaiEndpoint: aoaiEndpoint
    aoaiChatDeployment: aoaiChatDeployment
    aoaiEmbedDeployment: aoaiEmbedDeployment
    imageTag: imageTag
    databaseUrl: databaseUrl
    auditSigningKey: auditSigningKey
  }
}

module rbacShared 'modules/rbac.bicep' = {
  name: 'zdw-rbac-shared'
  scope: resourceGroup(sharedResourceGroupName)
  params: {
    acrName: acrName
    aoaiName: aoaiName
    principalId: project.outputs.identityPrincipalId
  }
}

output identityPrincipalId string = project.outputs.identityPrincipalId
output identityClientId string = project.outputs.identityClientId
output keyVaultUri string = project.outputs.keyVaultUri
output orchestratorFqdn string = project.outputs.orchestratorFqdn
