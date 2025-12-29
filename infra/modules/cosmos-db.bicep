// cosmos-db.bicep - Azure Cosmos DB Account and Containers
param name string
param location string
param environment string
param tags object = {}

// Cosmos DB Account
resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
      maxIntervalInSeconds: 5
      maxStalenessPrefix: 100
    }
    enableMultipleWriteLocations: false
    enableFreeTier: false
    publicNetworkAccess: 'Enabled'
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}


// Cosmos DB Database (new)
resource cosmosDatabaseNew 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosDbAccount
  name: 'agenticdb'
  properties: {
    resource: {
      id: 'agenticdb'
    }
  }
}

// Users Container
resource usersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabaseNew
  name: 'users'
  properties: {
    resource: {
      id: 'users'
      partitionKey: {
        paths: [
          '/user_id'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
      defaultTtl: -1
    }
  }
}

// Agent Store Container (single container for all agent platform data)
resource agentStoreContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabaseNew
  name: 'agentStore'
  properties: {
    resource: {
      id: 'agentStore'
      partitionKey: {
        paths: [
          '/pk'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
          {
            path: '/content/*'
          }
          {
            path: '/stepsSummary/*'
          }
        ]
        compositeIndexes: [
          [
            {
              path: '/type'
              order: 'ascending'
            }
            {
              path: '/seq'
              order: 'descending'
            }
          ]
          [
            {
              path: '/type'
              order: 'ascending'
            }
            {
              path: '/runSeq'
              order: 'descending'
            }
          ]
          [
            {
              path: '/type'
              order: 'ascending'
            }
            {
              path: '/requestedAt'
              order: 'descending'
            }
          ]
        ]
      }
      defaultTtl: -1
    }
  }
}

// Outputs
output accountName string = cosmosDbAccount.name
output endpoint string = cosmosDbAccount.properties.documentEndpoint
output key string = cosmosDbAccount.listKeys().primaryMasterKey
output databaseName string = cosmosDatabaseNew.name
output accountId string = cosmosDbAccount.id
