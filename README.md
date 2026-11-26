# ToolIA-Bot

“ToolIA-Bot” será un chatbot universitario diseñado para centralizar y facilitar el acceso a la 
información institucional de la Universidad Tecnológica de Bolívar (UTB). Permitirá que 
estudiantes, aspirantes, docentes y administrativos realicen preguntas en lenguaje natural 
sobre reglamentos, manual de convivencia, calendario académico, procesos administrativos, 
requisitos, servicios y demás información publicada en la página web.

## Descarga semanal de fuentes en Azure

El [Job de Azure Container Apps](deploy/azure/README.md) ejecuta
`scripts/download_data_azure.py` los lunes a las 03:00 a. m. de Colombia
y guarda los resultados en Azure Files. `scripts/download_data.py` sigue
disponible para descargas manuales.

## Instalación y ejecución

**Requisitos previos:** Python 3.14.

1. Instalar Ollama: https://ollama.com/download
2. Descargar el modelo:
   ```bash
   ollama pull qwen3.5:9b
   ```
3. (Recomendado) Crear un entorno virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate 
      # O
   .\.venv314\Scripts\Activate.ps1 # Windows (Mac/Linux: source .venv/bin/activate)
   ```
4. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
5. Ejecutar la línea base (con Ollama abierto):
   ```bash
   python src/baseline/run_experiment.py
   ```
6. Calcular las métricas, después de etiquetar `experiments/baseline/respuestas.csv`:
   ```bash
   python src/evaluate.py
   ```

## CRISP-ML(Q): análisis de datos y embeddings

**Alcance:** un notebook exploratorio y un único auxiliar reutilizable. No crea otra
app ni ejecuta el experimento global de respuestas del chatbot.

- `notebooks/ToolIA_Bot_CRISP_MLQ.ipynb`: análisis, comparación TF-IDF/embeddings,
  incertidumbre, errores, recursos y pruebas de persistencia/actualización.
- `src/embeddings.py`: carga de textos, fragmentación, embeddings con Ollama y
  búsqueda en Chroma. Se importa desde el notebook y después desde el chatbot.
- `scripts/extract_text.py`: extractor existente del equipo. La limpieza conserva
  números aislados y las páginas vacías permiten detectar extracción incompleta.

### Ejecutar el notebook

Prerrequisitos explícitos: Ollama abierto, Python 3.14 y los datos institucionales
de Alex en `data/raw/` y `data/processed/`. Estos datos no están versionados. Si
faltan los textos, ejecutar el extractor existente; no basta con clonar el código.
Desde PowerShell en la raíz, usando el entorno dedicado:

```powershell
py -3.14 -m venv .venv314
.\.venv314\Scripts\python.exe -m pip install -r requirements.txt
ollama pull embeddinggemma:300m
.\.venv314\Scripts\python.exe -m nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=-1 notebooks/ToolIA_Bot_CRISP_MLQ.ipynb
```

También se puede abrir en VS Code/Jupyter y seleccionar el kernel `.venv314`.
La primera ejecución construye el índice si falta. Las siguientes reutilizan
índice y consultas guardadas; `REEXTRAER`, `RECONSTRUIR` y
`RECALCULAR_CONSULTAS` son opciones explícitas del notebook.
Cambiar datos/modelo/configuración requiere otra carpeta de resultados o una
reconstrucción consciente, no mezclar experimentos.

### Componente para el chatbot

```powershell
.\.venv314\Scripts\python.exe src/embeddings.py --construir
.\.venv314\Scripts\python.exe src/embeddings.py --pregunta "¿Cuál es el mínimo de asistencia?"
```

Dentro del código del bot, importar `cargar_indice` desde `embeddings` y utilizar
`indice.buscar(pregunta, k=5)`; los resultados contienen texto y procedencia.
El índice se guarda por defecto en `%LOCALAPPDATA%/ToolIA-Bot/crisp_vectorial`,
fuera de OneDrive. Puede cambiarse con `TOOLIA_INDICE`.

### Resultados y límites

Los artefactos reproducibles están en `experiments/crisp_datos/`: protocolo y
hashes, inventario, calidad de datos, consultas reales, comparación de recuperación,
errores y mediciones CodeCarbon (Cartagena, Colombia, modo máquina para incluir
Ollama). Los archivos son salidas del análisis, no nuevos módulos de aplicación.

No confundir métricas: HitFuente y cobertura de artículos son diagnósticos
automáticos, no fidelidad ni respuestas completas. Para Recall@5 de evidencia
hay que revisar `revision_evidencias.csv`, dividir las referencias en unidades
necesarias y registrar revisor/verificación. El notebook deja esa compuerta
incompleta mientras falte revisión. No se modifican las 57 preguntas ni la línea
base histórica. Los PDF escaneados/OCR pendientes se informan; no se afirma que
todo el corpus descargado esté indexado.

## Ejecutar el sistema RAG paso a paso

El RAG usa el **mismo LLM que la línea base** (`qwen3.5:9b`, temperatura 0, seed 42)
y añade recuperación de fragmentos desde el índice vectorial. Así, cualquier
diferencia en los resultados se atribuye a la recuperación documental.

Todos los comandos se ejecutan desde la raíz del proyecto, con Ollama abierto y el
entorno activado.

1. Instalar prerrequisitos
   ```powershell
   ollama pull qwen3.5:9b
   ollama pull embeddinggemma:300m
   pip install -r requirements.txt
   ```

2. Construir el índice vectorial
   ```powershell
   python src/embeddings.py --construir
   ```

   Si no hay información en data/proccessed, hacer lo siguiente:

   ```powershell
   python scripts/sources_filler.py
   python scripts/download_data.py
   python scripts/extract_text.py
   ```

3. Verificar la recuperación (sin LLM)
   ```powershell
   python src/embeddings.py --pregunta "¿Qué se propone la UTB para mejorar la calidad de la formación que ofrece?"
   ```
   Devuelve los 5 fragmentos más similares con su procedencia (documento, página,
   sección, URL). Si estos fragmentos no tienen relación con la pregunta, el problema
   está en el índice y no en el generador.

4. Hacer preguntas al chatbot RAG
   ```powershell
   python src/rag/rag.py                                   # chat por consola
   python src/rag/rag.py --pregunta "¿Qué se propone la UTB para mejorar la calidad de la formación que ofrece?" --json   # realizar una sola pregunta especifica
   ```

   Cada respuesta incluye las fuentes citadas y la latencia. Si el contexto recuperado
   no alcanza, el bot responde que no cuenta con esa información en las fuentes
   oficiales. 
   Opciones: 
   - `--k`: fragmentos a recuperar, 5 por defecto
   - `--umbral`: similitud mínima del mejor fragmento; por debajo de ella, el bot se abstiene sin
   llamar al LLM; desactivado por defecto.

5. Correr el conjunto de preguntas con el RAG
   Prueba rápida con pocas preguntas, en una carpeta aparte:

   ```powershell
   python src/rag/run_rag_exp.py --limit 5 --nombre rag_prueba
   ```

   Prueba completa:

   ```powershell
   python src/rag/run_rag_exp.py
   ```

   Lee `data/preguntas.csv` y guarda en `experiments/rag/`:

   - `respuestas.csv`: respuesta, latencia, abstención automática, similitud, fuentes
   citadas y `recall_auto`.
   - `recuperacion.jsonl`: fragmentos recuperados por pregunta (para el análisis de errores).
   - `run_info.json`: modelo, parámetros, prompt e información del índice de la corrida.

   Si se interrumpe, al ejecutar de nuevo retoma las preguntas pendientes. 
   Se pueden probar diferentes configuración, por ejemplo otros umbrales, para esto haz uso 
   de otro nombre para no mezclar corridas:

   ```powershell
   python src/rag/run_rag_exp.py --umbral 0.55 --nombre rag_u055
   ```

6. Etiquetar manualmente, abrir `experiments/rag/respuestas.csv` y llenar:
   - `etiqueta`: `correcta`, `parcial`, `incorrecta`, `alucinacion` o `abstencion`
   (las mismas opciones de la línea base).
   - `fidelidad`: `si` o `no`, solo en las respuestas donde el sistema no se abstuvo
   (¿la respuesta está respaldada por los fragmentos recuperados?).

7. Calcular métricas y comparar con la línea base
   ```powershell
   python src/rag/metricas_rag.py
   ```

### Estructura de resultados

```text
experiments/
├── baseline/          # línea base: respuestas.csv, metricas.json, run_info.json
├── rag/               # RAG: respuestas.csv, recuperacion.jsonl, metricas.json, run_info.json
└── comparacion_rag_vs_baseline.json
```
