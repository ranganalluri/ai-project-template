// main.bicep - Azure Container Apps Infrastructure for AI Project
targetScope = 'resourceGroup'

// Resource naming parameters
param location string = 'eastus2'
param companyName string = 'contoso'
param regionCode string = 'eu1'
param environment string = 'dev'
param index string = '01'

// Container Registry parameters
param containerRegistrySku string = 'Premium'
param containerRegistryAdminEnabled bool = true

// Naming convention: companyName-region-environment-appname-index
var resourceNamePrefix = '${companyName}-${regionCode}-${environment}'
var resourceIndexSuffix = index

// ACR naming (must be alphanumeric only, no hyphens)
var acrName = '${companyName}${regionCode}${environment}acr${index}'

// Container Apps Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${resourceNamePrefix}-cae-${resourceIndexSuffix}'
  location: location
  tags: {
    environment: environment
    region: regionCode
    createdBy: 'bicep'
  }
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

// Log Analytics Workspace for Container Apps
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2021-12-01-preview' = {
  name: '${resourceNamePrefix}-log-${resourceIndexSuffix}'
  location: location
  tags: {
    environment: environment
    region: regionCode
  }
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Managed Identity for Container Apps
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${resourceNamePrefix}-identity-${resourceIndexSuffix}'
  location: location
  tags: {
    environment: environment
    region: regionCode
  }
}

// Azure Container Registry
module acr 'modules/container-registry.bicep' = {
  name: 'acrDeployment'
  params: {
    name: acrName
    location: location
    environment: environment
    sku: containerRegistrySku
    adminUserEnabled: containerRegistryAdminEnabled
    acrPullPrincipalId: managedIdentity.properties.principalId
    tags: {
      region: regionCode
      createdBy: 'bicep'
    }
  }
}

// Outputs for AZD Integration
output containerAppEnvId string = containerAppEnv.id
output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerAppEnv.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.outputs.loginServer
output ACR_LOGIN_SERVER string = acr.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_ID string = acr.outputs.id
output AZURE_CONTAINER_REGISTRY_NAME string = acr.outputs.name
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output MANAGED_IDENTITY_ID string = managedIdentity.id
output MANAGED_IDENTITY_CLIENT_ID string = managedIdentity.properties.clientId
output AZURE_LOCATION string = location
output RESOURCE_NAME_PREFIX string = resourceNamePrefix
output RESOURCE_INDEX_SUFFIX string = resourceIndexSuffix
