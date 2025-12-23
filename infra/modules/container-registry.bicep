// container-registry.bicep - Azure Container Registry Module
targetScope = 'resourceGroup'

param name string
param location string
param environment string = 'dev'
param sku string = 'Basic'
param adminUserEnabled bool = false
param tags object = {}
@description('Principal ID of the managed identity to grant AcrPull role')
param acrPullPrincipalId string = ''

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-11-01' = {
  name: name
  location: location
  tags: union(tags, {
    environment: environment
    createdBy: 'bicep'
  })
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: adminUserEnabled
    networkRuleBypassOptions: 'AzureServices'
  }
}

// Assign AcrPull role if principal ID is provided
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(acrPullPrincipalId)) {
  name: guid(containerRegistry.id, acrPullPrincipalId, 'acrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: acrPullPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output loginServer string = containerRegistry.properties.loginServer
output id string = containerRegistry.id
output name string = containerRegistry.name
