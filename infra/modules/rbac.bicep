// Role assignments on the SHARED platform resources (rg-iot-visionkit) for the
// project managed identity. Deployed at the shared resource group scope.

@description('Shared ACR name.')
param acrName string

@description('Shared Azure OpenAI account name.')
param aoaiName string

@description('Principal ID of the project managed identity.')
param principalId string

// Built-in roles
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'           // AcrPull
var aoaiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'          // Cognitive Services OpenAI User

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: acrName
}

resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aoaiName
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, principalId, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

resource aoaiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoai.id, principalId, aoaiUserRoleId)
  scope: aoai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', aoaiUserRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
