"""Chat web con la variante `mejora` del RAG (rag_test/mejora.py).

Reutiliza AsistenteChat (historial, reformulación, cortesías, fuentes) y cambia
tres cosas respecto del RAG histórico, tal como en la corrida medida:
recuperación (RecuperadorDiverso), prompt (PROMPT_CONCISO) y la regla de
abstención (SIN_EVIDENCIA). Los parámetros del LLM los fija quien lo crea.
"""

import re
import sys
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # permite importar el paquete rag_test

from chat import AsistenteChat
from prompts import MENSAJE_ABSTENCION
from rag_test.mejora import PROMPT_CONCISO, RecuperadorDiverso

NOTA_HISTORIAL = (
    "\nLa conversación previa solo sirve para entender a qué se refiere el usuario; "
    "nunca es fuente de hechos sobre la UTB. Cita solo números de los FRAGMENTOS actuales.\n"
)
SIN_EVIDENCIA = re.compile(r"SIN_EVIDENCIA[.!]?", re.I)


def _normalizar_abstencion(texto):
    texto = texto.strip()
    return MENSAJE_ABSTENCION if not texto or SIN_EVIDENCIA.fullmatch(texto) else texto


class AsistenteChatMejora(AsistenteChat):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        prompt = ChatPromptTemplate.from_messages([
            ("system", (PROMPT_CONCISO + NOTA_HISTORIAL).replace("{", "{{").replace("}", "}}")),
            MessagesPlaceholder("historial"),
            ("human", "FRAGMENTOS:\n{contexto}\n\nPREGUNTA: {pregunta}"),
        ])
        self.chain_chat = (prompt | self.llm | StrOutputParser()
                           | RunnableLambda(_normalizar_abstencion))

    def contexto_para(self, fragmentos):
        contexto = super().contexto_para(fragmentos)
        # Misma disposición literal de vigencia que entrega la corrida medida.
        vigencias = {f["metadata"].get("disposiciones_vigencia", "") for f in fragmentos} - {""}
        if vigencias:
            contexto += ("\n\nDISPOSICIONES LITERALES DE VIGENCIA DE LAS FUENTES ANTERIORES:\n"
                         + "\n".join(sorted(vigencias)))
        return contexto


def crear_recuperador(indice, candidatos=30):
    """Recuperación de la corrida medida: fusión densa+léxica con diversidad."""
    return RecuperadorDiverso(indice, metodo="fusion", candidatos=candidatos)
