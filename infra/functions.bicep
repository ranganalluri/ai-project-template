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
param keyVaultUri string = ''
param storageAccountName string = ''


resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2022-03-01' existing = {
  name: containerAppsEnvironmentName
}

// Extract Key Vault name from URI (format: https://{name}.vault.azure.net/)
var keyVaultName = (!empty(keyVaultUri)) ? split(split(keyVaultUri, '://')[1], '.')[0] : ''

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = if (!empty(keyVaultUri)) {
  name: keyVaultName
}

resource api 'Microsoft.App/containerApps@2025-02-02-preview' = {
  name: '${resourceNamePrefix}-functions-${resourceIndexSuffix}'
  location: location
  tags: {
    'azd-env-name': environmentName
    'azd-service-name': 'functions'
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: identityId
        }
      ]
      secrets: (!empty(keyVaultUri)) ? [
        {
          name: 'cosmos-db-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/CosmosDbKey'
          identity: identityId
        }
        {
          name: 'storage-account-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/StorageAccountKey'
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
          env: concat(
            (!empty(keyVaultUri)) ? [
              {
                name: 'AZURE_COSMOSDB_KEY'
                secretRef: 'cosmos-db-key'
              }
              {
                name: 'AZURE_STORAGE_ACCOUNT_KEY'
                secretRef: 'storage-account-key'
              }
            ] : [],
            (!empty(storageAccountName)) ? [
              {
                name: 'AZURE_STORAGE_ACCOUNT_NAME'
                value: storageAccountName
              }
            ] : []
          )
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
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
output FUNCTIONS_FQDN string = api.properties.configuration.ingress.fqdn
output FUNCTIONS_URL string = 'https://${api.properties.configuration.ingress.fqdn}'
output FUNCTIONS_ID string = api.id
output FUNCTIONS_NAME string = api.name
