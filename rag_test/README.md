# Experimento de mejora del RAG de ToolIA-Bot

La primera apuesta es recuperar mejor evidencia y aprovecharla mejor con el
mismo `qwen3.5:9b`. El RAG histórico obtuvo 45,8 % de exactitud estricta,
72,9 % contando parciales, 77,5 % de fidelidad y se abstuvo en 8 de las 48
preguntas con información disponible. El [análisis de errores](../docs/analisis_rag.md)
señala dos causas: fragmentos de trámites similares desplazan los correctos, y el
generador omite condiciones o mezcla reglas de documentos distintos.

- **`control`**: ejecuta la clase y el prompt actuales con búsqueda vectorial.
- **`prompt`**: conserva la búsqueda vectorial y cambia el prompt. Pide cubrir
  cada parte, preservar condiciones y excepciones, distinguir trámites y versiones
  y citar junto a cada afirmación respaldada.
- **`hibrido`**: usa ese mismo prompt. Combina los 20 primeros resultados
  vectoriales con hasta 20 coincidencias TF-IDF sobre título, sección y texto.
  La fusión por rangos (RRF) da prioridad a fragmentos altos en ambas listas sin
  comparar escalas de puntaje distintas. Entrega cinco fragmentos al generador.

Las tres variantes usan el mismo corpus, fragmentación, índice, generador y
parámetros de generación. Los artefactos nuevos van a `rag_test/indice/`,
`rag_test/corridas/` y `rag_test/evaluaciones/`; las salidas históricas quedan intactas.

## Ejecutar con Ollama

Desde la raíz del repositorio, con Python 3.14 y Ollama en ejecución:

```powershell
python -m pip install -r requirements.txt
ollama pull qwen3.5:9b
ollama pull embeddinggemma:300m
python -m rag_test.ejecutar preparar
```

Para el último comando necesitas el corpus del equipo en `data/raw/` y
`data/processed/`. Esos archivos no se versionan. Si no los tienes, pídele al
equipo la copia usada para el RAG actual, o sigue el flujo de descarga y
extracción del [README principal](../README.md). Usa la misma copia para las tres
corridas. La huella del índice queda en `run_info.json`.

Primero se puede verificar el flujo con `--limit 5` y nombres como `control-5`,
`prompt-5` e `hibrido-5`. Para medir, ejecuta las 57 preguntas en la misma máquina:

```powershell
python -m rag_test.ejecutar corrida control --nombre control-57
python -m rag_test.ejecutar corrida prompt --nombre prompt-57
python -m rag_test.ejecutar corrida hibrido --nombre hibrido-57
```

Cada corrida usa una carpeta nueva. Si se interrumpe, conserva el registro
parcial en `recuperacion.jsonl`; repítela con otro nombre. Solo las corridas
completas publican `respuestas.csv`.

## Etiquetar y comparar

1. En cada `rag_test/corridas/<nombre>/respuestas.csv`, completa `etiqueta`,
   `fidelidad` (`si`/`no` solo si no se abstuvo) y `observaciones` siguiendo la
   [rúbrica](../docs/rubrica_etiquetado.md). Para una abstención con información
   disponible marca `abstencion_fallo`. Consulta `recuperacion.jsonl` para ver
   los fragmentos numerados y comprobar qué respaldan las citas. Conserva el
   orden de las preguntas y guarda el CSV en UTF-8.
2. Genera el informe; este paso no necesita Ollama:

   ```powershell
   python -m rag_test.evaluar control-57 prompt-57 hibrido-57 --nombre comparacion-57
   ```

3. Abre `rag_test/evaluaciones/comparacion-57/comparacion.json`. Mira primero
   la exactitud estricta, la fidelidad y las abstenciones por fallo. Comprueba
   cómo cambian también la alucinación, la abstención adecuada y la latencia.
   `prompt` frente a `control` mide el cambio de instrucciones; `hibrido` frente
   a `prompt` permite ver el efecto adicional de cambiar la recuperación.

**HitFuente@5** comprueba si las URLs de referencia aparecen entre los cinco
fragmentos, con conteo e intervalo de confianza. No verifica si el fragmento
trae el artículo, el párrafo o cada dato necesario. Tampoco captura alias de
URLs distintos de los guardados en el índice. Para medir recall de evidencia
se requiere revisión manual. El control nuevo es la referencia directa del
experimento: el histórico puede venir de otro corpus, máquina o etiquetado.

Las 57 preguntas sirven para comparar contra el RAG actual. Como el diseño
partió de sus errores históricos, conviene confirmar cualquier mejora con
preguntas nuevas antes de cambiar el sistema principal.
