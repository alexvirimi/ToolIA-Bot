"""Prepara el índice aislado y ejecuta una variante con Ollama."""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from langchain_core.output_parsers import StrOutputParser

from .asistente import (
    CANDIDATOS, CARPETA, CONSTANTE_RRF, K, PROMPT, ROOT, AsistenteExperimental,
    IndiceExperimental, RecuperacionHibrida, citas_validas, hit_fuente,
)

from config import get_llm
from csv_seguro import leer
from embeddings import (
    cargar_documentos, construir_indice, fragmentar_documentos,
    guardar_json, huella, identidad_modelo,
)
from prompts import TEMPLATE
from rag.rag import AsistenteRAG

INDICE = CARPETA / "indice"
CORRIDAS = CARPETA / "corridas"
PREGUNTAS = ROOT / "data" / "preguntas.csv"
VARIANTES = ("control", "prompt", "hibrido")
CAMPOS_PREGUNTAS = [
    "id", "categoria", "tiene_respuesta", "pregunta",
    "respuesta_referencia", "fuente_url", "pagina_o_seccion",
]


def nombre_local(nombre):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,59}", nombre):
        raise argparse.ArgumentTypeError("Usa 1–60 caracteres: a-z, 0-9, _ o -.")
    return nombre


def limite_positivo(valor):
    limite = int(valor)
    if limite < 1:
        raise argparse.ArgumentTypeError("El límite debe ser positivo.")
    return limite


def cargar_preguntas(ruta, limite):
    preguntas = leer(ruta)[CAMPOS_PREGUNTAS]
    if limite is not None:
        preguntas = preguntas.head(limite)
    if (preguntas.empty or preguntas["id"].duplicated().any()
            or preguntas[["id", "pregunta"]].apply(lambda c: c.str.strip().eq("")).any().any()):
        raise ValueError("Se necesitan preguntas e IDs no vacíos y únicos.")
    return preguntas.to_dict("records")


def ejecutar(args):
    preguntas = cargar_preguntas(args.preguntas, args.limit)
    if not (INDICE / "estado.json").is_file():
        raise ValueError("Falta el índice experimental: ejecuta primero el subcomando preparar.")
    destino = CORRIDAS / args.nombre
    destino.mkdir(parents=True, exist_ok=False)

    llm = get_llm()
    with IndiceExperimental(INDICE) as indice:
        if args.variante == "control":
            asistente = AsistenteRAG(indice=indice, llm=llm, k=K)
        else:
            recuperador = RecuperacionHibrida(indice) if args.variante == "hibrido" else indice
            asistente = AsistenteExperimental(recuperador, llm)

        guardar_json(destino / "run_info.json", {
            "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "variante": args.variante,
            "config_compartida": {
                "huella_indice": indice.estado["fingerprint"],
                "modelo_embeddings": indice.estado["model"],
                "modelo_generador": identidad_modelo(llm.model),
                "temperatura": llm.temperature,
                "seed": llm.seed,
                "num_predict": llm.num_predict,
                "reasoning": llm.reasoning,
                "k": K,
            },
            "indice": indice.estado,
            "prompt_sistema": TEMPLATE if args.variante == "control" else PROMPT,
            "fusion": {"candidatos_por_lista": CANDIDATOS, "constante_rrf": CONSTANTE_RRF}
            if args.variante == "hibrido" else None,
            "huella_preguntas": huella(preguntas),
            "n_preguntas": len(preguntas),
        })

        print("Calentando ambos modelos...", flush=True)
        asistente.indice.buscar("Hola", k=K)
        (llm | StrOutputParser()).invoke("Responde solo: listo.")

        filas = []
        with (destino / "recuperacion.jsonl").open("x", encoding="utf-8") as registro:
            for i, pregunta in enumerate(preguntas, 1):
                res = asistente.responder(pregunta["pregunta"])
                fragmentos = res["fragmentos"]
                citas = [] if res["abstencion"] else citas_validas(res["respuesta"], fragmentos)
                filas.append({
                    **pregunta,
                    "respuesta_modelo": res["respuesta"],
                    "latencia_s": res["latencia_total_s"],
                    "latencia_recuperacion_s": res["latencia_recuperacion_s"],
                    "abstencion_auto": "si" if res["abstencion"] else "no",
                    "citas_validas": " ".join(f"[{n}]" for n in citas),
                    "hit_fuente_at_5": hit_fuente(pregunta["fuente_url"],
                                                 pregunta["tiene_respuesta"], fragmentos),
                    "etiqueta": "",
                    "fidelidad": "",
                    "observaciones": "",
                })
                registro.write(json.dumps({
                    "id": pregunta["id"], "fragmentos": fragmentos, "citas_validas": citas,
                    "salida_modelo": res.get("salida_modelo", res["respuesta"]),
                }, ensure_ascii=False) + "\n")
                registro.flush()
                print(f"[{i}/{len(preguntas)}] ID {pregunta['id']}: {res['latencia_total_s']} s",
                      flush=True)

    temporal = destino / "respuestas.tmp"
    pd.DataFrame(filas).to_csv(temporal, index=False, encoding="utf-8-sig")
    temporal.rename(destino / "respuestas.csv")
    print(f"Listo: {destino / 'respuestas.csv'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("preparar", help="Construye solo rag_test/indice.")
    corrida = comandos.add_parser("corrida", help="Ejecuta una variante en una carpeta nueva.")
    corrida.add_argument("variante", choices=VARIANTES)
    corrida.add_argument("--nombre", required=True, type=nombre_local)
    corrida.add_argument("--preguntas", type=Path, default=PREGUNTAS)
    corrida.add_argument("--limit", type=limite_positivo)
    args = parser.parse_args()
    try:
        if args.comando == "preparar":
            documentos, _ = cargar_documentos()
            estado = construir_indice(fragmentar_documentos(documentos), ruta=INDICE)
            print(f"Índice {estado['status']}: {estado['count']} fragmentos en {INDICE}")
        else:
            ejecutar(args)
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
