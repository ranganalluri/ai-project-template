// key-vault.bicep - Azure Key Vault Module
targetScope = 'resourceGroup'

param name string
param location string
param managedIdentityPrincipalId string
param environment string = 'dev'
param tags object = {}
@secure()
param cosmosDbKey string = ''
@secure()
param storageAccountKey string = ''

// Key Vault resource
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: union(tags, {
    environment: environment
    createdBy: 'bicep'
  })
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enabledForDeployment: false
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    enableSoftDelete: false
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: managedIdentityPrincipalId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
        }
      }
    ]
  }
}

// Role assignment for managed identity - Key Vault Secrets User
resource keyVaultSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentityPrincipalId, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Placeholder secret for Foundry connection string
resource foundryConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'FoundryProjectConnectionString'
  properties: {
    value: 'PLACEHOLDER - Update after creating AI Project in Azure AI Studio'
    contentType: 'text/plain'
  }
}

// Cosmos DB Key secret
resource cosmosDbKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(cosmosDbKey)) {
  parent: keyVault
  name: 'CosmosDbKey'
  properties: {
    value: cosmosDbKey
    contentType: 'text/plain'
  }
}

// Storage Account Key secret
resource storageAccountKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(storageAccountKey)) {
  parent: keyVault
  name: 'StorageAccountKey'
  properties: {
    value: storageAccountKey
    contentType: 'text/plain'
  }
}

output id string = keyVault.id
output name string = keyVault.name
output uri string = keyVault.properties.vaultUri
output secretName string = 'FoundryProjectConnectionString'
output cosmosDbKeySecretName string = 'CosmosDbKey'
output storageAccountKeySecretName string = 'StorageAccountKey'

