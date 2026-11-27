# Análisis de la línea base del asistente UTB

Este documento se construye a partir de `experiments/rag/respuestas.csv` y `experiments/rag/metricas.csv`, evaluado sobre las mismas 57 preguntas que la línea base.

Los casos no sustituyen el análisis cuantitativo de las 57 preguntas, sino que muestran los patrones dominantes. De las 26 respuestas no correctas de `respuestas.csv` (13 parciales, 8 abstenciones por fallo y 5 incorrectas), la tabla incluye 20, las 6 restantes repiten un patrón ya representado: ID 7 ≈ 6; ID 14 ≈ 10; ID 19, 27 y 29 ≈ 2; ID 45 omite que ambos programas deben ser de la misma modalidad.

## 1. Casos representativos de error

Columna **Capa**: 
- **Recuperación**: La información necesaria no está en ninguno de los 5 fragmentos recuperados.
- **Generación**: La información sí estaba en el top 5 y el modelo respondió mal o incompleto.
- **Mixta**: Ambas contribuyeron. La presencia de la información se verificó por contenido (sección 2.5), no solo por el nombre del documento.


| Caso | ID | Pregunta | Respuesta de referencia | Respuesta del RAG | Etiqueta | Capa | Análisis del error e hipótesis de causa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | ¿Cuál es la calificación mínima aprobatoria para un curso de pregrado en la UTB? | 3,0 para cursos de pregrado y 3,5 para la práctica profesional (Reglamento, Art. 51). | Dice que el contexto no especifica la nota general; cita los 3,5 del Consultorio Jurídico y del ingreso Coterminal. | Abstención por fallo | Recuperación | Recall@5 = no (similitud 0,648). Se recuperaron reglamentos del Consultorio Jurídico y una resolución de trabajos de grado, no el Reglamento Estudiantil. Hipótesis: la consulta coincide léxicamente con "nota mínima" de documentos específicos. La abstención es coherente con el contexto; el problema está antes de la generación, está en la recuperación. |
| 2 | 2 | ¿Qué PPA debe mantener un estudiante de pregrado y qué pasa si al finalizar un periodo no lo logra? | PPA mínimo de 3,20; si queda por debajo, pasa a Prueba Académica Parcial el periodo siguiente (Art. 68). | Acierta 3,20 y Prueba Académica Parcial, pero omite que aplica cuando los créditos matriculados acumulados superan los del primer nivel. | Parcial | Generación | Recall@5 = sí. El fragmento correcto estaba en el top 5 y el modelo omitió una condición de aplicación. Mismo patrón en ID 27 (créditos acumulados), ID 29 (continuidad inmediata y autorización de la dirección del programa) e ID 19 (condiciones de continuidad). Hipótesis: el prompt no pide enumerar condiciones y excepciones. |
| 3 | 6 | ¿Qué descuento recibe un Estudiante de Honor para un curso de inglés por extensión y cuál es su vigencia? | 100 % de descuento; vigencia de tres años; intransferible y no canjeable (Res. No. 2, Art. 1). | Responde "100 % o 50 %" y tres años de vigencia. | Parcial | Recuperación | Recall@5 = no; fidelidad = no. Solo se recuperó la página web resumen de estímulos, que lista ambos porcentajes juntos. La Resolución No. 2, que los separa por distinción, nunca se recuperó. El mismo caso ocurre con el Estudiante Meritorio (ID 7, 50 %). |
| 4 | 8 | ¿Cuál es el estímulo por dominio de inglés B2 y quién designa los cupos? | Descuento del 50 % en la matrícula del siguiente semestre; la Vicerrectoría Administrativa designa los cupos. | Da el 50 % y declara que el contexto no menciona quién designa los cupos. | Parcial | Recuperación | Recall@5 = no. La web trae el descuento pero no la Vicerrectoría. El RAG reconoce el vacío en lugar de inventar (comportamiento deseable), pero la respuesta queda incompleta por la fuente ausente. |
| 5 | 9 | ¿Cuáles son los requisitos de inscripción para el estímulo por dominio del inglés B2? | Cuatro requisitos: sin cursos cancelados o reprobados ni Prueba Académica; sin sanciones; clasificación Saber 11 inglés 1–3 (A1/A2); certificar B2 al inscribirse. | Mezcla el plazo de cinco periodos, el costo del examen y requisitos de grado (Ruta de Autonomía, paz y salvo) como si fueran de inscripción; omite la clasificación Saber 11. | Incorrecta | Generación | Recall@5 por documento = no (Res. No. 2 ausente), pero por contenido = sí: la página de estímulos, en el puesto 3, trae "clasificación Saber 11: inglés 1, 2 o 3 (A1/A2)" y el modelo la omitió. Fidelidad = no. Contaminación de contexto: hay varios fragmentos sobre B2 (estímulo y requisito de grado) y el modelo los fusiona. |
| 6 | 10 | ¿Cuántas veces puede un estudiante obtener el estímulo por alcanzar el nivel B2? | Solo una vez por estudiante (Res. No. 2, Art. 2, Par. 1). | Dice que el contexto no especifica cuántas veces. | Abstención por fallo | Recuperación | Recall@5 = no (similitud 0,590). El parágrafo no se recuperó. La línea base también se abstuvo en esta pregunta, por lo que no hay mejora. |
| 7 | 12 | ¿Cuáles son los criterios de selección de la Beca a la Excelencia y Desempeño Integral? | PPA superior a 4,0; actividades extracurriculares específicas; logros en instancias externas. | Menciona "buen rendimiento", "gusto por liderar procesos" y participación extracurricular. | Parcial | Recuperación | Recall@5 = no; fidelidad = sí. La respuesta es fiel a la página web resumida, pero omite el PPA > 4,0 y los logros externos, que solo están en la Res. No. 2. Muestra que alta fidelidad no implica respuesta completa si la fuente correcta no se recupera. |
| 8 | 13 | ¿Cómo se evalúa la Beca a la Excelencia y Desempeño Integral y cuándo se notifica? | Presentación ante el Consejo/Comité Rectoral, rúbrica de un comité de la Vicerrectoría Académica y notificación antes del siguiente semestre. | Dice que no hay información específica y aclara que unas fechas corresponden a otra beca. | Abstención por fallo | Recuperación | Recall@5 = no (similitud 0,539). Se recuperaron cinco fuentes de otras becas (Surtigas, SPEC LNG, Legacy, entre otras) por coincidencia del término "beca". Rasgo positivo: no mezcló las fechas de otra beca. |
| 9 | 15 | ¿Qué unidad difunde y procesa las aplicaciones de la Beca a la Excelencia? | Ecosistema Universitario (Res. No. 2, Art. 3, Par. 2). | Dice que no existe información en el contexto y cita las cinco fuentes recuperadas. | Abstención por fallo | Recuperación | Recall@5 = no; similitud 0,482, la más baja entre las preguntas con respuesta. Además, citar cinco fuentes para sostener que "no hay información" no aporta trazabilidad: la cita debería omitirse en abstenciones. |
| 10 | 16 | ¿Son acumulables los beneficios de la política de estímulos y becas con otros descuentos? | No; se aplica únicamente el beneficio de mayor valor o el más favorable. | Dice que no son acumulables y agrega restricciones sobre ayudas de terceros y créditos condonables. | Parcial | Mixta | Recall@5 = no; fidelidad = no. Generaliza a toda la política restricciones propias de becas específicas (Legacy, PATH) y omite la regla del mayor valor. La línea base también omitió esa regla. |
| 11 | 17 | ¿Qué estímulos existen para estudiantes con puntajes sobresalientes en Saber Pro? | Art. 4 de la Res. No. 05 de 2023: puestos 1–10, 11–20 y mejores puntajes UTB; Planeación verifica y notifica. | Combina la Res. No. 1 de 2025 (40 puntos sobre la media) con la Res. No. 05 de 2023; omite los puestos 11–20. | Parcial | Generación | Recall@5 por documento = no, pero por contenido = sí (la Res. 05/2023 p.2, en el puesto 5, trae "puestos 11 y 20"); el modelo tenía el dato y lo omitió. Latencia 10,05 s. Mezcla disposiciones de resoluciones de años distintos sin indicar vigencia (riesgo de "información desactualizada"). La cita muestra "Microsoft Word - Propuesta de Sello Institucional…" (metadato del PDF) en lugar del nombre del documento. |
| 12 | 18 | ¿Qué oficina verifica los puntajes Saber Pro y notifica a los beneficiarios? | Oficina de Planeación y Gestión de la Calidad (Res. No. 2, Art. 4, Par.). | Dice que el contexto no identifica la oficina. | Abstención por fallo | Recuperación | Recall@5 = no. Se recuperaron la Res. No. 05 de 2023 y otros documentos, pero no el parágrafo de la Res. No. 2 donde está el dato. |
| 13 | 23 | ¿Es requisito demostrar nivel B2 de inglés para graduarse de un pregrado presencial? | Sí, para quienes iniciaron desde el 1 de enero de 2024 (Reglamento, Art. 78, Par. 2). | Responde sí, pero añade un plazo de cinco periodos y restricciones de inscripción. | Incorrecta | Generación | Recall@5 por documento = no (Art. 78 no recuperado), pero por contenido = sí: el Newsletter p.1, en el puesto 1, indica el requisito de grado B2 desde 2024. Fidelidad = no. El núcleo ("sí") es correcto, pero se le atribuyen al grado condiciones del estímulo. Cambia el error frente a la línea base (que lo negaba) a uno de mezcla de fuentes. Es la única pregunta de la categoría "inglés" (n = 1), así que su 0 % es anecdótico. |
| 14 | 30 | ¿Cuándo un estudiante pierde su calidad por bajo rendimiento académico? | Cuando, iniciando en Prueba Académica Total, no logra PPP ≥ 3,20 y queda con PPA < 3,20 (Arts. 68 y 69). | Indica que basta un PPA < 3,20 con créditos acumulados mayores al primer nivel. | Incorrecta | Generación | Recall@5 = sí; fidelidad = no. Los fragmentos correctos estaban presentes; el modelo fundió la condición del Art. 68 (Prueba Parcial) con la exclusión del Art. 69, omitiendo el paso por Prueba Total. Error de razonamiento sobre reglas condicionales encadenadas. |
| 15 | 40 | ¿Quién no puede solicitar reingreso a la UTB? | Excluidos por bajo rendimiento, expulsados y estudiantes en Recuperación Académica (Art. 28). | Acierta los dos primeros y añade reprobar o cancelar cursos, haber estado en Prueba Académica y tener sanciones. | Incorrecta | Mixta | Recall@5 = no; fidelidad = no. Se recuperaron páginas web de reingreso, pero se coló la página de estímulos y sus restricciones de distinciones se presentaron como restricciones de reingreso. |
| 16 | 43 | ¿Un estudiante sancionado puede recibir distinciones académicas? | No cumple los requisitos de varias distinciones (Arts. 83, 84 y 87); los Arts. 85 y 86 no lo exigen. | Dice que no se puede determinar con la información dada. | Abstención por fallo | Recuperación | Recall@5 = no. Los Arts. 81–88 del Reglamento no se recuperaron; sí llegaron el Consultorio Jurídico y la página de estímulos. La línea base respondió "no" con una condición inventada; el RAG prefiere abstenerse, más seguro pero poco útil. |
| 17 | 48 | ¿Cuáles son los requisitos específicos de la Beca Puerto Bahía? | Cinco requisitos (colegio de origen, edad 16–20, estudiante nuevo, Saber 11 ≥ 280, sin otra beca). | Enumera los requisitos correctos pero indica que el video se exige a todos. | Incorrecta | Generación | Recall@5 = sí; fidelidad = no; latencia 9,1 s. La fuente pide el video solo a los seis preseleccionados. Los cinco requisitos están bien; el error es una condición añadida. Conviene definir por escrito si "información añadida errónea" cuenta como incorrecta y la omisión como parcial. |
| 18 | 49 | ¿Cuál es el monto o cobertura del Crédito ICETEX para pregrado de la UTB? | ICETEX ofrece hasta el 100 % de la carrera y existen planes con porcentajes menores. | Dice que el contexto solo cubre diplomados y posgrado, no pregrado. | Abstención por fallo | Recuperación | Recall@5 = no. La fuente de referencia es externa (web.icetex.gov.co) y la propia fila indica "sin cobertura UTB específica verificada". Verificar que esa página esté en el corpus; si no, la pregunta debería reclasificarse como parcial o sin respuesta. La línea base inventó rangos; el RAG no. |
| 19 | 53 | ¿Qué estudiantes recibieron la distinción de Estudiante de Honor en 2025? | 22 estudiantes del primer periodo de 2025 (Informe de Gestión 2025, p. 37); no hay listado del segundo periodo. | Lista 19 de los 22; omite a Vera Reyes, García Maza y Nadjar Gaviria. | Parcial | Generación | Recall@5 = sí (Informe de Gestión p.37 en el puesto 1); fidelidad = sí; latencia 11,8 s (la máxima). Omisión al reproducir una lista larga. Hipótesis a verificar: que el chunk del PDF cortara parte de la tabla o que el modelo omitiera filas; revisar el texto del chunk recuperado. |
| 20 | 39 | ¿Cuáles son los tipos de admisión para programas de pregrado y posgrado? | Cinco tipos: primera vez, reinicio, reingreso, transferencia externa e interna (Art. 25). | Lista primera vez (pre y posgrado) y transferencia externa. | Parcial | Recuperación | Recall@5 = no. El Art. 25 no se recuperó, las páginas web por tipo de admisión dieron una respuesta parcial pero fiel. |

## 2. Análisis de las métricas del RAG

Las 57 preguntas se dividen igual que en la línea base: 47 con información completa, 1 parcial y 9 sin respuesta en el corpus. Son 48 preguntas evaluables para exactitud. No hubo fallos técnicos: la columna error está vacía en las 57 filas, mientras la línea base tuvo un HTTP 500 en el ID 29.

### 2.1. Exactitud

- **Exactitud estricta:** 45,8 % (22/48), IC 95 % de 32,6 % a 59,7 %.
- **Exactitud incluyendo parciales:** 72,9 % (35/48). 

Frente a la línea base (2,1 % estricta y 14,6 % con parciales), el RAG mejora 43,7 y 58,3 puntos respectivamente.
Los intervalos de confianza no se solapan (línea base 0,4 %–10,9 %), por lo que la mejora es estadísticamente clara. Sin embargo, el umbral era ≥ 75 % y al menos 15 puntos sobre la línea base: la diferencia se cumple, pero el nivel absoluto no, ni en la versión estricta ni en la que cuenta parciales (72,9 %, hizo falta una pregunta: 36/48 = 75 %).

## 2.2. Alucinaciones y respuestas no respaldadas

La tasa de alucinación es 0.0% (0/57, IC 95 % de 0 % a 6,3 %), frente a 47,4 % (27/57) en la línea base.

No obstante, es importante la siguiente aclaración: De las nueve respuestas con fidelada = no (ID 6, 7, 9, 16, 23, 30, 35, 40 y 48), cinco son incorrectas, tres parciales y una correcta. 
Como proporción de las 57 preguntas son 15,8 %, apenas por encima del umbral de 15 %. Casi todas son contaminación o mala aplicación del contexto recuperado, no invención desde el conocimiento del modelo; por eso se dice que el RAG no "alucina" en el sentido de la línea base, pero sí presenta afirmaciones no respaldadas.

## 2.3. Abstenciones

| Indicador | RAG | Línea base |
| --- | --- | --- |
| Abstenciones totales | 17/57 (29,8 %) | 19/57 (33,3 %) |
| Abstención adecuada | 9/9 (100 %), IC 70,1 %–100 % | 9/9 (100 %) |
| Abstención por fallo | 8/48 (16,7 %), IC 8,7 %–29,6 % | 10/48 (20,8 %)|

La abstención adecuada es perfecta en ambos sistemas, por lo que no hay diferencia entre ellos. 
La abstención por fallo mejora solo de 10 a 8 casos, una diferencia dentro del ruido. Las ocho abstenciones por fallo tienen la información ausente del top 5 (verificado por contenido): el modelo se abstiene porque el contexto realmente no contiene el dato. Es decir, el problema no es un prompt demasiado conservador, es recuperación.

Además, `abstencion_auto` es "no" en las 57 filas: el mecanismo automático de abstención por similitud nunca se activó, y toda abstención la decidió el LLM. Un umbral de similitud tampoco serviría de forma directa: las abstenciones correctas tienen similitud de 0,48 a 0,63 y las abstenciones por fallo de 0,48 a 0,69, rangos que se solapan, y el umbral de 0,65 dejaría fuera 4 respuestas correctas.

### 2.4. Fidelidad a las fuentes
 
Fidelidad: 77,5 % (31/40), IC 95 % de 62,5 % a 87,7 %, por debajo del umbral de 80 %. 
El denominador es 40 porque la fidelidad no se evalúa en las 8 abstenciones por fallo. Con 32 de 40 se alcanzaría el 80 %, y el intervalo incluye el umbral. Las respuestas con `fidelidad = no` se concentran en la categoría de becas y en preguntas donde se recuperaron fragmentos de varias fuentes (ver sección 3).

### 2.5. Recall@5

El `recall_auto` contiene tres filas sin marcar, con un resultado de 55,6 % (25/45), y un IC de 41,2 %–69,1 %. Sin embargo, esta versión subestima algunos casos.
 
| Fuente de referencia | Preguntas | Por documento (con alias) | Por contenido |
| --- | --- | --- | --- |
| Res. No. 2 (política de becas y estímulos) | 13 | 0 | 3 |
| Reglamento Estudiantil | 29 | 23 | 25 |
| Otras fuentes (web, ICETEX, Informe de Gestión) | 6 | 5 | 5 |
 
La Resolución No. 2 no aparece en ninguna de las 57 listas de fuentes recuperadas. Sus 3 aciertos por contenido vienen de páginas web que reproducen parte de su texto. Sin las preguntas de la Res. No. 2, el Recall@5 sería 80,0 % por documento (28/35) y 85,7 % por contenido (30/35). Es un diagnóstico, no un reemplazo del resultado oficial.

### 2.6. Latencia
 
Latencia promedio 3,79 s (línea base 3,81 s), máxima 11,8 s (línea base 11,99 s). La recuperación toma en promedio 0,33 s (0,19 a 0,42 s), menos del 9 % del total, así que agregar RAG no encareció el tiempo de respuesta, el cuello de botella es la generación. 
Las respuestas más lentas son las largas y con muchos requisitos (ID 53, 17, 48 y 9, todas por encima de 8 s). El umbral de 10 s en promedio.


### 2.7. Exactitud por categoría
 
Los valores por categoría de `metricas.json` cuentan las respuestas parciales como aciertos (`exactitud_por_categoria_%`) y la exactitud global (45,8 %) es estricta. En términos estrictos, y con las mismas etiquetas, resulta:
 
| Categoría | Preguntas | Correctas | Estricta | Con parciales |
| --- | --- | --- | --- | --- |
| Matrícula | 7 | 6 | 85,7 % | 100 % |
| Distinciones | 5 | 3 | 60,0 % | 80,0 % |
| Admisiones | 5 | 3 | 60,0 % | 80,0 % |
| Calificaciones | 2 | 1 | 50,0 % | 50,0 % |
| Web becas | 2 | 1 | 50,0 % | 100 % |
| Estados académicos | 6 | 2 | 33,3 % | 83,3 % |
| Becas y financiación | 17 | 3 | 17,6 % | 52,9 % |
| Asistencia, general | 3 | 3 | 100 % | 100 % |
| Inglés | 1 | 0 | 0 % | 0 % |
 
La categoría con peor desempeño, con diferencia, es **becas y financiación**, y concentra 17 de las 48 preguntas (35 %).

## 3. ¿Falló la recuperación o la generación?
 
Cruce de la presencia del dato clave en el top 5 (por contenido) con la etiqueta de la respuesta, en las 48 preguntas evaluables:
 
| Etiqueta | Total | Información presente en el top 5 | Información ausente del top 5 |
| --- | --- | --- | --- |
| Correcta | 22 | 22 | 0 |
| Parcial | 13 | 7 | 6 |
| Incorrecta | 5 | 4 | 1 |
| Abstención por fallo | 8 | 0 | 8 |
| **Total** | **48** | **33** | **15** |
 
- Con la información presente, el modelo acierta el 67 % (22/33) y responde correcta o parcialmente el 88 % (29/33). Con la información ausente, no acierta ninguna (0/15) y solo 6 respuestas son parciales (40 %).
- De las 26 respuestas no correctas: 15 (58 %) fallan por recuperación y 11 (42 %) por generación. Con la medida por documento original parecía que la recuperación explicaba casi todo, pero al verificar por contenido, 5 casos más (ID 9, 17, 23, 45 y 53) resultan ser fallas de generación con la información ya presente.
- Las 11 fallas de generación son siete omisiones de condiciones o elementos (ID 2, 17, 19, 27, 29, 45 y 53, todas parciales) y cuatro errores de mezcla o razonamiento (ID 9 y 23, que mezclan requisitos del estímulo con los de inscripción o grado; ID 30, que encadena mal los Arts. 68 y 69; e ID 48, que generaliza el video a todos los postulantes).
- La fidelidad depende de la recuperación: Con la información presente, 28 de 33 respuestas son fieles (84,8 %); con la información ausente, 3 de 7 (42,9 %). Las abstenciones por fallo no entran en ese cálculo.

### 3.1. Causas de fondo en la recuperación
 
1. **La Res. No. 2 explica 10 de las 15 fallas de recuperación (67 %):** ID 6, 7, 8, 10, 12, 13, 14, 15, 16 y 18. Aparece 0 veces en las 57 recuperaciones; la explicación más probable es que no se indexó o que su extracción de texto falló. Hay que buscar fragmentos de ese PDF en la base vectorial. Por otro lado, con los ID 6 y 7, la página web de estímulos trae "100 % o 50 %" sin distinguir Honor de Meritorio, así que recuperar esa página no basta; hace falta la resolución.
2. **Cuatro fallas ocurren con el Reglamento sí indexado:** (ID 1, 39, 40 y 43: Arts. 51, 25, 28 y 81–88). Son fallas de ranking, la consulta recuperó documentos de dominio cercano (Consultorio Jurídico, páginas web de admisión o de estímulos) por coincidencia léxica. Son candidatas a búsqueda híbrida, reranker y chunking con prefijo de título y sección.
3. **Una falla es de cobertura del corpus (ID 49, ICETEX):** La fuente de referencia es externa y no está en el índice, la pregunta o su referencia deberían revisarse.
4. **Copias duplicadas:** Las dos versiones idénticas del Reglamento aparecen juntas en el mismo top 5 en 27 consultas y desperdician posiciones. Conviene conservar una sola.
5. **La página `apoyo-financiero_estimulos.html` aparece en 18 de las 57 recuperaciones** y, cuando aparece, solo 2 de 18 respuestas son correctas (11 %), frente a 20 de 30 cuando no aparece (67 %). Es un consecuencia de la ausencia de la Res. No. 2, la página con el mismo tema ocupa su lugar con información genérica.
6. **Citación defectuosa.** En ID 17 y 18 la cita muestra el título interno del PDF ("Microsoft Word - Propuesta de Sello Institucional…") en lugar del nombre del documento, y en ID 15 se citan cinco fuentes para sostener una abstención.


## 4. Comparación con la línea base y con los umbrales
 
### 4.1. Comportamiento general (57 preguntas)
 
| Clasificación | Línea base | RAG |
| --- | --- | --- |
| Correcta | 1 (1,8 %) | 22 (38,6 %) |
| Parcial | 6 (10,5 %) | 13 (22,8 %) |
| Alucinación | 27 (47,4 %) | 0 (0 %) |
| Incorrecta | 4 (7,0 %) | 5 (8,8 %) |
| Abstención por fallo | 10 (17,5 %) | 8 (14,0 %) |
| Abstención adecuada | 9 (15,8 %) | 9 (15,8 %) |

El RAG desplazó la mayor parte de las 27 alucinaciones de la línea base hacia respuestas correctas, incorrectas y parciales. El número de respuestas incorrectas no bajó (4 a 5), y la abstención por fallo mejoró poco (10 a 8).

### 4.2. Umbrales de éxito

| Métrica | Umbral | Resultado RAG | Cumple | Por qué se cumple o no se cumple |
| --- | --- | --- | --- | --- |
| Exactitud | ≥ 75 % y +15 pts sobre línea base | 45,8 % estricta (72,9 % con parciales); +43,7 pts | No | La condición relativa se cumple con holgura (+43,7 pts), pero el nivel absoluto no: para llegar a 75 % estricta harían falta 36 respuestas correctas y hay 22 (14 más). De las 26 respuestas no correctas, 15 tienen la información ausente del top 5 (10 por la Res. No. 2 que nunca se recuperó, 4 por mal ranking en el Reglamento y 1 por una fuente fuera del corpus) y 11 tienen la información presente pero el modelo omitió condiciones o mezcló requisitos. Contando las 13 parciales como aciertos se llega a 72,9 %, a una pregunta del umbral (36/48), pero la propuesta no declaró si los parciales cuentan como aciertos; conviene fijar el criterio por escrito y aplicarlo igual a la línea base y al RAG. |
| Fidelidad | ≥ 80 % | 77,5 % (31/40; IC 62,5–87,7 %) | No (el IC incluye 80 %) | Falta 1 respuesta fiel para llegar a 80 % (32/40), así que el resultado es indeciso más que claramente insuficiente. Las 9 respuestas no respaldadas se explican así: 4 con la información ausente del top 5 (ID 6, 7, 16 y 40: el modelo responde con una página web ambigua o generaliza) y 5 con la información presente (ID 9, 23, 30, 48 y 35: mezcla de requisitos de documentos distintos, encadenamiento erróneo de artículos, una condición añadida y una sigla, PPA, expandida de forma incorrecta). El denominador de 40 excluye las 8 abstenciones por fallo; cuando la recuperación falla, la fidelidad cae a 42,9 % (3/7) frente a 84,8 % (28/33) cuando la información está presente. |
| Alucinación | ≤ 15 % | 0 % por etiqueta; 15,8 % por fidelidad = no | Sí por etiqueta; en el límite por fidelidad | Se cumple porque ninguna respuesta se etiquetó como alucinación (0/57): los errores del RAG son de contenido recuperado mal aplicado, no de datos inventados. Con el criterio alterno (respuestas con fidelidad = no, 9/57) el resultado queda en 15,8 %, apenas sobre el umbral, por lo que la conclusión depende de la definición operativa y debe justificarse en el informe. |
| Abstención adecuada | ≥ 70 % | 100 % (9/9; IC 70,1–100 %) | Sí | El modelo se abstuvo en las 9 preguntas cuya respuesta no está en el corpus. Con n = 9 el límite inferior del IC es 70,1 %, justo el umbral. La línea base obtuvo el mismo 100 %, así que la métrica no distingue entre sistemas. El costo está en la otra dirección: 8 abstenciones por fallo (16,7 %) en preguntas que sí tenían respuesta, todas con la información ausente del top 5. |
| Latencia | ≤ 10 s | 3,79 s | Sí | La recuperación toma 0,33 s en promedio (menos del 9 % del total) y la generación domina el tiempo. El promedio queda muy por debajo del umbral; solo 2 respuestas superan los 10 s (ID 53 con 11,8 s e ID 17 con 10,05 s), ambas largas, y el umbral se definió sobre el promedio. |
| Recall@5 | ≥ 80 % | 55,6 % (41,2 %–69,1 %) | No | De las 48 preguntas, 15 no tienen el dato en el top 5: 10 corresponden a la Res. No. 2, que no aparece en ninguna de las 57 recuperaciones (probable falla de ingesta); 4 al Reglamento indexado, donde compiten documentos cercanos (Consultorio Jurídico, páginas web); y 1 a una fuente externa que no está en el corpus (ICETEX). Sin las preguntas de la Res. No. 2 el recall sería 80,0 % por documento y 85,7 % por contenido, es decir, la brecha se concentra en un solo documento. |

El RAG supera a la línea base en exactitud y en tasa de alucinación, pero cumple 3 de los 6 umbrales con el criterio actual. 
El criterio de éxito de la propuesta exige al menos 5 de 6, así que con este RAG el proyecto no alcanzaría el éxito declarado.


## 5. Consideraciones
 
- **Una sola corrida y 57 preguntas:** Los intervalos de confianza son amplios (por ejemplo, 32,6 %–59,7 % para la exactitud). Sería bueno repetir la evaluación 3 a 5 veces con semilla fijada y reportar media y desviación.
- **No reetiquetar para alcanzar umbrales:** Los umbrales se fijaron antes de experimentar; reportar los resultados con el criterio original y, si se cambia una definición, justificarlo y mostrar ambas versiones.
- **Preguntas con referencia débil:** El ID 49 (ICETEX) apoya su referencia en una fuente externa sin verificación UTB; el ID 43 tiene una referencia matizada. Revisar si siguen siendo adecuadas como preguntas con respuesta.
- **Datos de la fila 53:** La referencia incluye nombres y PPA de estudiantes publicados en el Informe de Gestión institucional. Aunque son datos públicos y oficiales, mencionar en el apartado de IA responsable que el asistente puede difundir datos personales tomados de fuentes públicas y decidir si se filtra ese tipo de consulta.
- **"Información desactualizada":** Esta categoría no aparece de forma natural en las 57 preguntas (aunque ID 17 insinúa un riesgo por mezcla de resoluciones de años distintos). Conviene la prueba simulada prevista en la propuesta: modificar una fuente en una copia de prueba y verificar que se detecte y refleje el cambio.
- **Evitar sobreajuste a las 57 preguntas:** Al corregir el pipeline mirando estos casos, los resultados posteriores quedarán inflados. Reservar un subconjunto nuevo (por ejemplo, las preguntas adicionales más difíciles) como prueba final.

## 6. Conclusiones

El RAG mejora de forma clara y estadísticamente distinguible a la línea base: la exactitud estricta pasa de 2,1 % a 45,8 %, desaparecen las alucinaciones por etiqueta (47,4 % a 0 %) y la latencia no cambia (3,79 s frente a 3,81 s). El sistema es especialmente fiable cuando la información está en el top 5: en esos casos acierta el 67 % de las veces (22/33) y responde correcta o parcialmente el 88 %.

Aun así, con el criterio actual el RAG no alcanza los umbrales de exactitud (45,8 %), fidelidad (77,5 %) ni Recall@5 (55,6 %), por lo que cumple 3 de los 6 y no llega al mínimo de 5 declarado. 
El cuello de botella principal es la recuperación: 15 de las 26 respuestas no correctas (58 %) tienen la información ausente del top 5, y 10 de ellas dependen de un solo documento, la Resolución No. 2, que no aparece en ninguna recuperación. La generación aporta una segunda familia de errores, casi tan grande (11 casos), centrada en omitir condiciones y en mezclar reglas o requisitos de documentos distintos.
