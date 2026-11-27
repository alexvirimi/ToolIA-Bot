# Descarga semanal de fuentes de la UTB

El trabajo programado de Azure Container Apps consulta las fuentes de la UTB
y guarda los resultados en Azure Files. Esta guía describe cómo probar la
descarga antes de activar la ejecución semanal.

## Requisitos previos

Los comandos se ejecutan desde la raíz del repositorio. Se requiere Azure CLI
con la extensión `containerapp` y una sesión iniciada con `az login`.
Antes del despliegue, confirme que dispone de los siguientes recursos:

- Un entorno de Azure Container Apps en el mismo grupo de recursos donde se
  desplegará el trabajo. La plantilla busca el entorno en ese grupo.
- Un recurso compartido SMB de Azure Files
  [registrado en el entorno](https://learn.microsoft.com/azure/container-apps/storage-mounts)
  en modo `ReadWrite`. El parámetro `storageName` recibe el **nombre registrado
  en el entorno**, que puede ser distinto del nombre del recurso compartido.
- Un registro de Azure Container Registry y una identidad administrada asignada
  por el usuario. El trabajo utiliza esa identidad para descargar la imagen,
  por lo que se requiere el rol `AcrPull` en modo RBAC o
  `Container Registry Repository Reader` en modo RBAC+ABAC. El registro debe
  aceptar tokens con
  [audiencia ARM](https://learn.microsoft.com/azure/container-apps/managed-identity-image-pull).

## Construir la imagen y ejecutar una prueba

En PowerShell, sustituya los valores entre `< >` por los de su entorno. Estos
comandos construyen la imagen en el registro, despliegan el trabajo en modo
manual e inician una primera ejecución.

```powershell
$grupo = "<grupo-de-recursos>"
$entorno = "<entorno-de-container-apps>"
$almacenamiento = "<nombre-del-almacenamiento-en-el-entorno>"
$registro = "<nombre-del-acr>"
$identidadId = "<id-de-recurso-de-la-identidad-administrada>"
$etiqueta = "toolia-download:v1"

$servidor = az acr show --name $registro --query loginServer --output tsv
$region = az containerapp env show --resource-group $grupo --name $entorno --query location --output tsv
az acr build --registry $registro --image $etiqueta --file deploy/azure/Dockerfile .

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

Cuando finalice la ejecución, revise los registros en el portal y compruebe
que `raw/`, `manifest.json` y `pages.json` se hayan creado en Azure Files.
Inicie una segunda ejecución para verificar que se reutiliza el manifiesto:
los documentos que no hayan cambiado deben aparecer como `[sin cambios]`.

Si cambia el script o `data/sources.txt`, utilice una etiqueta nueva al construir
la imagen.

## Activar el horario semanal

Una vez comprobada la descarga manual, vuelva a aplicar la plantilla con
`programar=true`. Si abre otra sesión de PowerShell, defina primero las
variables del apartado anterior.

```powershell
az deployment group create --resource-group $grupo --template-file deploy/azure/download-job.bicep --parameters @parametros programar=true
```

Azure interpreta la expresión cron `0 8 * * 1` en UTC, lo que corresponde a
los lunes a las 03:00 a. m. en Colombia. La primera ejecución automática
tendrá lugar en la siguiente fecha programada.

## Consultar el resultado de una ejecución

El descargador lee la lista de fuentes de `data/sources.txt` y escribe los
resultados en `/mnt/utb-data`. Si una fuente solicita verificación, el script
registra el fallo, conserva la última copia disponible y continúa con las demás
fuentes. Un error de descarga o un documento que responda con HTTP 404 o 410
hace que Azure marque la ejecución como fallida, aunque otras fuentes se hayan
guardado correctamente. El resumen de los registros permite identificar qué
ocurrió en cada caso.

## Ejecutar el descargador fuera del contenedor

Instale las dependencias de `deploy/azure/requirements.txt` y luego instale
Chromium con `python -m playwright install chromium --only-shell`. Defina
`TOOLIA_DATA_DIR` con una ruta de salida distinta de `data/` y ejecute
`python scripts/download_data_azure.py`.
