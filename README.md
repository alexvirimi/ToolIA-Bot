# ToolIA-Bot

Asistente virtual institucional de la Universidad Tecnológica de Bolívar (UTB), diseñado para responder preguntas en lenguaje natural sobre reglamentos, manual de convivencia, calendario académico, procesos administrativos, requisitos, servicios y demás información publicada en la página web oficial de la UTB.

El sistema se evalúa como una propuesta de investigación con tres variantes:

| Variante | Descripción |
|---|---|
| **Línea base** | Modelo generativo sin recuperación (responde solo con el LLM). |
| **RAG** | Modelo con recuperación de fragmentos desde índice vectorial (variante histórica). |
| **RAG mejorado** | RAG con recuperación por fusión densa+léxica y diversidad, prompt conciso y regla de abstención SIN_EVIDENCIA (variante medida). |

---

## Estructura del repositorio

```
ToolIA-Bot/
├── rag_test/                 # Código del sistema RAG y pruebas de calidad
├── src/                      # Código fuente (API, chat, embeddings, RAG, baseline)
├── experiments/              # Resultados de experimentos (línea base y RAG)
├── rag_test/corridas/        # Corridas de evaluación del RAG mejorado
├── docs/                     # Documentos de análisis (métricas y comparativas)
├── deploy/                   # Guías de despliegue (Docker, Azure)
├── frontend/                 # Interfaz web (React + Vite)
├── notebooks/                # Notebook CRISP-ML(Q)
├── scripts/                  # Scripts de descarga y extracción de datos
└── data/                     # Datos institucionales (no versionados)
```

---

## Descarga semanal de fuentes en Azure

El [Job de Azure Container Apps](deploy/azure/README.md) ejecuta `scripts/download_data_azure.py` los lunes a las 03:00 a. m. (hora de Colombia) y guarda los resultados en Azure Files. `scripts/download_data.py` sigue disponible para descargas manuales.

---

## Demo del chatbot con Docker

La [guía de Docker Compose](deploy/bot/README.md) explica cómo probar el chatbot por consola con Ollama y llevarlo a una VM Linux de Azure.

---

## Instalación y ejecución

### Requisitos previos

- Python 3.14
- [Ollama](https://ollama.com/download) instalado y en ejecución
- Modelo `qwen3.5:9b` y `embeddinggemma:300m` descargados en Ollama

### Pasos iniciales

```bash
# 1. Descargar modelos de Ollama
ollama pull qwen3.5:9b
ollama pull embeddinggemma:300m

# 2. Crear y activar entorno virtual (recomendado)
python -m venv .venv314
.\.venv314\Scripts\Activate.ps1   # Windows
# source .venv314/bin/activate    # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Ejecutar la línea base

La línea base responde sin recuperar fragmentos, sirviendo como punto de comparación.

```powershell
python src/baseline/run_experiment.py
```

Luego de etiquetar manualmente `experiments/baseline/respuestas.csv`, calcular las métricas:

```powershell
python src/evaluate.py
```

---

## Ejecutar el sistema RAG (variante histórica)

El RAG usa el mismo LLM que la línea base (`qwen3.5:9b`, temperatura 0, seed 42) y añade recuperación de fragmentos desde el índice vectorial.

### 1. Construir el índice vectorial

```powershell
python src/embeddings.py --construir
```

Si no hay datos en `data/processed/`:

```powershell
python scripts/sources_filler.py
python scripts/download_data.py
python scripts/extract_text.py
```

### 2. Verificar la recuperación (sin LLM)

```powershell
python src/embeddings.py --pregunta "¿Qué se propone la UTB para mejorar la calidad de la formación que ofrece?"
```

### 3. Hacer preguntas al chatbot RAG

```powershell
python src/rag/rag.py                                   # chat por consola
python src/rag/rag.py --pregunta "¿...?" --json         # una sola pregunta
```

Opciones: `--k` (fragmentos a recuperar, 5 por defecto), `--umbral` (similitud mínima).

### 4. Correr el conjunto de preguntas

```powershell
python src/rag/run_rag_exp.py --limit 5 --nombre rag_prueba   # prueba rápida
python src/rag/run_rag_exp.py                                # prueba completa (57 preguntas)
```

### 5. Etiquetar y calcular métricas

Abrir `experiments/rag/respuestas.csv` y llenar las columnas `etiqueta` y `fidelidad`, luego:

```powershell
python src/rag/metricas_rag.py
```

---

## Ejecutar el RAG mejorado (variante medida)

El RAG mejorado es la versión evaluada formalmente en la propuesta de investigación. Incluye recuperación por fusión densa+léxica con diversidad, prompt conciso y regla de abstención SIN_EVIDENCIA.

### 1. Correr el conjunto de preguntas con el RAG mejorado

```powershell
python src/rag/run_rag_exp.py --nombre mejora80-final2-57
```

### 2. Etiquetar manualmente

Abrir `rag_test/corridas/mejora80-final2-57/respuestas.csv` y llenar:

- `etiqueta`: `correcta`, `parcial`, `incorrecta`, `alucinacion` o `abstencion`
- `fidelidad`: `si` o `no` (solo en respuestas donde el sistema no se abstuvo)
- `observaciones`: justificación de la etiqueta

### 3. Calcular métricas de calidad

```powershell
python -m rag_test.calidad evaluar mejora80-final2-57 --anotaciones "rag_test/evaluaciones/mejora80-20261126/mejora80-final2-57.anotaciones.json" --baseline "experiments/baseline/respuestas.csv"
```

Esto genera:
- `rag_test/corridas/mejora80-final2-57/metricas.json`
- `rag_test/corridas/mejora80-final2-57/evaluacion_evidencia.json`

---

## Ejecutar la API y el frontend

### API (FastAPI)

```powershell
.\.venv314\Scripts\python.exe src/api/app.py
```

La API expone:

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/health` | Health check con detalles del modelo y fragmentos |
| POST | `/api/chat` | Enviar pregunta al bot |
| POST | `/api/chat/{session_id}/close` | Cerrar una sesión |

### Frontend (React + Vite)

```powershell
cd frontend
npm install
npm run dev
```

El frontend se conecta a la API en `http://127.0.0.1:8000` por defecto. Puede cambiarse con la variable de entorno `VITE_API_URL`.

---

## Documentación de análisis

Los documentos en `docs/` contienen los resultados formales de la evaluación:

| Archivo | Contenido |
|---|---|
| `docs/analisis_rag_mejora.md` | Análisis detallado del RAG mejorado (métricas, casos de error, umbrales) |
| `docs/analisis_comparativo.md` | Comparativa completa: línea base vs. RAG vs. RAG mejorado |

### Resultados clave del RAG mejorado (`mejora80-final2-57`)

| Métrica | Valor | Umbral | Cumple |
|---|---|---|---|
| Exactitud con parciales | 75.0 % | ≥ 75 % | Sí |
| Fidelidad | 93.2 % | ≥ 80 % | Sí |
| Alucinación | 0.0 % | ≤ 15 % | Sí |
| Abstención adecuada | 100.0 % | ≥ 70 % | Sí |
| Recall@5 operacional | 89.6 % | ≥ 80 % | Sí |
| Latencia promedio | 10.71 s | ≤ 10 s | No |

**Resultado:** 5 de 6 umbrales cumplidos → éxito según la propuesta.

---

## CRISP-ML(Q): análisis de datos y embeddings

**Alcance:** notebook exploratorio y auxiliar reutilizable. No crea otra app ni ejecuta el experimento global de respuestas del chatbot.

- `notebooks/ToolIA_Bot_CRISP_MLQ.ipynb`: análisis, comparación TF-IDF/embeddings, incertidumbre, errores, recursos y pruebas de persistencia/actualización.
- `src/embeddings.py`: carga de textos, fragmentación, embeddings con Ollama y búsqueda en Chroma.
- `scripts/extract_text.py`: extractor existente del equipo.

### Ejecutar el notebook

Prerrequisitos: Ollama abierto, Python 3.14 y los datos institucionales en `data/raw/` y `data/processed/` (no versionados).

```powershell
py -3.14 -m venv .venv314
.\.venv314\Scripts\python.exe -m pip install -r requirements.txt
ollama pull embeddinggemma:300m
.\.venv314\Scripts\python.exe -m nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=-1 notebooks/ToolIA_Bot_CRISP_MLQ.ipynb
```

---

## Despliegue

- [Docker Compose](deploy/bot/README.md): prueba por consola con Ollama y despliegue en VM Linux de Azure.
- [Azure Container Apps](deploy/azure/README.md): job semanal de descarga de fuentes.
