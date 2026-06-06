// Private-networking foundation for the landing-zone-compliant deployment:
// a VNet with subnets for the Container Apps environment, private endpoints, and
// the Postgres delegated subnet, plus the private DNS zones each service needs.

param location string

var vnetName = 'vnet-zdw-agentic'

var zoneNames = [
  'privatelink.vaultcore.azure.net' // Key Vault
  'privatelink.azurecr.io' // Container Registry
  'privatelink.openai.azure.com' // Azure OpenAI
  'privatelink.cognitiveservices.azure.com' // Cognitive Services (OpenAI also registers here)
  'privatelink.postgres.database.azure.com' // Postgres flexible (VNet injection)
]

resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.20.0.0/16'
      ]
    }
    subnets: [
      {
        // Container Apps environment (workload-profile env → delegated, /23)
        name: 'snet-apps'
        properties: {
          addressPrefix: '10.20.0.0/23'
          delegations: [
            {
              name: 'aca'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        // Private endpoints (KV / ACR / AOAI)
        name: 'snet-pe'
        properties: {
          addressPrefix: '10.20.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        // Postgres flexible server VNet injection
        name: 'snet-pg'
        properties: {
          addressPrefix: '10.20.3.0/24'
          delegations: [
            {
              name: 'pg'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
    ]
  }
}

resource zones 'Microsoft.Network/privateDnsZones@2020-06-01' = [
  for z in zoneNames: {
    name: z
    location: 'global'
  }
]

resource links 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = [
  for (z, i) in zoneNames: {
    name: '${z}/link-zdw'
    location: 'global'
    properties: {
      registrationEnabled: false
      virtualNetwork: {
        id: vnet.id
      }
    }
    dependsOn: [
      zones[i]
    ]
  }
]

output appsSubnetId string = '${vnet.id}/subnets/snet-apps'
output peSubnetId string = '${vnet.id}/subnets/snet-pe'
output pgSubnetId string = '${vnet.id}/subnets/snet-pg'
output kvDnsId string = zones[0].id
output acrDnsId string = zones[1].id
output openaiDnsId string = zones[2].id
output cogDnsId string = zones[3].id
output pgDnsId string = zones[4].id
