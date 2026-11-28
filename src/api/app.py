import argparse
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "chat"))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chat import AsistenteChat, RegistroChat, evento_turno
from config import MODEL_NAME, get_llm
from embeddings import cargar_indice

DIST = ROOT / "frontend" / "dist"
CARPETA_CHATS = ROOT / "chats"
MAX_SESIONES = 100
INACTIVIDAD_S = 30 * 60
K = 5
UMBRAL = None
TURNOS_CONTEXTO = 4

SESIONES_LOCK = threading.Lock()
GENERACION_LOCK = threading.Lock()
recursos = {}
sesiones = {}


class Sesion:
    def __init__(self):
        self.asistente = AsistenteChat(
            indice=recursos["indice"], llm=recursos["llm"],
            k=K, umbral=UMBRAL, max_turnos=TURNOS_CONTEXTO,
        )
        self.registro = RegistroChat(CARPETA_CHATS)
        self.registro.escribir({"evento": "inicio", "origen": "web", "k": K,
                                "umbral": UMBRAL, "turnos_contexto": TURNOS_CONTEXTO})
        self.turnos = 0
        self.ultimo_uso = time.monotonic()

    def cerrar(self, motivo):
        self.registro.escribir({"evento": "fin", "turnos": self.turnos, "motivo": motivo})
        self.registro.cerrar()


def cerrar_sesion(sesion_id, motivo):
    with SESIONES_LOCK:
        sesion = sesiones.pop(sesion_id, None)
    if sesion:
        sesion.cerrar(motivo)


def cerrar_inactivas():
    limite = time.monotonic() - INACTIVIDAD_S
    with SESIONES_LOCK:
        vencidas = [i for i, s in sesiones.items() if s.ultimo_uso < limite]
    for sesion_id in vencidas:
        cerrar_sesion(sesion_id, "inactividad")


def obtener_o_crear_sesion(sesion_id):
    with SESIONES_LOCK:
        sesion = sesiones.get(sesion_id)
        if sesion:
            return sesion_id, sesion
        if len(sesiones) >= MAX_SESIONES:
            raise HTTPException(503, "Hay demasiadas conversaciones activas. Intenta de nuevo en unos minutos.")
        sesion_id = uuid.uuid4().hex
        sesiones[sesion_id] = Sesion()
        return sesion_id, sesiones[sesion_id]


@asynccontextmanager
async def lifespan(app):
    recursos["indice"] = cargar_indice()
    recursos["llm"] = get_llm()
    yield
    for sesion_id in list(sesiones):
        cerrar_sesion(sesion_id, "servidor detenido")
    recursos["indice"].close()


app = FastAPI(title="ToolIA-Bot", lifespan=lifespan)


class PreguntaIn(BaseModel):
    pregunta: str = Field(min_length=1, max_length=1000)
    sesion_id: Optional[str] = None


@app.get("/api/salud")
def salud():
    return {"ok": True, "modelo": MODEL_NAME, "fragmentos": recursos["indice"].estado["count"]}


@app.post("/api/chat")
def chat(datos: PreguntaIn):
    pregunta = datos.pregunta.strip()
    if not pregunta:
        raise HTTPException(422, "La pregunta está vacía.")
    cerrar_inactivas()
    sesion_id, sesion = obtener_o_crear_sesion(datos.sesion_id)
    sesion.ultimo_uso = time.monotonic()

    with GENERACION_LOCK:
        try:
            resultado = sesion.asistente.responder(pregunta)
        except Exception as e:
            sesion.registro.escribir({"evento": "error", "pregunta": pregunta, "detalle": str(e)})
            raise HTTPException(503, "No se pudo generar la respuesta. Revisa que Ollama esté en ejecución.")

    sesion.turnos += 1
    sesion.registro.escribir(evento_turno(sesion.turnos, resultado))
    return {
        "sesion_id": sesion_id,
        "respuesta": resultado["respuesta"],
        "abstencion": resultado["abstencion"],
        "fuentes": [
            {"n": f["n"], "titulo": f["titulo"], "pagina": f["pagina"], "seccion": f["seccion"], "url": f["url"]}
            for f in resultado["fuentes"]
        ],
        "latencia_s": resultado["latencia_total_s"],
    }


@app.post("/api/chat/{sesion_id}/cerrar")
def cerrar(sesion_id: str):
    cerrar_sesion(sesion_id, "cerrada")
    return {"ok": True}


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API y sitio web de ToolIA-Bot")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
