// ai-services.bicep - Azure AI Foundry (AI Services) Account Module
targetScope = 'resourceGroup'

param name string
param location string
param environment string = 'dev'
param sku string = 'S0'
param managedIdentityResourceId string = ''
param managedIdentityPrincipalId string = ''
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
  identity: (!empty(managedIdentityResourceId)) ? {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityResourceId}': {}
    }
  } : {
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


// Role assignment: Grant managed identity permission to use AI Foundry account
// This allows the container app to invoke models in the AI project
resource cognitiveServicesUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(managedIdentityPrincipalId)) {
  name: guid(aiFoundryAccount.id, managedIdentityPrincipalId, 'CognitiveServicesUser')
  scope: aiFoundryAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '86240b0e-9422-4c43-887b-b61143f32ba8')
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment: Grant managed identity permission to create and manage AI Foundry agents at account level
// This provides write access for agents operations
resource cognitiveServicesContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(managedIdentityPrincipalId)) {
  name: guid(aiFoundryAccount.id, managedIdentityPrincipalId, 'CognitiveServicesContributor')
  scope: aiFoundryAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68')
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment: Grant Cognitive Services User role at project level
// This allows the container app to invoke models in the AI project
resource projectCognitiveServicesUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(managedIdentityPrincipalId) && !empty(projectName)) {
  name: guid(aiProject.id, managedIdentityPrincipalId, 'CognitiveServicesUser')
  scope: aiProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '86240b0e-9422-4c43-887b-b61143f32ba8')
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment: Grant managed identity permission at project level for agents write operations
// Data actions like Microsoft.CognitiveServices/accounts/AIServices/agents/write may require project-level permissions
resource projectContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(managedIdentityPrincipalId) && !empty(projectName)) {
  name: guid(aiProject.id, managedIdentityPrincipalId, 'CognitiveServicesContributor')
  scope: aiProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68')
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment: Grant "Azure AI User" role which includes data actions for AI Foundry
// This role provides access to AI services including agents operations
// Role ID: 53ca6127-db72-4b80-b1b0-d745d6d5456d
resource azureAIUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(managedIdentityPrincipalId)) {
  name: guid(aiFoundryAccount.id, managedIdentityPrincipalId, 'AzureAIUser')
  scope: aiFoundryAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment: Grant "Azure AI User" role at project level for agents operations
resource projectAzureAIUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(managedIdentityPrincipalId) && !empty(projectName)) {
  name: guid(aiProject.id, managedIdentityPrincipalId, 'AzureAIUser')
  scope: aiProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
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
