# Descarga semanal de fuentes de la UTB

Desde la raíz del repositorio, usa Azure CLI con la extensión `containerapp`
y una sesión iniciada (`az login`). Necesitas:

- Un entorno de Azure Container Apps y un grupo de recursos donde desplegar el Job.
  La plantilla busca el entorno en ese mismo grupo.
- Un recurso compartido SMB de Azure Files registrado en ese entorno en modo
  `ReadWrite`. Usa el **nombre del almacenamiento en el entorno** como
  `storageName`, que puede ser distinto del nombre del recurso compartido.
  [Registrar el almacenamiento](https://learn.microsoft.com/azure/container-apps/storage-mounts).
- Un Azure Container Registry y una identidad administrada asignada por el
  usuario con permisos de lectura en el registro (`AcrPull` en modo RBAC, o
  `Container Registry Repository Reader` en modo RBAC+ABAC). El Job usa esa
  identidad para obtener la imagen. El registro debe aceptar tokens con
  [audiencia ARM](https://learn.microsoft.com/azure/container-apps/managed-identity-image-pull).

## Construir la imagen y ejecutar una prueba

En PowerShell:

```powershell
$grupo = "<grupo-de-recursos>"
$entorno = "<entorno-de-container-apps>"
$almacenamiento = "<nombre-del-almacenamiento-en-el-entorno>"
$registro = "<nombre-del-acr>"
$identidadId = "<id-de-recurso-de-la-identidad-administrada>"
$etiqueta = "toolia-download:v1"  # Usa otra etiqueta al cambiar el script o sources.txt.

$servidor = az acr show --name $registro --query loginServer --output tsv
$region = az containerapp env show --resource-group $grupo --name $entorno --query location --output tsv
az acr build --registry $registro --image $etiqueta --file Dockerfile.azure .

$parametros = @(
    "environmentName=$entorno"
    "location=$region"
    "storageName=$almacenamiento"
    "registryServer=$servidor"
    "registryIdentityId=$identidadId"
    "image=$servidor/$etiqueta"
)

az deployment group create --resource-group $grupo --template-file deploy/azure/download-job.bicep --parameters @parametros programar=false
az containerapp job start --resource-group $grupo --name toolia-download
az containerapp job execution list --resource-group $grupo --name toolia-download --output table
```

Cuando termine, revisa los registros de la ejecución en el portal y comprueba
que `raw/`, `manifest.json` y `pages.json` se crearon en Azure Files. Inicia
una segunda ejecución y verifica que el manifiesto se reutiliza: los documentos
que sigan iguales deben aparecer como `[sin cambios]`.

## Activar el horario semanal

```powershell
az deployment group create --resource-group $grupo --template-file deploy/azure/download-job.bicep --parameters @parametros programar=true
```

El cron `0 8 * * 1` usa UTC: lunes a las 03:00 a. m. en Colombia. La primera
ejecución automática ocurre en el siguiente horario programado.

La imagen lee `data/sources.txt` y escribe en `/mnt/utb-data`. Si la UTB devuelve
una página de verificación, el script registra el fallo, conserva la copia
anterior y continúa. Un error de descarga o un documento que devuelve
HTTP 404/410 hace que la ejecución figure como fallida, aunque se hayan guardado
otras fuentes. Revisa el resumen en los registros del Job.

Para ejecutar la copia fuera del contenedor, instala `deploy/azure/requirements.txt`
y `python -m playwright install chromium --only-shell`. Define `TOOLIA_DATA_DIR`
con una ruta de salida distinta de `data/` y ejecuta
`python scripts/download_data_azure.py`.
