// api.bicep - API Service Container App Deployment
// This is used by azd deploy to update the API service with new container images
targetScope = 'resourceGroup'

@description('Unique environment name used for resource naming.')
param environmentName string

@description('Primary location for all resources.')
param location string

param containerRegistryName string
param containerAppsEnvironmentName string
param imageName string
param identityId string
param resourceNamePrefix string
param resourceIndexSuffix string
param keyVaultName string = ''
param foundryEndpoint string = ''
param foundryProjectName string = ''
param cosmosDbEndpoint string = ''

var foundryProjectEndpoint = '${foundryEndpoint}api/projects/${foundryProjectName}'

// Extract managed identity name from resource ID and reference it to get client ID
var managedIdentityName = last(split(identityId, '/'))
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: managedIdentityName
}

// Build environment variables array conditionally
var baseEnvVars = (!empty(foundryEndpoint) && !empty(foundryProjectName)) ? [
  {
    name: 'FOUNDRY_ENDPOINT'
    value: foundryProjectEndpoint
  }
] : []

// Add Foundry connection string from Key Vault if available
// Connection string bypasses RBAC data action limitations for agents operations
var foundryConnectionStringEnvVars = (!empty(keyVaultName)) ? [
  {
    name: 'FOUNDRY_PROJECT_CONNECTION_STRING'
    secretRef: 'foundry-connection-string'
  }
] : []

var cosmosEnvVars = (!empty(cosmosDbEndpoint)) ? [
  {
    name: 'AZURE_COSMOSDB_ENDPOINT'
    value: cosmosDbEndpoint
  }
] : []

var keyVaultEnvVars = (!empty(keyVaultName)) ? [
  {
    name: 'AZURE_COSMOSDB_KEY'
    secretRef: 'cosmos-db-key'
  }
] : []

// Set AZURE_CLIENT_ID so DefaultAzureCredential knows which managed identity to use
// This is required for user-assigned managed identities in Container Apps
var managedIdentityEnvVars = (!empty(identityId)) ? [
  {
    name: 'AZURE_CLIENT_ID'
    value: managedIdentity.properties.clientId
  }
] : []

var allEnvVars = concat(baseEnvVars, cosmosEnvVars, keyVaultEnvVars, managedIdentityEnvVars, foundryConnectionStringEnvVars)

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2022-03-01' existing = {
  name: containerAppsEnvironmentName
}


resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = if (!empty(keyVaultName)) {
  name: keyVaultName
}

resource api 'Microsoft.App/containerApps@2025-02-02-preview' = {
  name: '${resourceNamePrefix}-api-${resourceIndexSuffix}'
  location: location
  tags: {
    'azd-env-name': environmentName
    'azd-service-name': 'api'
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: identityId
        }
      ]
      secrets: (!empty(keyVaultName)) ? [
        {
          name: 'foundry-connection-string'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/FoundryProjectConnectionString'
          identity: identityId
        }
        {
          name: 'cosmos-db-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/CosmosDbKey'
          identity: identityId
        }
      ] : []
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [
        {
          image: imageName
          name: 'main'
          env: allEnvVars
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
    }
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
}

// Outputs
output API_FQDN string = api.properties.configuration.ingress.fqdn
output API_URL string = 'https://${api.properties.configuration.ingress.fqdn}'
output API_ID string = api.id
output API_NAME string = api.name
