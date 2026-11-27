param environmentName string
param location string
param storageName string
param registryServer string
param registryIdentityId string
param image string
param jobName string = 'toolia-download'
param programar bool = true

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: environmentName
}

resource job 'Microsoft.App/jobs@2025-01-01' = {
  name: jobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${registryIdentityId}': {}
    }
  }
  properties: {
    environmentId: environment.id
    configuration: union({
      replicaTimeout: 10800
      replicaRetryLimit: 0
      registries: [
        {
          server: registryServer
          identity: registryIdentityId
        }
      ]
    }, programar ? {
      triggerType: 'Schedule'
      scheduleTriggerConfig: {
        cronExpression: '0 8 * * 1'
        parallelism: 1
        replicaCompletionCount: 1
      }
    } : {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    })
    template: {
      containers: [
        {
          name: 'descarga'
          image: image
          env: [
            {
              name: 'TOOLIA_DATA_DIR'
              value: '/mnt/utb-data'
            }
          ]
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          volumeMounts: [
            {
              volumeName: 'utb-data'
              mountPath: '/mnt/utb-data'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'utb-data'
          storageType: 'AzureFile'
          storageName: storageName
          mountOptions: 'uid=10001,gid=10001,file_mode=0660,dir_mode=0770'
        }
      ]
    }
  }
}
