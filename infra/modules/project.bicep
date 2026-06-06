// Project-scoped resources for Zero Day Warranty, deployed into Agentic-Automotives.
// Creates: managed identity, Key Vault (+ secrets), and three Container Apps bound
// to the shared cae-visionkit environment, pulling images from the shared ACR and
// calling the shared Azure OpenAI account — all via the project managed identity.

param location string
param keyVaultName string
param managedIdentityName string
param sharedResourceGroupName string
param containerAppsEnvName string
param acrLoginServer string
param aoaiEndpoint string
param aoaiChatDeployment string
param aoaiEmbedDeployment string
param imageTag string

@secure()
param databaseUrl string
@secure()
param auditSigningKey string

// Built-in role: Key Vault Secrets User
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource mi 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

// Grant the managed identity read access to the project Key Vault.
resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, mi.id, kvSecretsUserRoleId)
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: mi.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource secDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'database-url'
  properties: {
    value: databaseUrl
  }
}

resource secSigningKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'audit-ledger-signing-key'
  properties: {
    value: auditSigningKey
  }
}

resource secAoaiEndpoint 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'aoai-endpoint'
  properties: {
    value: aoaiEndpoint
  }
}

// Reuse the shared Container Apps environment (cross-RG existing reference).
resource cae 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: containerAppsEnvName
  scope: resourceGroup(sharedResourceGroupName)
}

var apps = [
  {
    name: 'ca-zdw-orchestrator'
    image: '${acrLoginServer}/zdw/orchestrator:${imageTag}'
    external: true
  }
  {
    name: 'ca-zdw-mcp-warranty'
    image: '${acrLoginServer}/zdw/mcp-warranty:${imageTag}'
    external: false
  }
  {
    name: 'ca-zdw-mcp-ledger'
    image: '${acrLoginServer}/zdw/mcp-ledger:${imageTag}'
    external: false
  }
]

resource containerApps 'Microsoft.App/containerApps@2024-03-01' = [for app in apps: {
  name: app.name
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${mi.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: app.external
        targetPort: 8080
        transport: 'auto'
      }
      registries: [
        {
          server: acrLoginServer
          identity: mi.id
        }
      ]
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/database-url'
          identity: mi.id
        }
        {
          name: 'audit-signing-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/audit-ledger-signing-key'
          identity: mi.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: app.name
          image: app.image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AZURE_CLIENT_ID'
              value: mi.properties.clientId
            }
            {
              name: 'AOAI_ENDPOINT'
              value: aoaiEndpoint
            }
            {
              name: 'AOAI_CHAT_DEPLOYMENT'
              value: aoaiChatDeployment
            }
            {
              name: 'AOAI_EMBED_DEPLOYMENT'
              value: aoaiEmbedDeployment
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'AUDIT_LEDGER_SIGNING_KEY'
              secretRef: 'audit-signing-key'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 2
      }
    }
  }
  // KV access + secret values must exist before the app's KV references resolve.
  dependsOn: [
    kvSecretsUser
    secDatabaseUrl
    secSigningKey
  ]
}]

output identityPrincipalId string = mi.properties.principalId
output identityClientId string = mi.properties.clientId
output keyVaultUri string = kv.properties.vaultUri
output orchestratorFqdn string = containerApps[0].properties.configuration.ingress.fqdn
