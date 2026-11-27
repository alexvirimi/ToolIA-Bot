# Análisis de la línea base del asistente UTB

## 1. Casos representativos de error

Esta tabla resume los casos de error más claros de la línea base, con caso, id, pregunta, respuesta de referencia, lo que respondió el modelo, tipo de error e hipótesis de causa. Presenta 20 casos seleccionados de la evaluación de la línea base (modelo sin recuperación documental), a partir del archivo `respuestas.csv` superando el mínimo de 10 solicitado.
Se incluyen errores de contenido, respuestas parciales, abstenciones injustificadas y un fallo técnico. La selección permite ilustrar los principales comportamientos observados, pero no reemplaza el análisis cuantitativo de las 57 preguntas.

| Caso | ID | Pregunta | Respuesta de referencia | Respuesta del modelo | Etiqueta | Análisis del error |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 | ¿Qué Promedio Ponderado Acumulado (PPA) debe mantener un estudiante de pregrado y qué pasa si al finalizar un período no lo logra? | Debe mantener un PPA mínimo de 3,20. Si al finalizar el período queda por debajo, pasa a Prueba Académica Parcial para el siguiente período. | Indica que el PPA mínimo es de 2,50 sobre 4,00. Añade pérdida de estatus activo, bloqueo de matrícula y riesgo de expulsión o retiro forzoso. | Alucinación | Reescribe la norma con valores de otra escala (4,00) y agrega consecuencias que no están en la referencia, completando con conocimiento genérico de otras universidades. |
| 2 | 3 | ¿Qué porcentaje mínimo de asistencia se exige en la modalidad presencial y qué ocurre si no se cumple? | Mínimo 80 por ciento de las sesiones de clase. Si no se cumple, el estudiante reprueba el curso con la calificación mínima establecida en el Reglamento. | Fija el mínimo en 75 por ciento y menciona inactividad académica, impedimento de regularización, promoción y obtención del título. | Alucinación | Confunde el umbral con una práctica común en otras instituciones y agrega sanciones no soportadas por el documento de referencia. |
| 3 | 4 | ¿Hasta qué semana puede retirar cursos un estudiante de pregrado presencial y qué pasa si retira todos? | Hasta el último día hábil de la semana 12 del período académico. Si retira todos sus cursos, pierde la calidad de estudiante regular. | Sitúa el plazo en la semana 6 del semestre y atribuye al retiro total consecuencias de abandono del programa y necesidad de reincorporación. | Alucinación | Usa plazos genéricos de retiro de otras universidades y especula sobre efectos administrativos sin sustento en el documento. |
| 4 | 6 | ¿Qué descuento recibe un Estudiante de Honor para un curso de inglés por extensión UTB y cuál es su vigencia? | El Estudiante de Honor recibe un descuento del 100 por ciento para un curso de inglés por extensión UTB. El estímulo es intransferible, no canjeable y tiene una vigencia de tres años. | Dice que no tiene acceso a precios actuales, políticas de descuentos ni estado vigente de promociones, y remite a oficinas. | Abstención por fallo | Prefiere no responder aunque la referencia ya contenga el dato exacto, lo que deja una oportunidad de mejora si se le da el documento como contexto al modelo. |
| 5 | 10 | ¿Cuántas veces puede un estudiante obtener el estímulo por alcanzar el nivel B2 en inglés? | Puede inscribirse en cada convocatoria, pero el beneficio por alcanzar el nivel B2 solo puede obtenerse una vez por estudiante. | Indica que no tiene información específica sobre la frecuencia o los límites del beneficio y remite a Admisiones o Relaciones Estudiantiles. | Abstención por fallo | La pregunta tiene disponibilidad documental completa (tiene_respuesta = si) y la referencia contiene expresamente la regla de obtención única. El modelo se abstiene injustificadamente. |
| 6 | 11 | ¿Cuáles son los beneficios de la Beca a la Excelencia y Desempeño Integral (All-round Scholarship)? | Beca del 100 por ciento de la matrícula de pregrado. Desarrollo personal: talleres de liderazgo y habilidades comunicativas, mentoría personalizada. Distinción académica en ceremonia pública. | Añade cobertura de materiales de estudio, libros, uniformes, kits tecnológicos, intercambios académicos, ferias científicas y actividades culturales. | Alucinación | Completa la lista con beneficios típicos de becas integrales que no aparecen en el documento de referencia. |
| 7 | 14 | ¿Cuántas veces puede obtenerse la Beca a la Excelencia y Desempeño Integral? | El estudiante puede inscribirse en cada convocatoria, pero la beca solo puede obtenerse una vez por estudiante. | Inventa una duración renovable de dos años académicos, diciendo que se puede renovar una vez más si se mantienen los promedios. | Alucinación | Confunde esta beca con programas renovables por semestre y crea una duración inventada sin base en la referencia. |
| 8 | 16 | ¿Son acumulables los beneficios de la política de estímulos y becas con otros descuentos de la universidad? | No. Los beneficios no son acumulables con otros beneficios o descuentos. Se aplicará únicamente el beneficio de mayor valor económico o el más favorable para el estudiante. | Acierta al indicar que no se acumulan, pero omite la regla de aplicar el beneficio de mayor valor o más favorable. | Parcial | Captura la idea principal pero deja fuera el detalle decisivo, dejando la respuesta incompleta para un caso real. |
| 9 | 19 | ¿Qué porcentaje de la matrícula cubre la Beca Legacy UTB para el primer y segundo semestre? | La Beca Legacy UTB cubre el 50 por ciento del valor total de la matrícula del primer y segundo semestre, siempre que se cumplan las condiciones de continuidad. | Afirma cobertura del 100 por ciento de la matrícula para ambos semestres y la dirige a familias con bajos recursos económicos. | Alucinación | Cambia el porcentaje concreto y añade un criterio socioeconómico que no está en la referencia disponible. |
| 10 | 21 | ¿Qué Promedio Ponderado Acumulado (PPA) mínimo debe tener un estudiante de pregrado para optar al título y cuál es para posgrado? | PPA mínimo de 3,20 para estudiantes de pregrado y mínimo 3,50 para estudiantes de posgrado. | Acierta el posgrado con 3,50, pero indica 3,0 para pregrado y agrega condiciones no solicitadas sobre reglamentos internos. | Parcial | Mezcla el umbral de aprobación de cursos (3,0) con el de titulación (3,20), generando confusión en un dato crítico para graduarse. |
| 11 | 22 | ¿Qué puntaje mínimo global debe obtener un estudiante de pregrado en el examen Saber Pro para optar al título? | Para optar al título, el estudiante de pregrado debe haber presentado y obtenido un puntaje global mínimo de 100 puntos, aplicable a quienes presentaron las pruebas a partir de 2024. | Niega que exista un puntaje mínimo único y fijo, y atribuye requisitos distintos por programa y año, con rangos inventados entre 200 y 350 puntos. | Alucinación | Confunde requisitos de admisión con requisitos de titulación e inventa rangos de puntaje que no aparecen en el documento. |
| 12 | 23 | ¿Es requisito demostrar nivel B2 de inglés para graduarse de un programa de pregrado presencial en la UTB? | Sí. Todos los programas de pregrado en la modalidad presencial tendrán como requisito demostrar un nivel B2 de conocimiento en inglés, para estudiantes que iniciaron a partir del 1 de enero de 2024. | Dice que no es un requisito general y añade excepciones de programas impartidos en inglés no sustentadas en la referencia. | Alucinación | Niega un requisito expreso del reglamento y especula sobre programas específicos sin sustento en el documento fuente. |
| 13 | 27 | ¿En qué condición queda un estudiante de pregrado que al finalizar un período no obtiene un PPA igual o superior a 3,20? | El estudiante queda en condición de Prueba Académica Parcial para el siguiente período, cuando los créditos matriculados acumulados sean mayores que los créditos del primer nivel. | Describe reprobación del período, bloqueo de avance hasta superar asignaturas pendientes, exámenes de recuperación y posible deserción o expulsión. | Alucinación | Interpreta el bajo promedio como una reprobación directa en lugar de una condición de prueba para el siguiente período. |
| 14 | 29 | ¿En qué condición queda un estudiante que inicia un período en Prueba Académica Total, obtiene un PPP igual o superior a 3,20 pero no un PPA igual o superior a 3,20? | El estudiante estará en condición de Recuperación Académica cuando, iniciando un período en Prueba Académica Total (PAT), logra un Promedio Ponderado del Período (PPP) igual o superior a 3,20 pero no logra obtener un PPA igual o superior a 3,20. | Sin respuesta por error HTTP 500 de llama-server (conexión interrumpida). | Incorrecta en el CSV; Errpr técnico en el análisis | Fallo de conexión con el servidor de lenguaje, por lo que no hay contenido del modelo para evaluar. Conviene repetir la pregunta antes de interpretar métricas. |
| 15 | 35 | ¿Cuál es la carga académica máxima de un estudiante regular de pregrado presencial en matrícula completa? | En un período académico, matrícula completa: hasta 18 créditos o el número máximo determinado por el nivel del programa. La dirección de programa puede autorizar hasta 20 créditos si el PPA es mayor a 4,00. | Afirma un máximo de 40 créditos académicos por semestre para garantizar equilibrio entre estudios y vida personal. | Alucinación | Infla el límite de créditos sin sustento en el documento, creando una cifra redonda pero inexistente en la normativa de la UTB. |
| 16 | 37 | ¿Cuánto dura el reembolso parcial de la matrícula si un estudiante se retira por semanas transcurridas? | 75 por ciento en la primera semana, 50 por ciento en la segunda, 25 por ciento en la tercera. A partir de la cuarta semana, no hay derecho a reembolso alguno. | Dice que no puede proporcionar el porcentaje exacto ni el valor monetario, y remite a la Secretaría Académica o Tesorería. | Abstención por fallo | No reproduce la tabla de reembolso de la referencia y declara falta de acceso a documentos internos. |
| 17 | 43 | ¿Un estudiante sancionado puede recibir distinciones académicas de la UTB? | No. El estudiante que sea sancionado por cualquier motivo no podrá recibir ninguna de las distinciones académicas establecidas en este Reglamento. | Acierta al responder que no, pero añade que la prohibición termina al levantarse la situación disciplinaria. | Parcial | Añade una condición de levantamiento de sanción que la referencia no menciona, ampliando el alcance más allá del documento. |
| 18 | 47 | ¿Qué porcentaje de descuento ofrece la Beca Premio Liderazgo Caribe? | La Beca Premio Liderazgo Caribe ofrece un 98 por ciento de descuento que cubre el total de semestres del plan de estudio de elección. | Indica un 100 por ciento de descuento en los costos de matrícula y aranceles académicos. | Incorrecta | Error de redondeo o confusión con becas de cobertura total, ya que cambia un dato numérico concreto. |
| 19 | 49 | ¿Cuál es el monto o cobertura del Crédito ICETEX para programas de pregrado de la UTB? | ICETEX ofrece un crédito del 100 por ciento de la carrera en cualquier universidad, pero también existen otros planes donde se prestan o condonan porcentajes más pequeños de la carrera. | Inventa coberturas específicas según el promedio: 100 por ciento si es 3,5 o superior, 80 por ciento entre 3,0 y 3,49, y 60 por ciento entre 2,5 y 2,99. | Incorrecta | Completa la información con rangos inventados que no aparecen en la referencia, presentándolos como política vigente. |
| 20 | 53 | ¿Qué estudiantes recibieron la distinción de Estudiante de Honor en 2025? | El Informe de Gestión 2025 presenta los 22 estudiantes distinguidos durante el primer período de 2025; no incluye el listado del segundo período. | Afirma que no tiene información y que probablemente el listado aún no ha sido publicado, y remite a canales institucionales. | Abstención por fallo | 	La disponibilidad documental es parcial (tiene_respuesta = parcial): el modelo podía entregar los 22 nombres del primer período y aclarar que la fuente no contiene el segundo. La abstención total desaprovecha la información existente. |

## 2. Análisis de las métricas de la línea base

La evaluación cuenta con 57 preguntas. De las cuales, 47 cuentan con información documental completa, una con información parcial y nueve no tienen respuesta en el corpus. Por tanto, 48 preguntas se consideran evaluables para exactitud, mientras que las nueve sin información permiten evaluar la abstención adecuada.

### 2.1. Exactitud

- **Exactitud estricta:** 2,1 % (1/48). Solo una respuesta fue clasificada como correcta.
- **Exactitud incluyendo respuestas parciales:** 14,6 % (7/48). Cuenta con una respuesta correcta y seis parciales.

La diferencia entre ambas métricas es que las parciales son respuestas que solo recuperan una parte de la información solicitada, no alcanzan a responderla de manera completa y fiable. 
Incluso con este criterio más flexible que reconoce las respuestas parciales, el desempeño de la línea base es bajo, solo siete de las 48 preguntas con información disponible fueron respondidas correcta o parcialmente correctas.

El intervalo de confianza del 95% de la exactitud estricta es de 0.4% a 10.9%. Este es un intervalo amplio, esto se debe en parte por el tamaño de la muestra, reforzando que el resultado es una evidencia experimental sobre el conjunto evaluado, no una estimación definitiva del desempeño.

### 2.2. Alucinaciones y errores factuales

En las métricas se identificaron 27 alucinaciones sobre 57 preguntas (47,4%), la principal categoría de error de la línea base. En estos casos el modelo no se limita a omitir información, sino que introduce cifras, condiciones, consecuencias o beneficios que contradicen la referencia o no están respaldados.

Este patrón sería especialmente problemático en un asistente institucional, porque presenta información no verificada con un tono de seguridad que puede inducir a decisiones equivocadas.

El intervalo de confianza del 95% para la tasa de alucinación es de 35% a 60.1%. Además, se registraron cuatro respuestas incorrectas (7,0 % del total) y seis parciales (10,5 %). Las respuestas incorrectas cambian datos centrales o presentan información incompatible con la referencia, mientras las parciales contienen algún elemento acertado, pero omiten una parte relevante de lo solicitado.

### 2.3. Abstenciones

El análisis de las abstenciones permite diferenciar dos comportamientos: la abstención adecuada, que ocurre cuando el modelo reconoce que no dispone de información suficiente para responder, y la abstención por fallo, que ocurre cuando el modelo se abstiene a pesar de que la respuesta está disponible total o parcialmente.
En la línea base se identificaron los siguientes resultados:

- Abstenciones totales: 19/57 (33.3%).
- Abstenciones adecuadas: 9/9 (100%).
- Abstenciones por fallo: 10/48 (20.8%). 

El resultado del 100 % de abstención adecuada indica que el modelo evitó responder en todos los casos en los que no existía información institucional en el corpus.

En diez preguntas, el modelo manifestó no disponer de información suficiente, aunque el corpus sí contenía elementos para construir una respuesta. Entre estos casos se encuentran las preguntas sobre los estímulos asociados al nivel B2 de inglés (ID 10) y los estudiantes que recibieron la distinción de Estudiante de Honor durante el primer período de 2025 (ID 53). En este último caso, aunque la información disponible era parcial, el modelo podía haber presentado los datos existentes y aclarado el alcance de la fuente.

El intervalo de confianza del 95 % para la tasa de abstención adecuada es de 70,1 % a 100 %, mientras que para las abstenciones por fallo se encuentra aproximadamente entre 11,7 % y 34,2 %.

Estos resultados muestran que, aunque el modelo tiene capacidad para reconocer algunos escenarios en los que debe abstenerse, también presenta dificultades para responder preguntas cuya información está disponible. Por tanto, la abstención no debe interpretarse exclusivamente como un comportamiento positivo: es necesario distinguir cuándo evita una respuesta no sustentada y cuándo representa una falla en el uso de la información institucional.

### 2.4. Comportamiento general de la línea base

| Clasificación | Cantidad | Porcentaje |
| --- | --- | --- |
| Alucinación | 27 | 47.4% |
| Abstención por fallo | 10 | 17,5 % |
| Abstención adecuada | 9 | 15,8 % |
| Parcial | 6 | 10,5 % |
| Incorrecta | 4 | 7,0 % |
| Correcta | 1 | 1,8 % |
| Total | 57 | 100 % |

Las alucinaciones constituyen casi la mitad de las respuestas evaluadas, mientras que las abstenciones por fallo muestran que el modelo tampoco logra aprovechar de manera consistente la información institucional que se encuentra disponible.

El comportamiento de la línea base se caracteriza por dos limitaciones principales: la generación de información no respaldada y la incapacidad para responder preguntas cuya información institucional no forma parte de su conocimiento efectivo.

### 2.5. Latencia

La latencia promedio fue de 3.81 segundos, con un máximo de 11.99 segundos.
El promedio se encuentra por debajo del umbral experimental de 10 segundos, aunque el máximo muestra que algunas consultas tuvieron tiempos considerablemente superiores al promedio.

### 2.6. Consideraciones sobre la evaluación

Sobre el **fallo técnico**, el ID 29 no contiene una respuesta del modelo debido a un error HTTP 500 de llama-server. Aunque el archivo CSV lo clasifica como incorrecta, no corresponde a un error semántico del modelo ya que no corresponde a una respuesta generada por el modelo.
Para un futuro conviene repetir la consulta y separar los errores de infraestructura de las etiquetas de calidad de respuesta.

Las métricas de fidelidad y Recall@5 no son aplicables a esta línea base en los mismos términos que al sistema RAG, el modelo no recupera fragmentos documentales que permitan evaluar la correspondencia de la respuesta con el contexto recuperado ni la recuperación de documentos relevantes.

## 3. Conclusiones

La evaluación de la línea base evidencia que hay limitaciones importantes. 
De las 48 preguntas con información disponible total o parcialmente, únicamente una obtuvo una respuesta completamente correcta y seis fueron clasificadas como parciales. La exactitud, incluso al incluir estas últimas, alcanzó apenas el 14,6 %.

La latencia promedio de 3,81 segundos es favorable frente al umbral de 10 segundos, pero el principal problema de la línea base no es la velocidad, sino la confiabilidad de las respuestas.
La principal dificultad identificada fue la generación de información no respaldada, reflejada en una tasa de alucinación del 47,4 %. A esto se suman las abstenciones por fallo, que representaron el 20,8 % de las preguntas con información disponible. Aunque el modelo presentó una tasa de abstención adecuada del 100 % frente a las preguntas sin respuesta en el corpus, este comportamiento no compensa las dificultades para responder consultas que requieren conocimiento institucional específico.

La línea base permite establecer un punto de comparación para evaluar el aporte de la arquitectura RAG. La incorporación de recuperación documental busca reducir la dependencia del conocimiento paramétrico del modelo, proporcionar información institucional como contexto y mejorar tanto la exactitud como la capacidad de responder con fundamento documental.