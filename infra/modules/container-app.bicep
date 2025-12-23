// container-app.bicep - Reusable Container App Module using Azure Verified Modules
targetScope = 'resourceGroup'

// Parameters
param name string
param location string
param containerAppEnvId string
param image string
@description('Image tag to use. Defaults to latest')
param imageTag string = 'latest'
param targetPort int = 80
param acrLoginServer string
param managedIdentityId string
param ingressExternal bool = true
param allowInsecure bool = false
param envVars array = []
param tags object = {}

// Container App using AVM module
module containerApp 'br/public:avm/res/app/container-app:0.8.0' = {
  name: '${name}-deployment'
  params: {
    name: name
    location: location
    environmentResourceId: containerAppEnvId
    ingressTargetPort: targetPort
    ingressExternal: ingressExternal
    ingressAllowInsecure: allowInsecure
    scaleMinReplicas: 1
    scaleMaxReplicas: 3
    containers: [
      {
        name: name
        image: '${image}:${imageTag}'
        env: envVars
        resources: {
          cpu: json('0.5')
          memory: '1.0Gi'
        }
      }
    ]
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: [managedIdentityId]
    }
    registries: [
      {
        server: acrLoginServer
        identity: managedIdentityId
      }
    ]
    tags: tags
  }
}

// Output the FQDN for the container app
output fqdn string = containerApp.outputs.fqdn
output url string = 'https://${containerApp.outputs.fqdn}'
output id string = containerApp.outputs.resourceId
output name string = containerApp.outputs.name
