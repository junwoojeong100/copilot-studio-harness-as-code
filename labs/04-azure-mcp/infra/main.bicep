// Lab 04 - Issue-triage MCP server on Azure Container Apps (ACA)
//
// Resources: ACR (Basic) + Container Apps environment (Consumption) + Container App
// (external HTTPS ingress, system-assigned identity with AcrPull on the registry).
//
// Two-phase rollout (see scripts/deploy.sh):
//   1) imageTag == ''  -> "bootstrap": the app starts from a public placeholder image so that its
//      system-assigned identity exists and can be granted AcrPull. (The identity cannot get a role
//      before the app exists, and the app cannot pull from ACR before it has the role.)
//   2) imageTag == '<tag>' -> the app runs <acr>.azurecr.io/<imageRepository>:<tag>, pulled with
//      the managed identity (no registry password anywhere).

targetScope = 'resourceGroup'

@description('Azure region. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Short prefix used in resource names.')
@minLength(3)
@maxLength(12)
param baseName string = 'csharness'

@description('Image tag in the ACR repository. Empty = bootstrap mode (placeholder image).')
param imageTag string = ''

@description('Repository name inside the registry.')
param imageRepository string = 'csharness-mcp'

@description('API key required in the x-api-key header for /mcp. Stored as a Container Apps secret.')
@secure()
@minLength(16)
param apiKey string

@description('Non-secret fingerprint of the key. It changes whenever the key changes, which makes Container Apps create a new revision so that running replicas pick up the new secret value.')
param keyFingerprint string = ''

@description('Tag: date after which the resources can be deleted.')
param deleteAfter string = '2026-10-24'

var tags = {
  purpose: 'copilot-studio-harness-lab'
  deleteAfter: deleteAfter
}

var bootstrap = empty(imageTag)
var acrName = toLower('acr${baseName}${uniqueString(resourceGroup().id)}')
var environmentName = 'cae-${baseName}'
var appName = 'ca-${baseName}-mcp'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var placeholderImage = 'mcr.microsoft.com/k8se/quickstart:latest'

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

// No appLogsConfiguration -> no Log Analytics workspace (cheapest). Live logs still work through
// `az containerapp logs show` (log stream). Add a workspace here if you need log retention/queries.
resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    zoneRedundant: false
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      maxInactiveRevisions: 3
      ingress: {
        external: true
        targetPort: bootstrap ? 80 : 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: bootstrap ? [] : [
        {
          server: registry.properties.loginServer
          identity: 'system'
        }
      ]
      secrets: [
        {
          name: 'api-key'
          value: apiKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp'
          image: bootstrap ? placeholderImage : '${registry.properties.loginServer}/${imageRepository}:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'API_KEY'
              secretRef: 'api-key'
            }
            {
              name: 'API_KEY_FINGERPRINT'
              value: keyFingerprint
            }
          ]
          probes: bootstrap ? [] : [
            {
              type: 'Startup'
              httpGet: {
                path: '/healthz'
                port: 8000
              }
              periodSeconds: 3
              failureThreshold: 20
              timeoutSeconds: 3
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 8000
              }
              periodSeconds: 20
              failureThreshold: 3
              timeoutSeconds: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/healthz'
                port: 8000
              }
              periodSeconds: 10
              failureThreshold: 3
              timeoutSeconds: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
        rules: [
          {
            name: 'http-concurrency'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, app.id, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: app.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
output appName string = app.name
output acrName string = registry.name
output acrLoginServer string = registry.properties.loginServer
output environmentName string = environment.name
