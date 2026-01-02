// storage-account.bicep - Azure Storage Account Module
targetScope = 'resourceGroup'

param name string
param location string
param environment string = 'dev'
param containerName string = 'files'
param tags object = {}

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: union(tags, {
    environment: environment
    createdBy: 'bicep'
  })
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    accessTier: 'Hot'
  }
}

// Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

// Container for files
resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}

// Get storage account keys using listKeys function
var storageAccountKeys = storageAccount.listKeys()

output accountName string = storageAccount.name
output primaryKey string = storageAccountKeys.keys[0].value
output containerName string = container.name
output id string = storageAccount.id
output endpoint string = storageAccount.properties.primaryEndpoints.blob

