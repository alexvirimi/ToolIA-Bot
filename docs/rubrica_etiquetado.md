# Rúbrica de etiquetado de respuestas - ToolIA-Bot

Este documento define cómo se etiquetarán las respuestas del asistente virtual ToolIA-Bot durante la evaluación experimental. Se redacta antes de conocer los resultados finales, tal como exige la propuesta del proyecto, para que las métricas estén definidas antes de experimentar.

Cada respuesta recibe una sola etiqueta: correcta, parcial, incorrecta, alucinacion o abstencion. Junto a la etiqueta se escribe una observación que la justifique.

## 1. Definición de etiquetas y ejemplos

### Correcta

La respuesta responde completa y correctamente a la pregunta usando solo información de las fuentes recuperadas o de los documentos institucionales. No inventa datos y cita la fuente (documento, página o sección) cuando es posible y pertinente. Por ejemplo:

| pregunta | respuesta | etiqueta | observación |
|----------|-----------|----------|-------------|
| ¿Cuál es el valor del crédito académico para pregrado en 2026? | El valor del crédito académico para programas de pregrado en 2026 es de $1.250.000 COP, según el Manual de Matrícula de la UTB, sección Finanzas. | correcta | Dato exacto, completo y con cita de la fuente institucional. |

### Parcial

La respuesta contiene información correcta pero incompleta. Omite un dato importante, responde solo parte de la pregunta o usa las fuentes de manera incompleta sin inventar información falsa. Por ejemplo

| pregunta | respuesta | etiqueta | observación |
|----------|-----------|----------|-------------|
| ¿Cuáles son los requisitos y documentos para solicitar la beca de excelencia académica? | Necesitas tener un promedio mínimo de 4.0 y estar inscrito en el semestre. | parcial | La información es correcta, pero omite los documentos requeridos y las fechas de convocatoria. |

### Incorrecta

La respuesta ofrece información falsa o contradictoria con las fuentes recuperadas, o no responde a lo que se preguntó. Por ejemplo:

| pregunta | respuesta | etiqueta | observación |
|----------|-----------|----------|-------------|
| ¿En qué sede de la UTB se imparte el programa de Medicina? | El programa de Medicina se dicta en la sede Centro de Cartagena. | incorrecta | Las fuentes no reportan un programa de Medicina en esa sede. El dato es falso respecto a la información institucional. |

### Alucinacion

La respuesta inventa hechos, cifras, fechas, documentos o fuentes que no aparecen en ninguna fuente recuperada ni en la base de conocimiento institucional. Incluye citar fuentes inexistentes. Por ejemplo:

| pregunta | respuesta | etiqueta | observación |
|----------|-----------|----------|-------------|
| ¿Cuál es el teléfono de la oficina de Bienestar Estudiantil? | Puedes comunicarte al 310 555 0199 de lunes a viernes de 8:00 a.m. a 5:00 p.m. | alucinacion | Ese número y horario no aparecen en ningún documento ni página oficial de la UTB. El dato fue inventado. |

### Abstencion

El sistema reconoce explícitamente que no cuenta con información suficiente en las fuentes recuperadas para responder, y se niega a inventar. Se espera esta etiqueta en las preguntas cuya respuesta no está publicada en las fuentes de la UTB. Por ejemplo:

| pregunta | respuesta | etiqueta | observación |
|----------|-----------|----------|-------------|
| ¿Cuál es el costo de la maestría en inteligencia artificial de la UTB? | No cuento con información publicada sobre el costo de la maestría en inteligencia artificial en las fuentes de la UTB, por lo que no puedo responder con certeza. Te recomiendo consultar la página de posgrados. | abstencion | Rechazo fundamentado sin inventar datos. Adecuado para preguntas sin respuesta en las fuentes. |

## 2. Resumen de decisión

| Situación | Etiqueta sugerida |
| ----------- | ------------------- |
| Responde completo, correcto y con fuente | correcta |
| Responde correcto pero incompleto u omite parte | parcial |
| Dato falso, contradictorio o no responde | incorrecta |
| Inventa datos, cifras, fuentes o fechas inexistentes | alucinacion |
| Dice que no tiene información y no responde | abstencion |

>[!important]
>Si una respuesta mezcla un dato verdadero con uno inventado, se etiqueta como alucinacion. Si omite información pero no inventa nada, es parcial.

## 3. Métricas asociadas

Estas etiquetas alimentan directamente las métricas del proyecto definidas en la sección 8 de la propuesta.

| Métrica | Umbral de éxito | Relación con etiquetas |
| --------- | ----------------- | ------------------------ |
| Exactitud de respuesta | 75 por ciento en RAG, y al menos 15 puntos porcentuales por encima de la línea base | correcta y parcial |
| Fidelidad a las fuentes | 80 por ciento de respuestas respaldadas | correcta y parcial respaldadas |
| Tasa de alucinacion | 15 por ciento | alucinacion |
| Tasa de abstencion | 70 por ciento de preguntas sin respuesta en fuentes | abstencion |
| Latencia | 10 segundos en promedio | tiempo de respuesta |
| Recall@5 | 80 por ciento | fragmentos relevantes en el top 5 |

El proyecto se considera exitoso si cumple al menos cinco de los seis umbrales y supera a la línea base en exactitud y tasa de alucinacion.

## 4. Proceso de etiquetado

1. Cada estudiante etiqueta por separado las respuestas de las 50 preguntas, tanto del sistema RAG como de la línea base. Completa las columnas etiqueta y observaciones.
2. Se comparan las etiquetas de ambos estudiantes.
3. Se revisan juntos los desacuerdos y se acuerda una etiqueta final por consenso. Si persiste el desacuerdo, interviene un tercer estudiante.
4. Las etiquetas finales se usan para calcular las métricas y validar los umbrales de éxito.
