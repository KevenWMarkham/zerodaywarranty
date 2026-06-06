// All project resources for Zero Day Warranty, created inside Agentic-Automotives.
// Self-contained: ACR, Azure OpenAI (+ deployments), Postgres (+ db), Container
// Apps environment, Key Vault (+ secrets), managed identity, observability, the
// three Container Apps, and all (local) role assignments.

param location string
param suffix string
param keyVaultName string
param managedIdentityName string
param logAnalyticsName string
param appInsightsName string
param containerAppsEnvName string
param aoaiName string
param aoaiChatDeployment string
param aoaiChatModelVersion string
param aoaiEmbedDeployment string
param aoaiEmbedModelVersion string
param pgAdminUser string
@secure()
param pgAdminPassword string
param imageTag string
@secure()
param auditSigningKey string

// Built-in role definition IDs
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'       // AcrPull
var aoaiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'      // Cognitive Services OpenAI User

var acrName = 'acrzdwagentic${suffix}'
var pgServerName = 'pg-zdw-agentic${suffix}'

// ---------------------------------------------------------------------------
// Identity + observability
// ---------------------------------------------------------------------------
resource mi 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
}

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

// ---------------------------------------------------------------------------
// Container Registry (keyless — managed identity pull)
// ---------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

// ---------------------------------------------------------------------------
// Azure OpenAI + deployments (keyless — Entra only)
// ---------------------------------------------------------------------------
resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aoaiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aoaiName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

resource aoaiChat 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  name: aoaiChatDeployment
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: aoaiChatDeployment
      version: aoaiChatModelVersion
    }
  }
}

resource aoaiEmbed 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  name: aoaiEmbedDeployment
  sku: {
    name: 'Standard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: aoaiEmbedDeployment
      version: aoaiEmbedModelVersion
    }
  }
  // AOAI deployments on one account must be created serially.
  dependsOn: [
    aoaiChat
  ]
}

// ---------------------------------------------------------------------------
// Postgres flexible server + project database
// ---------------------------------------------------------------------------
resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: pgServerName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: pgAdminUser
    administratorLoginPassword: pgAdminPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Enabled'
      tenantId: subscription().tenantId
    }
  }
}

resource pgDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: pg
  name: 'zdw'
}

resource pgAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: pg
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ---------------------------------------------------------------------------
// Key Vault + secrets
// ---------------------------------------------------------------------------
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

resource secDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'database-url'
  properties: {
    value: 'postgresql://${pgAdminUser}:${pgAdminPassword}@${pg.properties.fullyQualifiedDomainName}:5432/zdw?sslmode=require'
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
    value: aoai.properties.endpoint
  }
}

// ---------------------------------------------------------------------------
// Local role assignments for the managed identity
// ---------------------------------------------------------------------------
resource raKvSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, mi.id, kvSecretsUserRoleId)
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: mi.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource raAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, mi.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: mi.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource raAoaiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoai.id, mi.id, aoaiUserRoleId)
  scope: aoai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', aoaiUserRoleId)
    principalId: mi.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Container Apps environment + apps
// ---------------------------------------------------------------------------
resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
  }
}

var apps = [
  {
    name: 'ca-zdw-orchestrator'
    image: '${acr.properties.loginServer}/zdw/orchestrator:${imageTag}'
    external: true
  }
  {
    name: 'ca-zdw-mcp-warranty'
    image: '${acr.properties.loginServer}/zdw/mcp-warranty:${imageTag}'
    external: false
  }
  {
    name: 'ca-zdw-mcp-ledger'
    image: '${acr.properties.loginServer}/zdw/mcp-ledger:${imageTag}'
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
          server: acr.properties.loginServer
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
              value: aoai.properties.endpoint
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
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appi.properties.ConnectionString
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
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8080
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8080
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
            }
            {
              type: 'Startup'
              httpGet: {
                path: '/health'
                port: 8080
              }
              initialDelaySeconds: 3
              periodSeconds: 5
              failureThreshold: 12
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
    raKvSecrets
    raAcrPull
    secDatabaseUrl
    secSigningKey
  ]
}]

output acrLoginServer string = acr.properties.loginServer
output aoaiEndpoint string = aoai.properties.endpoint
output identityPrincipalId string = mi.properties.principalId
output identityClientId string = mi.properties.clientId
output keyVaultUri string = kv.properties.vaultUri
output orchestratorFqdn string = containerApps[0].properties.configuration.ingress.fqdn
