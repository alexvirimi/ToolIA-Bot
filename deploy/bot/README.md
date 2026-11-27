# ToolIA-Bot con Docker Compose

Esta demo ejecuta el chatbot por consola. Docker Compose inicia dos
contenedores: **Ollama** carga los modelos y **ToolIA-Bot** busca en Chroma y
genera la respuesta. El único Dockerfile nuevo es el del bot: Ollama usa su
imagen oficial y los modelos se descargan en un volumen de Docker.

## 1. Preparar los documentos

Necesitas Docker con el comando `docker compose`. En Windows, abre Docker
Desktop y usa contenedores Linux. Para una prueba con CPU y `qwen3.5:9b`,
16 GiB de RAM disponibles para Docker son un punto de partida; mide la latencia
antes de decidir el tamaño de la VM.

Copia un corpus válido de la UTB a `data/raw/` y sus textos extraídos a
`data/processed/`. Si solo tienes los originales, ejecuta
`python scripts/extract_text.py` desde la raíz, con las dependencias del
proyecto instaladas y con el `data/manifest.json` de la descarga para conservar
las URL de los documentos. Mantén la estructura de `data/raw/`: al construir
el índice, el código verifica que cada texto coincida con el archivo original.
Un clon de Git no trae este corpus.

## 2. Descargar los modelos y construir el índice

Ejecuta estos comandos desde la raíz del repositorio:

```sh
docker compose -f deploy/bot/compose.yaml up -d --wait ollama
docker compose -f deploy/bot/compose.yaml exec ollama ollama pull embeddinggemma:300m
docker compose -f deploy/bot/compose.yaml exec ollama ollama pull qwen3.5:9b
docker compose -f deploy/bot/compose.yaml run --rm --build bot python src/embeddings.py --construir
```

`up` inicia Ollama y espera a que esté listo. `exec` descarga los modelos
dentro de Ollama. `run` crea un contenedor temporal del bot, que lee `data/`
en modo de solo lectura y guarda el índice en un volumen de Docker. Los
volúmenes conservan los modelos y el índice al recrear los contenedores;
`down -v` elimina esos volúmenes.

## 3. Probar una pregunta

```sh
docker compose -f deploy/bot/compose.yaml run --rm bot python src/rag/rag.py --pregunta "¿Cuál es el mínimo de asistencia?" --json
```

Revisa `respuesta`, `fuentes` y `latencia_total_s`. Para abrir el chat
interactivo, ejecuta `docker compose -f deploy/bot/compose.yaml run --rm bot`.

## 4. Repetir la prueba en Azure

1. Crea una VM Linux, por ejemplo Ubuntu LTS, y conéctate por SSH.
2. Instala Docker Engine y el complemento Docker Compose. Clona el repositorio
   y copia el corpus inicial a `data/` con la misma estructura de la prueba local.
3. Repite los comandos de los pasos 2 y 3 desde la VM. Los volúmenes residen
   en el disco donde Docker guarda sus datos; usa almacenamiento persistente
   de la VM, no el disco temporal de Azure.

Ollama se comunica con el bot a través de la red interna de Compose, sin publicar
el puerto `11434`. La demo se usa desde la consola de la VM y no ofrece una
interfaz web. El [Job de descarga](../azure/README.md) funciona aparte: sus
archivos no se incorporan al índice de esta demo automáticamente.
