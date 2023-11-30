targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param resourceGroupName string = ''

param vnetName string = ''
param vnetRgName string = ''

param appServicePlanName string = ''
param backendServiceName string = ''
param webappPrivateDnsZoneId string = ''
param webappDeployPrivateEP bool = false // This needs to be set to false if the app needs to be deployed seamlessly. At the end, set this to true and run azd provision (instead of azd up)

param searchServiceName string = ''
param searchServiceResourceGroupName string = ''
param searchServiceResourceGroupLocation string = location
param searchServiceSkuName string = 'standard'
param searchPrivateDnsZoneId string = ''
param searchDeployPrivateEP bool = false
param searchIndexName string = 'kitchat-searchindex-all'

param storageAccountName string = ''
param storageResourceGroupName string = ''
param storageResourceGroupLocation string = location
param storageContainerName string = 'content'
param storageBlobPrivateDnsZoneId string = ''
param storageDeployPrivateEP bool = false

param openAiServiceName string = ''
param openAiResourceGroupName string = ''
param openAiResourceGroupLocation string = location
param openAiSkuName string = 'S0'
param openAiPrivateDnsZoneId string = ''
param openAiDeployPrivateEP bool = false

param subnet_name_1 string = 'JPSNdevprivate'
param subnet_name_2 string = 'JPSNdevwebapp'

@description('Id of the user or app to assign application roles')
param principalIds array = []
param principalType string = 'Group'

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

var webappName = !empty(backendServiceName) ? backendServiceName : '${abbrs.webSitesAppService}backend-${resourceToken}'
var openAiName = !empty(openAiServiceName) ? openAiServiceName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
var searchName = !empty(searchServiceName) ? searchServiceName : 'gptkb-${resourceToken}'
var storageName = !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

resource searchServiceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(searchServiceResourceGroupName)) {
  name: !empty(searchServiceResourceGroupName) ? searchServiceResourceGroupName : resourceGroup.name
}

resource storageResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(storageResourceGroupName)) {
  name: !empty(storageResourceGroupName) ? storageResourceGroupName : resourceGroup.name
}

// Create an App Service Plan to group applications under the same payment plan and SKU
module appServicePlan 'core/host/appserviceplan.bicep' = {
  name: 'appserviceplan'
  scope: resourceGroup
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'B1'
      capacity: 1
    }
    kind: 'linux'
  }
}

// The application frontend
module backend 'core/host/appservice.bicep' = {
  name: 'web'
  scope: resourceGroup
  params: {
    name: webappName
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    appServicePlanId: appServicePlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.11'
    scmDoBuildDuringDeployment: true
    managedIdentity: true
    appSettings: {
      AZURE_STORAGE_ACCOUNT: storage.outputs.name
      AZURE_STORAGE_CONTAINER: storageContainerName
      AZURE_OPENAI_SERVICE: openAi.outputs.name
      AZURE_SEARCH_INDEX: searchIndexName
      AZURE_SEARCH_SERVICE: searchService.outputs.name
    }
    vnetIntegrationSubnetId: '${subscription().id}/resourceGroups/${vnetRgName}/providers/Microsoft.Network/virtualNetworks/${vnetName}/subnets/${subnet_name_2}'
  }
}

module backendPe 'core/network/pe.bicep' = if (webappDeployPrivateEP) {
  name: 'web-pe'
  scope: resourceGroup
  params: {
    id: backend.outputs.id
    name: '${webappName}-pe'
    location: location
    subResourceName: 'sites'
    subnetId: '${subscription().id}/resourceGroups/${vnetRgName}/providers/Microsoft.Network/virtualNetworks/${vnetName}/subnets/${subnet_name_1}'
    privateDnsZoneId: webappPrivateDnsZoneId
  }
}

module openAi 'core/ai/cognitiveservices.bicep' = {
  name: 'openai'
  scope: openAiResourceGroup
  params: {
    name: openAiName
    location: openAiResourceGroupLocation
    tags: tags
    sku: {
      name: openAiSkuName
    }
    deployments: [
      {
        name: 'gpt-35-turbo'
        model: {
          format: 'OpenAI'
          name: 'gpt-35-turbo'
          version: '0613'
        }
        sku: {
          name: 'Standard'
          capacity: 10
        }
      }
      {
        name: 'gpt-4'
        model: {
          format: 'OpenAI'
          name: 'gpt-4'
          version: '0613'
        }
        sku: {
          name: 'Standard'
          capacity: 5
        }
      }
      {
        name: 'text-embedding-ada-002'
        model: {
          format: 'OpenAI'
          name: 'text-embedding-ada-002'
          version: '2'
        }
        capacity: 10
      }
    ]
  }
}

module openAiPrivateEP 'core/network/pe.bicep' = if (openAiDeployPrivateEP) {
  name: 'openai-pe'
  scope: resourceGroup
  params: {
    id: openAi.outputs.id
    name: '${openAiName}-pe'
    location: location
    subResourceName: 'account'
    subnetId: '${subscription().id}/resourceGroups/${vnetRgName}/providers/Microsoft.Network/virtualNetworks/${vnetName}/subnets/${subnet_name_1}'
    privateDnsZoneId: openAiPrivateDnsZoneId
  }
}

module searchService 'core/search/search-services.bicep' = {
  name: 'search-service'
  scope: searchServiceResourceGroup
  params: {
    name: searchName
    location: searchServiceResourceGroupLocation
    tags: tags
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    sku: {
      name: searchServiceSkuName
    }
  }
}

module searchPrivateEP 'core/network/pe.bicep' = if (searchDeployPrivateEP) {
  name: 'search-pe'
  scope: resourceGroup
  params: {
    id: searchService.outputs.id
    name: '${searchName}-pe'
    location: location
    subResourceName: 'searchService'
    subnetId: '${subscription().id}/resourceGroups/${vnetRgName}/providers/Microsoft.Network/virtualNetworks/${vnetName}/subnets/${subnet_name_1}'
    privateDnsZoneId: searchPrivateDnsZoneId
  }
}

module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: storageResourceGroup
  params: {
    name: storageName
    location: storageResourceGroupLocation
    tags: tags
    publicNetworkAccess: 'Enabled'
    sku: {
      name: 'Standard_ZRS'
    }
    deleteRetentionPolicy: {
      enabled: true
      days: 2
    }
    containers: [
      {
        name: storageContainerName
        publicAccess: 'None'
      }
    ]
  }
}

module storagePrivateEP 'core/network/pe.bicep' = if (storageDeployPrivateEP) {
  name: 'storage-pe'
  scope: resourceGroup
  params: {
    id: storage.outputs.id
    name: '${storageName}-pe'
    location: location
    subResourceName: 'blob'
    subnetId: '${subscription().id}/resourceGroups/${vnetRgName}/providers/Microsoft.Network/virtualNetworks/${vnetName}/subnets/${subnet_name_1}'
    privateDnsZoneId: storageBlobPrivateDnsZoneId
  }
}

// USER ROLES
module openAiRoleUser 'core/security/role.bicep' = [for principalId in principalIds: {
  scope: openAiResourceGroup
  name: 'openai-role-user-${principalId}'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: principalType
  }
}]

module storageRoleUser 'core/security/role.bicep' = [for principalId in principalIds: {
  scope: storageResourceGroup
  name: 'storage-role-user-${principalId}'
  params: {
    principalId: principalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: principalType
  }
}]

module storageContribRoleUser 'core/security/role.bicep' = [for principalId in principalIds: {
  scope: storageResourceGroup
  name: 'storage-contribrole-user-${principalId}'
  params: {
    principalId: principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    principalType: principalType
  }
}]

module searchRoleUser 'core/security/role.bicep' = [for principalId in principalIds: {
  scope: searchServiceResourceGroup
  name: 'search-role-user-${principalId}'
  params: {
    principalId: principalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: principalType
  }
}]

module searchContribRoleUser 'core/security/role.bicep' = [for principalId in principalIds: {
  scope: searchServiceResourceGroup
  name: 'search-contrib-role-user-${principalId}'
  params: {
    principalId: principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
    principalType: principalType
  }
}]

// SYSTEM IDENTITIES
module openAiRoleBackend 'core/security/role.bicep' = {
  scope: openAiResourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}

module storageRoleBackend 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: 'ServicePrincipal'
  }
}

module searchRoleBackend 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'ServicePrincipal'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

output AZURE_OPENAI_SERVICE string = openAi.outputs.name
output AZURE_OPENAI_RESOURCE_GROUP string = openAiResourceGroup.name

output AZURE_SEARCH_SERVICE string = searchService.outputs.name
output AZURE_SEARCH_SERVICE_RESOURCE_GROUP string = searchServiceResourceGroup.name

output AZURE_STORAGE_ACCOUNT string = storage.outputs.name
output AZURE_STORAGE_CONTAINER string = storageContainerName
output AZURE_STORAGE_RESOURCE_GROUP string = storageResourceGroup.name

output BACKEND_URI string = backend.outputs.uri
