# ToolIA-Bot con Docker Compose

Esta guía explica cómo probar ToolIA-Bot por consola, primero en un equipo
local y luego, si se requiere, en una máquina virtual de Azure. Docker Compose
coordina los dos servicios: ToolIA-Bot consulta el índice de Chroma y utiliza
Ollama para generar los embeddings y las respuestas. El bot se construye con
el Dockerfile de esta carpeta y Ollama se ejecuta con su imagen oficial.

## 1. Preparar los documentos

Para seguir esta guía se requiere Docker con el comando `docker compose`.
En Windows, Docker Desktop debe estar configurado para usar contenedores Linux.
Para una primera prueba con `qwen3.5:9b` en CPU, 16 GiB de RAM disponibles para
Docker son un punto de partida. La latencia que se observe en esa prueba
servirá para elegir el tamaño de la máquina virtual.

El repositorio no incluye los documentos de la UTB. Copie los archivos
originales a `data/raw/` y los textos extraídos a `data/processed/`. Si solo
dispone de los originales, instale las dependencias del proyecto y ejecute
`python scripts/extract_text.py` desde la raíz del repositorio. El archivo
`data/manifest.json` de la descarga permite conservar las URL de los documentos.
Mantenga la estructura de `data/raw/`, ya que el índice se construye verificando
que cada texto corresponda a su archivo original.

## 2. Descargar los modelos y construir el índice

Desde la raíz del repositorio, ejecute los siguientes comandos en orden:

```sh
docker compose -f deploy/bot/compose.yaml up -d --wait ollama
docker compose -f deploy/bot/compose.yaml exec ollama ollama pull embeddinggemma:300m
docker compose -f deploy/bot/compose.yaml exec ollama ollama pull qwen3.5:9b
docker compose -f deploy/bot/compose.yaml run --rm --build bot python src/embeddings.py --construir
```

El primer comando inicia Ollama y espera a que esté listo. Los dos siguientes
descargan los modelos y el último construye el índice en un contenedor temporal
del bot. Ese contenedor consulta `data/` en modo de solo lectura.

Los modelos y el índice se guardan en volúmenes de Docker, por lo que se
conservan al recrear los contenedores. El comando `down -v` elimina esos
volúmenes, junto con su contenido.

## 3. Hacer una consulta

```sh
docker compose -f deploy/bot/compose.yaml run --rm bot python src/rag/rag.py --pregunta "¿Cuál es el mínimo de asistencia?" --json
```

La salida en JSON permite revisar el texto de la `respuesta`, las `fuentes`
consultadas y el tiempo total en `latencia_total_s`. Para iniciar una sesión
interactiva en la consola, ejecute
`docker compose -f deploy/bot/compose.yaml run --rm bot`.

## 4. Repetir la prueba en Azure

1. Cree una máquina virtual Linux, por ejemplo con Ubuntu LTS, y conéctese por SSH.
2. Instale Docker Engine y el complemento Docker Compose. Clone el repositorio y
   copie los documentos a `data/` con la misma estructura de la prueba local.
3. Repita los pasos 2 y 3 de esta guía en la máquina virtual. Configure Docker
   para almacenar los volúmenes en un disco persistente de la máquina, fuera
   del disco temporal de Azure.

Esta configuración permite usar el chatbot desde la terminal de la máquina
virtual. Ollama se comunica con el bot por la red interna de Compose, sin
exponer el puerto `11434`. El [Job de descarga semanal](../azure/README.md)
funciona por separado: los archivos que descarga no se incorporan
automáticamente al índice.
