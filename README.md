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