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


resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2022-03-01' existing = {
  name: containerAppsEnvironmentName
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
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [
        {
          image: imageName
          name: 'main'
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
output FUNCTIONS_FQDN string = api.properties.configuration.ingress.fqdn
output FUNCTIONS_URL string = 'https://${api.properties.configuration.ingress.fqdn}'
output FUNCTIONS_ID string = api.id
output FUNCTIONS_NAME string = api.name
