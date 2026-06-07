// Zero Day Warranty — landing-zone-compliant (private networking) deployment.
//
// Same resources as infra/main.bicep, but every data service has public network
// access disabled and is reached over a private endpoint (KV/ACR/AOAI) or VNet
// injection (Postgres), with a VNet-integrated Container Apps environment.
// Use this in subscriptions that enforce the APEX-M "require private endpoint"
// deny policies.
//
//   az deployment sub create -n zdw-deploy -l eastus2 \
//     -f infra/main-private.bicep -p infra/main-private.parameters.json \
//     -p pgAdminPassword='<strong-secret>'

targetScope = 'subscription'

param location string = 'eastus2'
param resourceGroupName string = 'Agentic-Automotives'
param keyVaultName string = 'kv-zero-day-warranty'
param managedIdentityName string = 'id-zdw-warranty-agent'
param containerAppsEnvName string = 'cae-zdw-agentic'
param aoaiName string = 'aoai-zdw-agentic'
param aoaiChatDeployment string = 'gpt-4.1-mini'
param aoaiChatModelVersion string = '2025-04-14'
param aoaiEmbedDeployment string = 'text-embedding-3-small'
param aoaiEmbedModelVersion string = '1'
param logAnalyticsName string = 'log-zdw-agentic'
param appInsightsName string = 'appi-zdw-agentic'
param pgAdminUser string = 'zdwadmin'
@secure()
param pgAdminPassword string
param imageTag string = '0.1.0'
@secure()
param auditSigningKey string = base64(newGuid())

@description('Deploy the Container Apps. Phase 1: false (before images exist). Phase 2: true (after import).')
param deployApps bool = true

var suffix = take(uniqueString(subscription().subscriptionId, resourceGroupName), 6)

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
}

module network 'modules/network.bicep' = {
  name: 'zdw-network'
  scope: rg
  params: {
    location: location
  }
}

module project 'modules/project-private.bicep' = {
  name: 'zdw-project-private'
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
    aoaiEmbedDeployment: aoaiEmbedDeployment
    pgAdminUser: pgAdminUser
    pgAdminPassword: pgAdminPassword
    imageTag: imageTag
    auditSigningKey: auditSigningKey
    deployApps: deployApps
    appsSubnetId: network.outputs.appsSubnetId
    peSubnetId: network.outputs.peSubnetId
    pgSubnetId: network.outputs.pgSubnetId
    kvDnsId: network.outputs.kvDnsId
    acrDnsId: network.outputs.acrDnsId
    openaiDnsId: network.outputs.openaiDnsId
    cogDnsId: network.outputs.cogDnsId
    pgDnsId: network.outputs.pgDnsId
  }
}

// AOAI model deployments run AFTER the account is fully provisioned (separate
// module + dependsOn) to avoid the state-Accepted race.
module aoaiDeployments 'modules/aoai-deployments.bicep' = {
  name: 'zdw-aoai-deployments'
  scope: rg
  dependsOn: [
    project
  ]
  params: {
    aoaiName: aoaiName
    aoaiChatDeployment: aoaiChatDeployment
    aoaiChatModelVersion: aoaiChatModelVersion
    aoaiEmbedDeployment: aoaiEmbedDeployment
    aoaiEmbedModelVersion: aoaiEmbedModelVersion
  }
}

output resourceGroup string = rg.name
output acrLoginServer string = project.outputs.acrLoginServer
output aoaiEndpoint string = project.outputs.aoaiEndpoint
output keyVaultUri string = project.outputs.keyVaultUri
output identityClientId string = project.outputs.identityClientId
