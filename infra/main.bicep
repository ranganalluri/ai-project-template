// main.bicep - Azure Container Apps Infrastructure for AI Project
targetScope = 'resourceGroup'

// Resource naming parameters
param location string = resourceGroup().location
param companyName string = 'contoso'
param regionCode string = 'eu1'
param environment string = 'dev'
param index string = '01'

// Container Registry parameters
param containerRegistrySku string = 'Premium'
param containerRegistryAdminEnabled bool = true

// AI Services parameters
param aiServicesSku string = 'S0'
param keyVaultEnabled bool = true
param aiProjectName string = ''
param deploymentCapacity int = 6

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

// Azure AI Foundry (AI Services) Account
module aiServices 'modules/ai-services.bicep' = {
  name: 'aiFoundryDeployment'
  params: {
    name: '${resourceNamePrefix}-ai-${resourceIndexSuffix}'
    location: location
    environment: environment
    sku: aiServicesSku
    managedIdentityResourceId: managedIdentity.id
    managedIdentityPrincipalId: managedIdentity.properties.principalId
    projectName: (!empty(aiProjectName)) ? aiProjectName : '${resourceNamePrefix}-project-${resourceIndexSuffix}'
    deploymentCapacity: deploymentCapacity
    tags: {
      region: regionCode
      createdBy: 'bicep'
    }
  }
}

// Azure Cosmos DB
module cosmosDb 'modules/cosmos-db.bicep' = {
  name: 'cosmosDbDeployment'
  params: {
    name: '${resourceNamePrefix}-cosmos-${resourceIndexSuffix}'
    location: location
    environment: environment
    tags: {
      region: regionCode
      createdBy: 'bicep'
    }
  }
}

// Azure Key Vault
module keyVault 'modules/key-vault.bicep' = if (keyVaultEnabled) {
  name: 'keyVaultDeployment'
  params: {
    name: '${resourceNamePrefix}-kv-${resourceIndexSuffix}'
    location: location
    managedIdentityPrincipalId: managedIdentity.properties.principalId
    environment: environment
    cosmosDbKey: cosmosDb.outputs.key
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

// AI Foundry outputs
output AI_FOUNDRY_ACCOUNT_NAME string = aiServices.outputs.accountName
output AI_FOUNDRY_ENDPOINT string = aiServices.outputs.endpoint
output AI_FOUNDRY_PROJECT_NAME string = aiServices.outputs.projectNameOut
output AI_FOUNDRY_PROJECT_ID string = aiServices.outputs.projectId
output AI_FOUNDRY_GPT4_DEPLOYMENT string = aiServices.outputs.gpt4DeploymentName
output AI_SERVICES_ACCOUNT_NAME string = aiServices.outputs.accountName
output AI_SERVICES_ENDPOINT string = aiServices.outputs.endpoint

// Cosmos DB outputs
output AZURE_COSMOSDB_ACCOUNT_NAME string = cosmosDb.outputs.accountName
output AZURE_COSMOSDB_ENDPOINT string = cosmosDb.outputs.endpoint
output AZURE_COSMOSDB_KEY string = cosmosDb.outputs.key
output AZURE_COSMOSDB_DATABASE_NAME string = cosmosDb.outputs.databaseName

// Key Vault outputs
output KEY_VAULT_NAME string = (keyVaultEnabled) ? keyVault.outputs.name : ''
output KEY_VAULT_URI string = (keyVaultEnabled) ? keyVault.outputs.uri : ''
output FOUNDRY_CONNECTION_STRING_SECRET_NAME string = (keyVaultEnabled) ? keyVault.outputs.secretName : ''
output FOUNDRY_CONNECTION_STRING string = (keyVaultEnabled) ? 'Update Key Vault secret "${keyVault.outputs.secretName}" after creating AI Project' : ''
output COSMOS_DB_KEY_SECRET_NAME string = (keyVaultEnabled) ? keyVault.outputs.cosmosDbKeySecretName : ''
