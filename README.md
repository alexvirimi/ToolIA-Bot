# ToolIA-Bot

“ToolIA-Bot” será un chatbot universitario diseñado para centralizar y facilitar el acceso a la 
información institucional de la Universidad Tecnológica de Bolívar (UTB). Permitirá que 
estudiantes, aspirantes, docentes y administrativos realicen preguntas en lenguaje natural 
sobre reglamentos, manual de convivencia, calendario académico, procesos administrativos, 
requisitos, servicios y demás información publicada en la página web.

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
   .venv\Scripts\activate # Windows (Mac/Linux: source .venv/bin/activate)
   ```
4. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
5. Ejecutar la línea base (con Ollama abierto):
   ```bash
   python src/run_experiment.py
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

