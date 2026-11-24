import argparse
import json
import sys
import re
import time

from pathlib import Path
from langchain_core.output_parsers import StrOutputParser


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from config import get_llm
from prompts import rag_prompt, MENSAJE_ABSTENCION
from embeddings import cargar_indice

def formatear_contexto(fragmentos):
    """Numera cada fragmento con su procedencia para que el LLM pueda citarlo."""
    bloques = []
    for n, f in enumerate(fragmentos, 1):
        metadata = f["metadata"]
        ubicacion = metadata["title"]
        if metadata.get("page"):
            ubicacion += f", p. {metadata['page']}"
        if metadata.get("section"):
            ubicacion += f", {metadata['section']}"
        bloques.append(f"[{n}] ({ubicacion})\n{f['text']}")
    return "\n\n".join(bloques)


def construir_fuentes(fragmentos, numeros=None):
    """
    Lista de fuentes (documento, página, sección, URL). 
    Si hay 'numeros', son el conjunto de citas que el modelo usó.
    Convierte fragmentos en una lista de fuentes para mostrar al usuario.
    """
    fuentes = []
    for n, f in enumerate(fragmentos, 1):
        if numeros is not None and n not in numeros:
            continue
        metadata = f["metadata"]
        fuentes.append({
            "n": n,
            "titulo": metadata["title"],
            "pagina": metadata.get("page") or None,
            "seccion": metadata.get("section") or None,
            "url": metadata["source_url"],
            "similitud": round(f["similarity"], 3),
        })
    return fuentes


class AsistenteRAG:
    """RAG sobre el índice vectorial de la UTB.

    k: fragmentos a recuperar (Recall@5 de la propuesta -> k=5).
    umbral: similitud coseno mínima del mejor fragmento; por debajo se abstiene
        sin llamar al LLM. None lo desactiva. Calíbralo con un conjunto de
        desarrollo, no con las 50 preguntas de prueba.
    """

    def __init__(self, indice=None, llm=None, k=5, umbral=None):
        self.indice = indice or cargar_indice()
        self.llm = llm or get_llm()
        self.chain = rag_prompt | self.llm | StrOutputParser()
        self.k = k
        self.umbral = umbral

    def responder(self, pregunta):
        t0 = time.perf_counter()
        fragmentos = self.indice.buscar(pregunta, k=self.k)
        t_recuperacion = time.perf_counter() - t0
        mejor = max((f["similarity"] for f in fragmentos), default=0.0)

        # Si el mejor fragmento ni siquiera llega al umbral, la búsqueda no encontró nada relevante
        # No le pregunto al LLM y me abstengo.
        if self.umbral is not None and mejor < self.umbral:
            respuesta, motivo = MENSAJE_ABSTENCION, "umbral_similitud"
        else:
            respuesta = self.chain.invoke({
                "contexto": formatear_contexto(fragmentos),
                "pregunta": pregunta,
            }).strip()
            motivo = "llm" if MENSAJE_ABSTENCION.lower() in respuesta.lower() else None

        abstencion = motivo is not None
        if abstencion:
            fuentes, citas = [], False
        else:
            # Extraer los números en entre corchetes
            citadas = {int(n) for n in re.findall(r"\[(\d+)\]", respuesta)}
            # Descarta que no se inventen números
            citadas = {n for n in citadas if 1 <= n <= len(fragmentos)}
            citas = bool(citadas)  # Indica si el modelo citó o no algo
            # Si el modelo no citó nada, se muestran todos los recuperados como referencia.
            fuentes = construir_fuentes(fragmentos, citadas or None)

        return {
            "pregunta": pregunta,
            "respuesta": respuesta,
            "abstencion": abstencion,
            "motivo_abstencion": motivo,
            "citas_en_respuesta": citas,
            "fuentes": fuentes,
            "fragmentos": fragmentos,  # para calcular Recall@5 y analizar errores
            "mejor_similitud": round(mejor, 4),
            "latencia_recuperacion_s": round(t_recuperacion, 3),
            "latencia_total_s": round(time.perf_counter() - t0, 3),
        }

    def close(self):
        self.indice.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def mostrar(resultado):
    print(f"ToolIA: {resultado['respuesta']}")
    if resultado["fuentes"]:
        print("Fuentes:")
        for f in resultado["fuentes"]:
            partes = [f["titulo"]]
            if f["pagina"]:
                partes.append(f"p. {f['pagina']}")
            if f["seccion"]:
                partes.append(f["seccion"])
            print(f"  [{f['n']}] {', '.join(partes)} - {f['url']}")
    print(f"({resultado['latencia_total_s']} s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ToolIA-Bot con RAG")
    parser.add_argument(
        "--pregunta", help="Una sola pregunta; sin ella se abre el chat")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--umbral", type=float, default=None)
    parser.add_argument("--json", action="store_true",
                        help="Imprime el resultado completo en JSON")
    args = parser.parse_args()

    with AsistenteRAG(k=args.k, umbral=args.umbral) as asistente:
        if args.pregunta:
            res = asistente.responder(args.pregunta)
            print(json.dumps(res, ensure_ascii=False, indent=2)
                  if args.json else "", end="")
            if not args.json:
                mostrar(res)
        else:
            while True:
                entrada = input("Pregunta usuario: ").strip()
                if entrada.lower() in ["exit", "quit", "salir", "terminar"]:
                    print("¡Hasta luego!")
                    break
                if entrada:
                    mostrar(asistente.responder(entrada))
