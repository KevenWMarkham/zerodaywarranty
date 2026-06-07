// Azure OpenAI model deployments, in a SEPARATE module so they run only after
// the account is fully provisioned. Deploying the model deployments as children
// in the same pass as the account creation races the account's async PUT and
// fails intermittently with "AccountProvisioningStateInvalid … state Accepted".
// main-private.bicep wires this module to depend on the project module.

param aoaiName string
param aoaiChatDeployment string
param aoaiChatModelVersion string
param aoaiEmbedDeployment string
param aoaiEmbedModelVersion string

resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aoaiName
}

resource chat 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
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

resource embed 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
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
    chat
  ]
}
