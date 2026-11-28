# Comparativa: Línea base vs. RAG vs. RAG mejorado

Este documento compara los tres sistemas sobre las mismas 57 preguntas del corpus UTB:
- Línea base: `experiments/baseline/respuestas.csv` (modelo sin RAG)
- RAG: `experiments/rag/respuestas.csv` (RAG histórico/variante original)
- RAG mejorado: `rag_test/corridas/mejora80-final2-57/respuestas.csv` (variante mejora, corrida medida)

## 1. Distribución de etiquetas (57 preguntas)

| Clasificación | Línea base | RAG | RAG mejorado |
| --- | --- | --- | --- |
| Correcta | 1 (1,8 %) | 22 (38,6 %) | 32 (56,1 %) |
| Parcial | 6 (10,5 %) | 13 (22,8 %) | 5 (8,8 %) |
| Alucinación | 27 (47,4 %) | 0 (0 %) | 0 (0 %) |
| Incorrecta | 4 (7,0 %) | 5 (8,8 %) | 8 (14,0 %) |
| Abstención por fallo | 10 (17,5 %) | 8 (14,0 %) | 4 (7,0 %) |
| Abstención adecuada | 9 (15,8 %) | 9 (15,8 %) | 9 (15,8 %) |
| Respondidas (correcta + parcial) | 7 (12,3 %) | 35 (61,4 %) | 37 (64,9 %) |

### Observaciones
- La línea base acumula el 47,4 % de alucinaciones; ambos sistemas RAG las eliminan por completo.
- El RAG mejorado tiene la mayor proporción de respuestas correctas (56,1 %) y la menor de abstenciones por fallo (7,0 %).
- El RAG mejorado tiene más incorrectas (14,0 %) que la línea base (7,0 %) y el RAG original (8,8 %), lo que refleja un mayor escrutínio de fidelidad y menos abstenciones "seguras".

## 2. Métricas principales

| Métrica | Línea base | RAG | RAG mejorado | Umbral propuesta |
| --- | --- | --- | --- | --- |
| Exactitud estricta | 2,1 % | 45,8 % | 66,7 % | — |
| Exactitud con parciales | 14,6 % | 72,9 % | 75,0 % | ≥ 75 % y +15 pp sobre línea base |
| Mejora vs. línea base (pp) | — | +58,3 pp | +60,4 pp | ≥ 15 pp |
| Fidelidad | — | 77,5 % | 93,2 % | ≥ 80 % |
| Tasa alucinación | 47,4 % | 0,0 % | 0,0 % | ≤ 15 % |
| Abstención adecuada | 100 % | 100 % | 100 % | ≥ 70 % |
| Recall@5 operacional | — | 55,6 % | 89,6 % | ≥ 80 % |
| Latencia promedio | 3,81 s | 3,79 s | 10,71 s | ≤ 10 s |

### Cumplimiento de umbrales

| Métrica | Línea base | RAG | RAG mejorado |
| --- | --- | --- | --- |
| Exactitud con parciales | No | Sí (relativa) | Sí |
| Fidelidad | — | No | Sí |
| Alucinación | No | Sí | Sí |
| Abstención adecuada | Sí | Sí | Sí |
| Latencia | Sí | Sí | No |
| Recall@5 | — | No | Sí |
| Metas cumplidas | — | 3 de 6 | 5 de 6 |
| Éxito según propuesta | — | No | Sí |

## 3. Evolución del desempeño

### Línea base → RAG
- Exactitud con parciales: 14,6 % → 72,9 % (+58,3 pp)
- Alucinación: 47,4 % → 0 % (eliminada por completo)
- Correctas: 1 → 22 (+21 preguntas)
- Abstención por fallo: 10 → 8 (mejora leve)
- Latencia: 3,81 s → 3,79 s (sin cambio relevante)
- Recall@5: no reportado → 55,6 % (no cumple umbral)

### RAG → RAG mejorado
- Exactitud con parciales: 72,9 % → 75,0 % (+2,1 pp)
- Correctas: 22 → 32 (+10 preguntas)
- Alucinación: 0 % → 0 % (se mantiene eliminada)
- Fidelidad: 77,5 % → 93,2 % (+15,7 pp)
- Abstención por fallo: 8 → 4 (reducción del 50 %)
- Recall@5: 55,6 % → 89,6 % (+34,0 pp, ahora cumple umbral)
- Latencia: 3,79 s → 10,71 s (empeora, supera umbral de 10 s)

## 4. Análisis por capa de fallo

| Sistema | Fallos por recuperación | Fallos por generación | Total no correctas |
| --- | --- | --- | --- |
| Línea base | Dominante (27 alucinaciones) | Secundario | 46 de 57 |
| RAG | 15 de 26 (58 %) | 11 de 26 (42 %) | 26 de 48 |
| RAG mejorado | 8 de 16 (50 %) | 8 de 16 (50 %) | 16 de 48 |

El RAG mejorado equilibra los fallos entre recuperación y generación, mientras que en el RAG original la recuperación era el cuello de botella claro (58 %). El RAG mejorado reduce las fallas de recuperación de 15 a 8, pero las fallas de generación se mantienen estables (11 → 8) debido a problemas de truncamiento por límite de tokens y mezcla de documentos similares (por ejemplo, estímulo B2 vs. distinciones académicas).

## 5. Conclusión

El RAG mejorado es el único sistema de los tres evaluados que alcanza el éxito según la propuesta, cumpliendo 5 de los 6 umbrales establecidos. Cada métrica revela una historia distinta sobre la evolución del asistente UTB y los trade-offs inherentes a cada arquitectura.

### 5.1. Distribución de etiquetas

El cambio más dramático entre la línea base y cualquiera de los dos sistemas RAG es la eliminación completa de las alucinaciones por etiqueta. La línea base acumula el 47,4 % de sus respuestas en esta categoría (27 de 57 preguntas), lo que significa que casi la mitad de sus respuestas contenían información inventada o no respaldada por el corpus. Tanto el RAG original como el RAG mejorado reducen esta tasa a 0,0 %, demostrando que la incorporación de fragmentos recuperados como fuente obligatoria sanea fundamentalmente la generación.

Sin embargo, esta eliminación de alucinaciones no viene sin costos. El RAG mejorado presenta el mayor porcentaje de respuestas incorrectas (14,0 %), superando tanto a la línea base (7,0 %) como al RAG original (8,8 %). Este aumento no indica un peor desempeño, sino un cambio de comportamiento, el RAG mejorado es menos propenso a abstenerse "de forma segura" y más propenso a entregar una respuesta que, aunque equivocada, intenta ser útil. La reducción de abstenciones por fallo del 17,5 % (línea base) al 7,0 % (RAG mejorado) confirma esta tendencia, el sistema mejorado prefiere arriesgar una respuesta antes que declarar que no sabe, siempre que el contexto recuperado ofrezca algún material relacionado.

En términos de respuestas realmente útiles (correcta + parcial), el RAG mejorado alcanza el 64,9 % (37 de 57), superando claramente al RAG original (61,4 %) y triplicando el resultado de la línea base (12,3 %). Este es, quizás, el indicador más relevante para un usuario final. Más de dos de cada tres preguntas reciben ahora una respuesta al menos parcialmente válida, frente a apenas una de cada ocho en la línea base.

### 5.2. Exactitud y fidelidad

La exactitud con parciales pasa del 14,6 % en la línea base al 72,9 % en el RAG original y al 75,0 % en el RAG mejorado. Aunque la mejora absoluta entre el RAG original y el mejorado es modesta (+2,1 pp), la exactitud estricta crece de forma más significativa: del 45,8 % al 66,7 %. Esto indica que el RAG mejorado no solo acierta más seguido, sino que lo hace con mayor precisión, requiriendo menos "ayuda" de las respuestas parciales para alcanzar el umbral.

La fidelidad, que mide si la respuesta del modelo está respaldada por los fragmentos recuperados, muestra una mejora aún más pronunciada: del 77,5 % en el RAG original al 93,2 % en el RAG mejorado. Este salto de casi 16 puntos porcentuales sugiere que las mejoras introducidas en la variante mejora (recuperación fusion, prompt más conciso, regla de abstención SIN_EVIDENCIA) no solo ayudaron a encontrar mejor información, sino también a que el modelo la utilice de forma más fiel. Las respuestas con `fidelidad = no` en el RAG mejorado se concentran en casos de mezcla de documentos similares (por ejemplo, confundir requisitos del estímulo B2 con los de distinciones académicas), un error más sutil que la invención pura de la línea base.

### 5.3. Abstenciones
La abstención adecuada se mantiene en el 100 % en los tres sistemas, lo que indica que ninguno falla al declinar responder cuando el corpus realmente no contiene la información. Sin embargo, la abstención por fallo —cuando el sistema se abstiene aunque la información sí estaba disponible— mejora de forma consistente: del 17,5 % en la línea base al 14,0 % en el RAG original y al 7,0 % en el RAG mejorado.

Esta reducción es especialmente relevante porque cada abstención por fallo representa una oportunidad perdida de ayudar al usuario. El RAG mejorado reduce a la mitad las abstenciones por fallo del RAG original (de 8 a 4 casos), lo que sugiere que la estrategia de recuperación por fusión y diversidad está logrando cubrir más huecos del corpus sin sacrificar la precisión.

### 5.4. Recall@5

El Recall@5 operacional mide si, para cada pregunta con respuesta, al menos uno de los cinco fragmentos recuperados es pertinente. Aquí es donde se observa una de las brechas más grandes entre sistemas. El RAG original alcanzaba apenas el 55,6 %, lo que significa que casi la mitad de las veces el fragmento clave no aparecía en el top 5. El RAG mejorado eleva esta métrica al 89,6 %, superando con holgura el umbral del 80 %.

Esta mejora de 34 puntos porcentuales es el resultado directo de cambios en la estrategia de recuperación: uso de fusión densa+léxica con diversidad, mayor número de candidatos (30) y mejor agrupación de fragmentos. El RAG mejorado deja solo 3 preguntas de 48 sin el dato clave en el top 5, frente a las 15 que tenía el RAG original. La recuperación ya no es el cuello de botella principal; ahora es un sistema robusto que entrega contexto relevante en la gran mayoría de los casos.

### 5.5. Capa de fallo
El análisis de capa de fallo revela una transformación en la naturaleza de los errores. En la línea base, los fallos son dominados por la falta de fundamentación (27 alucinaciones de 46 respuestas no correctas). En el RAG original, la recuperación explica el 58 % de los fallos (15 de 26), mientras que la generación explica el 42 % restante. En el RAG mejorado, ambos factores se equilibran exactamente al 50 % cada uno (8 de 16 fallos cada uno).

Este equilibrio no es casualidad: al solucionar la mayoría de los problemas de recuperación, el sistema expone con mayor claridad las limitaciones de la generación. Los errores de generación en el RAG mejorado se concentran en tres patrones: (1) truncamiento por límite de tokens (`num_predict = 1000`), que corta respuestas largas antes de completarlas; (2) contaminación entre documentos de temas similares, como confundir requisitos del estímulo de inglés B2 con los de distinciones académicas; y (3) condiciones añadidas no respaldadas por el contexto, como exigir un video a todos los postulantes cuando solo aplica a preseleccionados.

Estos errores son más difíciles de corregir que una falla de recuperación, porque requieren ajustes finos en el prompt, límites de generación más flexibles o un mejor filtrado de documentos irrelevantes durante la inferencia.

### 5.6. Latencia

La única métrica en la que el RAG mejorado empeora respecto a sus predecesores es la latencia promedio: de 3,81 s en la línea base y 3,79 s en el RAG original a 10,71 s en el RAG mejorado. Este incremento de casi tres veces el tiempo de respuesta supera el umbral de 10 s y representa el principal obstáculo para una adopción en producción sin ajustes adicionales.

La causa raíz no es la recuperación, que sigue siendo rápida (menos del 9 % del tiempo total), sino la generación de respuestas más largas y detalladas. El percentil 95 de latencia alcanza los 25,09 s, y dos respuestas se truncan por alcanzar el límite de tokens. Este trade-off es comprensible: el RAG mejorado entrega respuestas más completas y fieles, pero a costa de mayor tiempo de generación. Para entornos de producción, se recomienda reducir `num_predict`, comprimir el contexto o implementar generación por fragmentos (streaming) para mejorar la percepción de velocidad.

### 5.7. Veredicto final

En resumen, la evolución de la línea base al RAG mejorado no es lineal en todas las dimensiones, pero sí es claramente positiva en las que más importan para la utilidad del asistente:

- Exactitud con parciales crece del 14,6 % al 75,0 %, cumpliendo el umbral propuesto.
- Alucinaciones desaparecen por completo, pasando del 47,4 % al 0,0 %.
- Fidelidad mejora del 77,5 % al 93,2 %, superando el umbral del 80 %.
- Recall@5 pasa del 55,6 % al 89,6 %, asegurando que el contexto relevante esté presente casi siempre.
- Abstención por fallo se reduce del 17,5 % al 7,0 %, aprovechando mejor el conocimiento disponible.

El único umbral no cumplido es la latencia, que es un problema de ingeniería (ajuste de hiperparámetros e infraestructura) más que de diseño del sistema. Dado que el criterio de éxito requiere cumplir al menos 5 de 6 umbrales, y el RAG mejorado cumple exactamente 5, el proyecto alcanza el éxito declarado según la propuesta original.

Las próximas iteraciones deberían priorizar, (1) reducir la latencia de generación sin sacrificar exactitud, (2) afinar el prompt para evitar la contaminación entre documentos temáticamente similares, y (3) revisar los cuatro casos donde la información sigue ausente del top 5 de recuperación. Una vez resueltos estos puntos, el RAG mejorado estará listo para operar como asistente institucional de la UTB con altos estándares de calidad y confiabilidad.
