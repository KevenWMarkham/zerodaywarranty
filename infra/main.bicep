// Zero Day Warranty — Azure deployment (reference IaC · design-as-code)
//
// Subscription-scoped: creates the project resource group `Agentic-Automotives`
// and deploys EVERY project resource into it. Fully self-contained — no shared
// dependencies on any other resource group.
//
// This template is present for review. It has not been applied.
//
//   az deployment sub create -l eastus2 \
//     -f infra/main.bicep -p infra/main.parameters.json \
//     -p pgAdminPassword='<strong-secret>'

targetScope = 'subscription'

@description('Region for the project RG and all resources.')
param location string = 'eastus2'

@description('Project resource group to CREATE. Everything is deployed inside it.')
param resourceGroupName string = 'Agentic-Automotives'

@description('Project Key Vault (created per APEX-M guide §3).')
param keyVaultName string = 'kv-zero-day-warranty'

@description('Project user-assigned managed identity (the per-agent identity).')
param managedIdentityName string = 'id-zdw-warranty-agent'

@description('Container Apps environment name (created).')
param containerAppsEnvName string = 'cae-zdw-agentic'

@description('Azure OpenAI account name (created).')
param aoaiName string = 'aoai-zdw-agentic'

@description('AOAI chat deployment the agent uses.')
param aoaiChatDeployment string = 'gpt-4.1-mini'

@description('Model version for the chat deployment. Set to a version available in your region.')
param aoaiChatModelVersion string = '2025-04-14'

@description('AOAI embedding deployment for the RAG step.')
param aoaiEmbedDeployment string = 'text-embedding-3-small'

@description('Model version for the embedding deployment.')
param aoaiEmbedModelVersion string = '1'

@description('Log Analytics workspace name (created).')
param logAnalyticsName string = 'log-zdw-agentic'

@description('Application Insights name (created).')
param appInsightsName string = 'appi-zdw-agentic'

@description('Postgres flexible server admin login.')
param pgAdminUser string = 'zdwadmin'

@description('Postgres flexible server admin password. Pass at deploy time.')
@secure()
param pgAdminPassword string

@description('Image tag for the zdw containers in ACR.')
param imageTag string = '0.1.0'

@description('HMAC key sealing each audit row. Defaults to a generated value for RnD.')
@secure()
param auditSigningKey string = base64(newGuid())

// Deterministic 6-char suffix for globally-unique names (ACR, AOAI, Postgres).
var suffix = take(uniqueString(subscription().subscriptionId, resourceGroupName), 6)

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
}

module project 'modules/project.bicep' = {
  name: 'zdw-project'
  scope: rg
  params: {
    location: location
    suffix: suffix
    keyVaultName: keyVaultName
    managedIdentityName: managedIdentityName
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
    containerAppsEnvName: containerAppsEnvName
    aoaiName: aoaiName
    aoaiChatDeployment: aoaiChatDeployment
    aoaiChatModelVersion: aoaiChatModelVersion
    aoaiEmbedDeployment: aoaiEmbedDeployment
    aoaiEmbedModelVersion: aoaiEmbedModelVersion
    pgAdminUser: pgAdminUser
    pgAdminPassword: pgAdminPassword
    imageTag: imageTag
    auditSigningKey: auditSigningKey
  }
}

output resourceGroup string = rg.name
output acrLoginServer string = project.outputs.acrLoginServer
output aoaiEndpoint string = project.outputs.aoaiEndpoint
output keyVaultUri string = project.outputs.keyVaultUri
output identityClientId string = project.outputs.identityClientId
output orchestratorFqdn string = project.outputs.orchestratorFqdn
