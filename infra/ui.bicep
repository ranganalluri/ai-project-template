// ui.bicep - UI Service Container App Deployment
// This is used by azd deploy to update the UI service with new container images
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
param apiUrl string


resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2022-03-01' existing = {
  name: containerAppsEnvironmentName
}

resource ui 'Microsoft.App/containerApps@2025-02-02-preview' = {
  name: '${resourceNamePrefix}-ui-${resourceIndexSuffix}'
  location: location
  tags: {
    'azd-env-name': environmentName
    'azd-service-name': 'ui'
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 5173
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
          env: [
            {
              name: 'VITE_API_URL'
              value: apiUrl
            }
          ]
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
output UI_FQDN string = ui.properties.configuration.ingress.fqdn
output UI_URL string = 'https://${ui.properties.configuration.ingress.fqdn}'
output UI_ID string = ui.id
output UI_NAME string = ui.name
