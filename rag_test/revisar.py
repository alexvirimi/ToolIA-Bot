"""Muestra respuestas y evidencia para revisión IA/humana sin ejecutar modelos."""

import argparse
import json
import sys
from pathlib import Path

from .asistente import ROOT
from csv_seguro import leer
from embeddings import huella
from .mejora import limpiar_pagina, normalizar


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("corrida")
    p.add_argument("--contra")
    p.add_argument("--inicio", type=int, default=1)
    p.add_argument("--fin", type=int, default=100_000)
    p.add_argument("--evidencia", action="store_true")
    p.add_argument("--sembrar-previas", action="store_true")
    p.add_argument("--solo-respuestas", action="store_true")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    carpeta = ROOT / "rag_test/corridas" / args.corrida
    filas = leer(carpeta / "respuestas.csv").to_dict("records")
    recuperadas = {r["id"]: r for r in map(json.loads, (carpeta / "recuperacion.jsonl").read_text(encoding="utf-8").splitlines())}
    anteriores = {}
    contextos_previos = {}
    if args.contra:
        anteriores = {r["id"]: r for r in leer(ROOT / "rag_test/corridas" / args.contra / "respuestas.csv").to_dict("records")}
        archivo = ROOT / "rag_test/corridas" / args.contra / "recuperacion.jsonl"
        contextos_previos = {r["id"]: r for r in map(json.loads, archivo.read_text(encoding="utf-8").splitlines())}
    vistos = set()
    normalizados = set()
    fuentes_completas = set()
    if args.sembrar_previas:
        for nombre in ("control-57", "prompt-57", "hibrido-57"):
            archivo = ROOT / "rag_test/corridas" / nombre / "recuperacion.jsonl"
            for r in map(json.loads, archivo.read_text(encoding="utf-8").splitlines()):
                vistos.update(huella(f["text"]) for f in r["fragmentos"])
                normalizados.update(normalizar(limpiar_pagina(f["text"])) for f in r["fragmentos"])
        for pagina in (ROOT / "rag_test/evaluaciones/mejora80-20261126/ocr_becas").glob("pagina_*.md"):
            vistos.add(huella(pagina.read_text(encoding="utf-8")))
        verificado = ROOT / "data/processed/ocr_becas_9bb3f68c.json"
        if verificado.exists():
            fuentes_completas.add(json.loads(verificado.read_text(encoding="utf-8"))["sha256_origen"])
    for posicion, fila in enumerate(filas, 1):
        if not args.inicio <= posicion <= args.fin:
            continue
        r = recuperadas[fila["id"]]
        print(f"\n## {fila['id']} [{fila['tiene_respuesta']}] {fila['pregunta']}")
        previo = anteriores.get(fila["id"])
        if previo and previo["respuesta_modelo"] == fila["respuesta_modelo"]:
            print("RESPUESTA EXACTAMENTE IGUAL A LA REFERENCIA DE COMPARACIÓN:", previo["etiqueta"])
        else:
            print("RESPUESTA:", fila["respuesta_modelo"])
        print("FIN:", fila.get("fin_generacion", "no registrado"))
        if args.solo_respuestas:
            previo = contextos_previos.get(fila["id"])
            firma = lambda x: [(f["text"], f["metadata"]) for f in x["fragmentos"]]
            print("CONTEXTO:", "idéntico a la comparación" if previo and firma(previo) == firma(r) else "cambió; revisar fragmentos")
            continue
        for i, f in enumerate(r["fragmentos"], 1):
            m, clave = f["metadata"], huella(f["text"])
            print(f"[{i}] {m['title']}; p. {m.get('page')} a {m.get('page_end', m.get('page'))}; {m.get('section', '')}; sha {clave[:10]}")
            conocido = clave in vistos or normalizar(limpiar_pagina(f["text"])) in normalizados or m.get("source_hash") in fuentes_completas
            if args.evidencia and not conocido:
                print(f["text"])
                vistos.add(clave)
            elif args.evidencia:
                print("(Contenido ya revisado.)")


if __name__ == "__main__":
    main()
