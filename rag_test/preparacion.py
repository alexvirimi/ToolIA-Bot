"""Preparación experimental: divide entradas demasiado largas sin truncarlas."""

import json
import sqlite3
from pathlib import Path

from .mejora import fragmentar_integral
from embeddings import (_api, _ventanas, construir_indice, guardar_json, huella,
                        identidad_modelo, validar_vectores)


def preparar_integral(documentos, ruta, cache_anterior=None):
    ruta = Path(ruta)
    ruta.mkdir(parents=True, exist_ok=True)
    identidad = identidad_modelo()
    fragmentos = fragmentar_integral(documentos)
    ajustes = []
    anterior = sqlite3.connect(Path(cache_anterior).resolve().as_uri() + "?mode=ro", uri=True) if cache_anterior and Path(cache_anterior).exists() else None

    def entrada(f):
        return "title: " + f["metadata"]["title"][:200] + " | text: " + f["text"]

    try:
        with sqlite3.connect(ruta / "cache.sqlite3") as cache:
            cache.execute("CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector TEXT NOT NULL)")

            def lote(items):
                pendientes, claves = [], []
                for f in items:
                    clave = huella([identidad["digest"], entrada(f)])
                    encontrado = cache.execute("SELECT vector FROM embeddings WHERE key=?", (clave,)).fetchone()
                    if not encontrado and anterior:
                        encontrado = anterior.execute("SELECT vector FROM embeddings WHERE key=?", (clave,)).fetchone()
                        if encontrado:
                            cache.execute("INSERT OR IGNORE INTO embeddings VALUES (?, ?)", (clave, encontrado[0]))
                    if not encontrado:
                        pendientes.append(f)
                        claves.append(clave)
                if not pendientes:
                    return items
                try:
                    vectores = _api("/api/embed", {"model": identidad["name"],
                        "input": [entrada(f) for f in pendientes], "truncate": False, "keep_alive": "15m"})["embeddings"]
                except RuntimeError as exc:
                    if "input length exceeds" not in str(exc):
                        raise
                    if len(items) > 1:
                        mitad = len(items) // 2
                        return lote(items[:mitad]) + lote(items[mitad:])
                    f = items[0]
                    if len(f["text"]) < 200:
                        raise ValueError("Entrada corta excede contexto: revisar el tokenizador, no truncar.") from exc
                    tamano = max(150, len(f["text"]) // 2)
                    hijos = []
                    for i, texto in enumerate(_ventanas(f["text"], tamano, min(100, tamano // 4))):
                        meta = {**f["metadata"], "text_hash": huella(texto), "embedding_parent": f["id"], "parte_embedding": i}
                        hijos.append({"id": huella([f["id"], i, texto, "division-contexto-v1"]), "text": texto, "metadata": meta})
                    ajustes.append({"original": f["id"], "motivo": "contexto_embeddings_excedido",
                                    "caracteres": len(f["text"]), "hijos": [h["id"] for h in hijos]})
                    return lote(hijos)
                validar_vectores(vectores, len(pendientes))
                cache.executemany("INSERT OR REPLACE INTO embeddings VALUES (?, ?)",
                                  [(k, json.dumps(v)) for k, v in zip(claves, vectores)])
                cache.commit()
                return items

            finales = []
            for i in range(0, len(fragmentos), 24):
                finales.extend(lote(fragmentos[i:i + 24]))
                if i % 480 == 0:
                    print(f"Entradas verificadas {min(i + 24, len(fragmentos))}/{len(fragmentos)}", flush=True)
            cache.commit()
    finally:
        if anterior:
            anterior.close()
    guardar_json(ruta / "preparacion.json", {"modelo": identidad, "ajustes": ajustes,
                 "fragmentos_originales": len(fragmentos), "fragmentos_finales": len(finales), "truncamiento": False})
    guardar_json(ruta / "fragmentos.json", finales)
    return construir_indice(finales, ruta=ruta)


def main():
    import argparse
    from embeddings import cargar_documentos

    parser = argparse.ArgumentParser(description="Construye el índice de fragmentación integral (variante mejora).")
    parser.add_argument("--construir", action="store_true", required=True)
    parser.add_argument("--ruta", type=Path, default=Path(__file__).resolve().parent / "indice" / "mejora80-integral-v2")
    parser.add_argument("--cache-anterior", type=Path, help="cache.sqlite3 de otro índice, para reutilizar embeddings idénticos")
    args = parser.parse_args()
    documentos, _ = cargar_documentos()
    estado = preparar_integral(documentos, args.ruta, cache_anterior=args.cache_anterior)
    print(f"Índice listo: {estado.get('count')} fragmentos en {args.ruta}")


if __name__ == "__main__":
    main()
