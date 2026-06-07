// Landing-zone-compliant project resources: every data service has public
// network access disabled and is reached over a private endpoint (KV/ACR/AOAI)
// or VNet injection (Postgres). The Container Apps environment is VNet-integrated
// so the apps can reach those private endpoints; ingress stays external so the
// orchestrator is reachable for the smoke test.

param location string
param suffix string
param keyVaultName string
param managedIdentityName string
param logAnalyticsName string
param appInsightsName string
param containerAppsEnvName string
param aoaiName string
param aoaiChatDeployment string
param aoaiEmbedDeployment string
param pgAdminUser string
@secure()
param pgAdminPassword string
param imageTag string
@secure()
param auditSigningKey string

@description('Deploy the Container Apps. Set false for phase 1 (before images exist), true after import.')
param deployApps bool = true

// Network inputs (from modules/network.bicep)
param appsSubnetId string
param peSubnetId string
param pgSubnetId string
param kvDnsId string
param acrDnsId string
param openaiDnsId string
param cogDnsId string
param pgDnsId string

var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull
var aoaiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User

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
// Container Registry (Premium — required for private endpoints; public off)
// ---------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: 'Premium'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Disabled'
  }
}

resource peAcr 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-acr-zdw'
  location: location
  properties: {
    subnet: {
      id: peSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'acr'
        properties: {
          privateLinkServiceId: acr.id
          groupIds: [
            'registry'
          ]
        }
      }
    ]
  }
}

resource peAcrDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: peAcr
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'acr'
        properties: {
          privateDnsZoneId: acrDnsId
        }
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Azure OpenAI (public off, network deny) + private endpoint + deployments
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
    publicNetworkAccess: 'Disabled'
    disableLocalAuth: true
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}

resource peAoai 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-aoai-zdw'
  location: location
  properties: {
    subnet: {
      id: peSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'aoai'
        properties: {
          privateLinkServiceId: aoai.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

resource peAoaiDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: peAoai
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'openai'
        properties: {
          privateDnsZoneId: openaiDnsId
        }
      }
      {
        name: 'cognitiveservices'
        properties: {
          privateDnsZoneId: cogDnsId
        }
      }
    ]
  }
}

// (AOAI model deployments are created by modules/aoai-deployments.bicep AFTER
// the account is fully provisioned — see main-private.bicep — to avoid the
// "AccountProvisioningStateInvalid … state Accepted" race.)

// ---------------------------------------------------------------------------
// Postgres flexible server — VNet injection (no public access)
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
    network: {
      delegatedSubnetResourceId: pgSubnetId
      privateDnsZoneArmResourceId: pgDnsId
    }
  }
}

resource pgDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: pg
  name: 'zdw'
}

// ---------------------------------------------------------------------------
// Key Vault (public off) + private endpoint + secrets
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
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

resource peKv 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-kv-zdw'
  location: location
  properties: {
    subnet: {
      id: peSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'kv'
        properties: {
          privateLinkServiceId: kv.id
          groupIds: [
            'vault'
          ]
        }
      }
    ]
  }
}

resource peKvDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: peKv
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'vault'
        properties: {
          privateDnsZoneId: kvDnsId
        }
      }
    ]
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
// Role assignments (data-plane) for the managed identity
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
// Container Apps environment (VNet-integrated) + apps
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
    vnetConfiguration: {
      infrastructureSubnetId: appsSubnetId
      internal: false
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

var apps = deployApps ? [
  {
    name: 'ca-zdw-orchestrator'
    repo: 'orchestrator'
    external: true
  }
  {
    name: 'ca-zdw-mcp-warranty'
    repo: 'mcp-warranty'
    external: false
  }
  {
    name: 'ca-zdw-mcp-ledger'
    repo: 'mcp-ledger'
    external: false
  }
] : []

resource containerApps 'Microsoft.App/containerApps@2024-03-01' = [
  for app in apps: {
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
      workloadProfileName: 'Consumption'
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
            image: '${acr.properties.loginServer}/zdw/${app.repo}:${imageTag}'
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
            ]
          }
        ]
        scale: {
          minReplicas: 0
          maxReplicas: 2
        }
      }
    }
    dependsOn: [
      raKvSecrets
      raAcrPull
      secDatabaseUrl
      secSigningKey
      peKvDns
      peAcrDns
    ]
  }
]

// ---------------------------------------------------------------------------
// One-shot migration job (runs INSIDE the VNet) to apply the medallion + audit
// schema to the private Postgres. Manual trigger:
//   az containerapp job start -g <RG> -n ca-zdw-migrate
// Idempotent (the DDL uses IF NOT EXISTS / CREATE OR REPLACE).
// ---------------------------------------------------------------------------
resource migrateJob 'Microsoft.App/jobs@2024-03-01' = {
  name: 'ca-zdw-migrate'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${mi.id}': {}
    }
  }
  properties: {
    environmentId: cae.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 1
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/database-url'
          identity: mi.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'migrate'
          image: 'postgres:16-alpine'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'SCHEMA_URL'
              value: 'https://raw.githubusercontent.com/KevenWMarkham/zerodaywarranty/main/infra/scripts/postgres-schemas.sql'
            }
          ]
          command: [
            '/bin/sh'
            '-c'
          ]
          args: [
            'set -e; wget -qO /tmp/s.sql "$SCHEMA_URL"; psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f /tmp/s.sql; echo SCHEMA_APPLIED'
          ]
        }
      ]
    }
  }
  dependsOn: [
    raKvSecrets
    secDatabaseUrl
  ]
}

output acrLoginServer string = acr.properties.loginServer
output aoaiEndpoint string = aoai.properties.endpoint
output identityPrincipalId string = mi.properties.principalId
output identityClientId string = mi.properties.clientId
output keyVaultUri string = kv.properties.vaultUri
