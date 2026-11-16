# Bitácora de uso de IA

> [!note]
> El uso de asistentes de IA (ChatGPT, Claude, Gemini, Copilot u otros) está permitido y se espera, siempre que sea declarado y que el equipo pueda explicar y defender todo lo entregado. Usar IA sin declararlo, o no poder explicar un fragmento de código o texto en la sustentación, se trata como falta de integridad académica.

| Fecha | Integrante | Herramienta | Para qué se usó | Qué se aceptó, modificó o descartó | Cómo se verificó |
| ----- | ---------- | ----------- | --------------- | ---------------------------------- | ---------------- |
| 12/11/2026 | Ana Meza | Claude Sonnet 5.5 | Elegir y analizar LLM a utilizar | Presentó diferentes opciones de modelos, se aceptó la recomendación de utilizar un modelo local con Ollama. Se descartó hacer uso de una API, se descartaron también otros modelos locales como Qwen 2.5. | Se consultó a otros compañeros, en otras fuentes como videos de Youtube. Se realizaron otras búsquedas en línea para validar las recomendaciones. |
| 12/11/2026 | Ana Meza | Claude Sonnet 5.5 | Ayudar a generar run_experiment.py | Se aceptó la estructura básica del script. Se utilizó una base ya creada de preguntas y respuestas por medio de la terminal para pasarla a la IA y que generará las modificaciones correspondientes. | Se realizaron pruebas para verificar su funcionamiento. |
| 15/11/2026 | Juan Narváez | Claude Sonnet 5.5 | Transcribir documento de Word a Markdown | Se aceptó el documento de errores de linea base, el cual se tenía sin formato en Word, para añadirlo a la carpeta de documentación del repositorio (docs/errores_linea_base.md) | Se verificó que el contenido generado era identico al original y que tuviera buena ortografía |
| 11/11/2026 | Alejandro Villarreal | Claude Sonnet 5.5 | Se utilizó para crear la estructura del código de extracción de datos. El estudiante no está tan familiarizado con el scrapping, por lo que fue necesario la guía del llm. | Se aceptó la estructura general propuesta por Claude, sin embargo se modificó la fomra en cómo realizaba el scrapping. Lo propuesto utilizaba la libería request de python, que la página objetivo rechazaba al reconorcela como una acción automatizada. Se modificó por una solución Playwright + Selenium. | Se verificó mediante prueba y error. Los errores eran de 503 y 403, lo que ocasionó revisar la forma en cómo se estaba pidiendo la información, que terminó causando el cambio. |

## Reflexión sobre una propuesta de IA rechazada

> [!important]
> Además, el informe incluye una reflexión de media página con al menos un caso en que la IA propuso algo incorrecto o inadecuado y cómo lo detectaron.
