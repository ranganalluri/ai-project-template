// ai-services.bicep - Azure AI Foundry (AI Services) Account Module
targetScope = 'resourceGroup'

param name string
param location string
param environment string = 'dev'
param sku string = 'S0'
param managedIdentityResourceId string = ''
param projectName string = ''
param tags object = {}

// Azure AI Foundry uses kind 'AIServices'
resource aiFoundryAccount 'Microsoft.CognitiveServices/accounts@2025-09-01' = {
  name: name
  location: location
  tags: union(tags, {
    environment: environment
    createdBy: 'bicep'
  })
  kind: 'AIServices'
  sku: {
    name: sku
  }
  properties: {
    apiProperties: {}
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: true
    customSubDomainName: name
  }
  identity: (!empty(managedIdentityResourceId)) ? {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityResourceId}': {}
    }
  } : {
    type: 'SystemAssigned'
  }
}

// AI Project under Foundry account
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-09-01' = if (!empty(projectName)) {
  parent: aiFoundryAccount
  name: projectName
  location: location
  tags: union(tags, {
    environment: environment
    createdBy: 'bicep'
  })
  properties: {}
  identity: {
    type: 'SystemAssigned'
  }
}

// GPT-4-1 Deployment (at account level, for use with project)
resource gpt4Deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-09-01' = if (!empty(projectName)) {
  parent: aiFoundryAccount
  name: 'gpt-4.1'
  sku: {
    name: 'Standard'
    capacity: 1
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2025-04-14'
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

// Outputs
output id string = aiFoundryAccount.id
output accountName string = aiFoundryAccount.name
output name string = aiFoundryAccount.name
output endpoint string = aiFoundryAccount.properties.endpoint
@secure()
output primaryKey string = aiFoundryAccount.listKeys().key1
output projectNameOut string = (!empty(projectName)) ? aiProject.name : ''
output projectId string = (!empty(projectName)) ? aiProject.id : ''
output gpt4DeploymentName string = (!empty(projectName)) ? gpt4Deployment.name : ''
