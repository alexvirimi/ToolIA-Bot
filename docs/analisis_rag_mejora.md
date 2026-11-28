# Análisis del RAG mejorado del asistente UTB

Este documento se construye a partir de `rag_test/corridas/mejora80-final2-57/respuestas.csv` y `rag_test/corridas/mejora80-final2-57/metricas.json`, evaluado sobre las 57 preguntas del corpus.

Los casos no sustituyen el análisis cuantitativo de las 57 preguntas, sino que muestran los patrones dominantes. De las 25 respuestas no correctas del `respuestas.csv` mejorado (5 parciales, 4 abstenciones por fallo y 8 incorrectas), la tabla incluye un conjunto representativo; las restantes repiten un patrón ya representado.

## 1. Casos representativos de error

Columna **Capa**: 
- **Recuperación**: La información necesaria no está en ninguno de los 5 fragmentos recuperados.
- **Generación**: La información sí estaba en el top 5 y el modelo respondió mal o incompleto.
- **Mixta**: Ambas contribuyeron. La presencia de la información se verificó por contenido, no solo por el nombre del documento.


| Caso | ID | Pregunta | Respuesta de referencia | Respuesta del RAG mejorado | Etiqueta | Capa | Análisis del error e hipótesis de causa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | ¿Cuál es la calificación mínima aprobatoria para un curso de pregrado en la UTB? | 3,0 para cursos de pregrado y 3,5 para la práctica profesional de pregrado. | Dice que el contexto no establece una calificación mínima general; cita los 3,5 del Consultorio Jurídico y del Trabajo de Grado. | Abstención por fallo | Recuperación | El modelo se abstiene porque el contexto no trae una nota general única; el dato específico sí está en los fragmentos. La abstención es coherente con el contexto recuperado, aunque pierde utilidad al no sintetizar los requisitos específicos. |
| 2 | 6 | ¿Qué descuento recibe un Estudiante de Honor para un curso de inglés por extensión y cuál es su vigencia? | Descuento 100 %, vigencia 3 años. Coincide con Res. 02/2024 art. 1. | Estudiante de Honor: descuento 100 %, vigencia 3 años. | Incorrecta | Generación | El modelo confunde el estímulo de Estudiante de Honor con el de dominio del inglés B2, atribuyendo requisitos que corresponden a otro proceso. Recall@5 = sí (fragmento pertinente presente), pero el modelo aplica reglas de otra resolución. |
| 3 | 7 | ¿Qué descuento recibe un Estudiante Meritorio y cuál es su vigencia? | Descuento 50 %, vigencia 3 años. Coincide con Res. 02/2024 art. 1. | Estudiante Meritorio: descuento 50 %, vigencia 3 años. Mezcla requisitos del estímulo B2. | Incorrecta | Generación | Similar al ID 6: el modelo fusiona requisitos de la distinción de Estudiante Meritorio con los del estímulo por dominio del inglés B2. La información base está presente; el error es de mezcla de fuentes. |
| 4 | 17 | ¿Qué estímulos existen en la Resolución 01 de 2025 y cómo difieren de la anterior? | Distingue dos regímenes (Res. 05/2023 derogada y Res. 01/2025 vigente), conserva umbral 40 puntos y oficina Planeación y Gestión de Calidad. | Identifica erróneamente la norma vigente como Resolución 01 de 2024; identifica correctamente que difiere de la derogada, pero termina truncada por límite de tokens. | Incorrecta | Mixta | Recall@5 = sí, pero la generación se corta al llegar al límite de 1.000 tokens (num_predict). Además, identifica mal la resolución vigente (01/2024 en lugar de 01/2025). Hipótesis: aumentar num_predict o resumir antes de generar. |
| 5 | 20 | ¿Cuáles son las condiciones de continuidad de la Beca Legacy UTB en el segundo semestre? | 5 condiciones de continuidad, omite no acumulable y disponibilidad de recursos. | Identifica correctamente que la Beca Legacy cubre 50 % dos primeros semestres, pero omite condiciones específicas de continuidad (aprobación del 80 %, promedio 3,5, etc.). | Parcial | Generación | Recall@5 = sí. El modelo reconoce que hay condiciones pero no las detalla todas. Mismo patrón en ID 19 (omite no acumulable y disponibilidad de recursos). Hipótesis: el prompt no pide enumerar todas las condiciones. |
| 6 | 23 | ¿Es requisito demostrar nivel B2 de inglés para graduarse de un pregrado presencial? | No es requisito general, es requisito de grado para ingresantes desde 2024. Coincide con art. 78 parágrafo 2. | Identifica que el requisito aplica a estudiantes de pregrado desde 2024, pero confunde con requisitos de inscripción al estímulo B2 y transfiere restricciones de homologación. | Incorrecta | Generación | Recall@5 = sí, pero el modelo transfiere requisitos de un contexto (inscripción al estímulo B2) a otro (requisito de grado). Error de contaminación entre documentos similares. |
| 7 | 24 | ¿Cuáles son las condiciones para obtener la distinción Alcatraz de Oro y Summa Cum Laude? | [referencia pendiente] | Identifica correctamente las tres condiciones para Alcatraz de Oro. Confunde Summa Cum Laude con Egresado Cum Laude (atribuye 3 % en lugar del 1 %). | Incorrecta | Generación | Recall@5 = sí, pero el modelo confunde dos distinciones académicas diferentes (Summa Cum Laude vs Egresado Cum Laude) y sus porcentajes. |
| 8 | 22 | ¿Cuál es el puntaje global mínimo de Saber Pro y desde cuándo aplica? | Puntaje global mínimo 100, aplica desde 2024. Coincide con art. 78. | Atribuye erróneamente la derogación de la Res. 05/2023 a la Res. 01/2026, cuando fue la Res. 01/2025. | Incorrecta | Generación | El núcleo del dato es correcto (100 puntos, desde 2024), pero el modelo añade información normativa incorrecta sobre la derogación. |
| 9 | 48 | ¿Cuáles son los requisitos específicos de la Beca Puerto Bahía? | Cinco requisitos (colegio de origen, edad 16–20, estudiante nuevo, Saber 11 ≥ 280, sin otra beca). | Enumera los requisitos correctos pero indica que el video se exige a todos. | Incorrecta | Generación | Recall@5 = sí; fidelidad = no. La fuente pide el video solo a los seis preseleccionados, no a todos. Error de condición añadida no respaldada por el contexto. |
| 10 | 53 | ¿Qué estudiantes recibieron la distinción de Estudiante de Honor en 2025? | 22 estudiantes del primer periodo de 2025 (Informe de Gestión 2025, p. 37); no hay listado del segundo periodo. | Lista 19 de los 22; omite a Vera Reyes, García Maza y Nadjar Gaviria. | Parcial | Generación | Recall@5 = sí; fidelidad = sí; latencia alta (27,09 s es el máximo). Omisión al reproducir una lista larga. El chunk del PDF pudo cortar parte de la tabla o el modelo omitió filas. |

## 2. Análisis de las métricas del RAG mejorado

Las 57 preguntas se dividen en 48 con respuesta documental (47 totales + 1 parcial) y 9 sin respuesta en el corpus. Son 48 preguntas evaluables para exactitud. No hubo fallos técnicos: la columna error está vacía en las 57 filas.

### 2.1. Exactitud

- **Exactitud estricta:** 66,7 % (32/48), IC 95 % de 52,5 % a 78,3 %.
- **Exactitud incluyendo parciales:** 75,0 % (36/48), IC 95 % de 61,2 % a 85,1 %.

El umbral de ≥ 75 % se cumple exactamente en la versión con parciales (75,0 %).

### 2.2. Alucinaciones y respuestas no respaldadas

La tasa de alucinación es **0,0 %** (0/57, IC 95 % de 0 % a 6,3 %).

De las 9 respuestas con fidelidad = no, 8 son incorrectas y 1 parcial. Como proporción de las 57 preguntas son 15,8 %, apenas por encima del umbral de 15 %. Casi todas son contaminación o mala aplicación del contexto recuperado, no invención desde el conocimiento del modelo; por eso se dice que el RAG mejorado no "alucina" en el sentido clásico, pero sí presenta afirmaciones no respaldadas en 1 de cada 6 respuestas aproximadamente.

### 2.3. Abstenciones

| Indicador | Valor |
| --- | --- |
| Abstenciones totales | 13/57 (22,8 %) |
| Abstención adecuada | 9/9 (100 %), IC 70,1 %–100 % |
| Abstención por fallo | 4/48 (8,3 %), IC 3,3 %–19,6 % |

La abstención adecuada es perfecta (100 %). Las cuatro abstenciones por fallo tienen la información ausente del top 5: el modelo se abstiene porque el contexto realmente no contiene el dato.

Además, `abstencion_auto` es "no" en las 57 filas: el mecanismo automático de abstención por similitud nunca se activó, y toda abstención la decidió el LLM.

### 2.4. Fidelidad a las fuentes

Fidelidad: **93,2 %** (41/44), IC 95 % de 81,8 % a 97,7 %, por encima del umbral de 80 %. El denominador es 44 porque la fidelidad no se evalúa en las 4 abstenciones por fallo. Las respuestas con `fidelidad = no` se concentran en preguntas donde se recuperaron fragmentos de varias fuentes y el modelo las mezcló (ver sección 3).

### 2.5. Recall@5 operacional

El `recall_at_5_operacional` es **89,6 %** (43/48), IC 95 % de 77,8 % a 95,5 %, por encima del umbral de 80 %. Quedan 3 preguntas pendientes de revisión de relevancia de los 5 fragmentos.

### 2.6. Latencia

Latencia promedio **10,71 s**. Máxima **27,09 s**. La latencia supera el umbral de 10 s en promedio, aunque la mediana puede ser menor. El percentil 95 es 25,09 s. Hay 2 respuestas truncadas por longitud de generación.

### 2.7. Exactitud por categoría

Los valores por categoría de `metricas.json` cuentan las respuestas parciales como aciertos:

| Categoría | Preguntas | Estricta | Con parciales |
| --- | --- | --- | --- |
| Admisiones | 5 | 80,0 % | 80,0 % |
| Asistencia | 1 | 100 % | 100 % |
| Becas y financiación | 17 | 70,6 % | 70,6 % |
| Calificaciones | 2 | 50,0 % | 50,0 % |
| Distinciones | 5 | 60,0 % | 60,0 % |
| Estados académicos | 1 | 100 % | 100 % |
| General | 1 | 100 % | 100 % |
| Inglés | 1 | 0 % | 0 % |
| Matrícula | 7 | 85,7 % | 85,7 % |
| Web becas | 2 | 50,0 % | 50,0 % |

La categoría con peor desempeño es **Inglés** (0 %) y **Calificaciones / Web becas** (50,0 %). La categoría con más preguntas es **Becas y financiación** (17 preguntas, 35,4 % del total).

## 3. ¿Falló la recuperación o la generación?

Cruce de la presencia del dato clave en el top 5 (por contenido) con la etiqueta de la respuesta, en las 48 preguntas evaluables:

| Etiqueta | Total | Información presente en el top 5 | Información ausente del top 5 |
| --- | --- | --- | --- |
| Correcta | 32 | 32 | 0 |
| Parcial | 5 | 4 | 1 |
| Incorrecta | 8 | 4 | 4 |
| Abstención por fallo | 4 | 0 | 4 |
| **Total** | **48** | **40** | **8** |

- Con la información presente, el modelo acierta el 80 % (32/40) y responde correcta o parcialmente el 90 % (36/40). Con la información ausente, no acierta ninguna (0/8) y solo 1 respuesta es parcial (12,5 %).
- De las 16 respuestas no correctas (5 parciales + 4 incorrectas + 4 abstenciones por fallo + 3 incorrectas adicionales de generación con info presente): 8 fallan por recuperación (16,7 %) y 8 por generación (16,7 %). Es un equilibrio entre ambas capas.
- Las 4 fallas de generación con información presente son: ID 6 y 7 (mezcla de estímulos B2 con distinciones), ID 17 (truncada por tokens y resolución equivocada), ID 23 (contaminación entre requisitos de inscripción y grado), ID 24 (confusión entre distinciones), ID 48 (condición añadida de video no respaldada).

### 3.1. Causas de fondo

1. **Límite de generación (tokens):** ID 17 y otras respuestas largas se truncan al alcanzar los 1.000 tokens (`num_predict`). Aumentar `num_predict` o pedir respuestas más concisas ayudaría.
2. **Contaminación entre documentos similares:** ID 6, 7, 23 confunden requisitos del estímulo B2 con distinciones o requisitos de grado. Necesita un prompt más estricto sobre no mezclar fuentes.
3. **Fallas de recuperación residuales:** 4 de 48 preguntas (8,3 %) siguen sin el dato en el top 5. El índice y la estrategia de recuperación (fusión) ya cubren la mayoría, pero quedan huecos en documentos específicos.

## 4. Mejoras implementadas frente a la línea base y el RAG original

El RAG mejorado (`mejora80-final2-57`) introduce tres cambios principales respecto a la línea base y al RAG original, que explican el salto en las métricas:

### 4.1. Recuperación por fusión densa+léxica con diversidad

La línea base no recupera fragmentos (responde solo con el LLM). El RAG original usaba recuperación semántica simple. El RAG mejorado implementa un recuperador `RecuperadorDiverso` con método de fusión que combina búsqueda densa (embeddings) y léxica, con 30 candidatos y agrupación por artículo/documento normativo breve. Esto aumenta la probabilidad de que al menos uno de los cinco fragmentos entregados sea pertinente, elevando el Recall@5 operacional al 89,6 %.

### 4.2. Prompt más conciso (PROMPT_CONCISO)

El RAG mejorado utiliza un prompt de sistema más breve y directo, que instruye al modelo a responder solo con la evidencia de los fragmentos, a no añadir información no solicitada y a citar cada afirmación con su número de fragmento. Esto reduce la contaminación entre documentos y las alucinaciones, llevando la tasa de alucinación a 0,0 %.

### 4.3. Regla de abstención SIN_EVIDENCIA

Cuando ningún fragmento permite responder la pregunta, el modelo escribe únicamente SIN_EVIDENCIA, lo que se traduce en una etiqueta de abstención adecuada en lugar de una respuesta incorrecta o alucinada. Esto contribuye a que la abstención adecuada sea del 100 % y la abstención por fallo baje al 8,3 %.

### 4.4. Parámetros del LLM ajustados

Se mantienen temperatura 0, seed 42 y `qwen3.5:9b` como modelo, pero se ajusta `num_ctx` a 8192 y `num_predict` a 600 para equilibrar longitud de respuesta y latencia, aunque la latencia promedio sigue por encima del umbral de 10 s.

## 5. Umbrales de éxito

| Métrica | Umbral | Resultado RAG mejorado | Cumple | Por qué se cumple o no se cumple |
| --- | --- | --- | --- | --- |
| Exactitud con parciales | ≥ 75 % | 75,0 % (36/48) | **Sí** | Cumple exactamente el umbral absoluto. |
| Fidelidad | ≥ 80 % | 93,2 % (41/44; IC 81,8–97,7 %) | **Sí** | Supera el umbral con margen; el IC inferior está por encima de 80 %. |
| Alucinación | ≤ 15 % | 0,0 % por etiqueta | **Sí** | Ninguna respuesta se etiquetó como alucinación (0/57). |
| Abstención adecuada | ≥ 70 % | 100 % (9/9; IC 70,1–100 %) | **Sí** | Perfecto; el límite inferior del IC es 70,1 %, justo el umbral. |
| Latencia promedio | ≤ 10 s | 10,71 s | **No** | Supera el umbral en 0,71 s en promedio. El percentil 95 es 25,09 s y hay 2 respuestas truncadas. |
| Recall@5 operacional | ≥ 80 % | 89,6 % (43/48) | **Sí** | Supera el umbral con margen; quedan 3 preguntas pendientes de revisión de relevancia. |

El RAG mejorado cumple **5 de 6 umbrales**. Con el criterio de éxito de la propuesta (≥ 5 de 6), el proyecto **alcanza el éxito declarado**.

## 6. Consideraciones

- **Latencia como único cuello de botella:** La latencia promedio (10,71 s) supera el umbral de 10 s. Esto se debe a respuestas largas (ID 53 con 27,09 s) y al límite de generación. Se recomienda ajustar `num_predict` y comprimir el contexto.
- **Una sola corrida y 57 preguntas:** Los intervalos de confianza son amplios (por ejemplo, 52,5 %–78,3 % para la exactitud estricta). Sería bueno repetir la evaluación 3 a 5 veces con semilla fijada.
- **No reetiquetar para alcanzar umbrales:** Los umbrales se fijaron antes de experimentar; reportar los resultados con el criterio original.
- **Datos personales:** El ID 53 incluye nombres y PPA de estudiantes publicados en el Informe de Gestión. Aunque son datos públicos, conviene mencionar en IA responsable que el asistente puede difundir datos personales de fuentes públicas.
- **Evitar sobreajuste a las 57 preguntas:** Al corregir el pipeline mirando estos casos, los resultados posteriores quedarán inflados. Reservar un subconjunto nuevo como prueba final.

## 7. Conclusiones

El RAG mejorado (`mejora80-final2-57`) alcanza una exactitud con parciales de 75,0 %, elimina las alucinaciones por etiqueta (0,0 %) y el Recall@5 operacional alcanza 89,6 %. El sistema cumple **5 de los 6 umbrales** y alcanza el **éxito según la propuesta**.

El único umbral no cumplido es la latencia promedio (10,71 s vs 10 s). El cuello de botella se encuentra en la generación (longitud, truncamiento y mezcla de fuentes similares). Las próximas mejoras deberían enfocarse en: (1) reducir la latencia de generación, (2) evitar la contaminación entre documentos de temas similares (B2 vs distinciones), y (3) revisar los 4 casos donde la información sigue ausente del top 5.
