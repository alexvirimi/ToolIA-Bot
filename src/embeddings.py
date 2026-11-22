"""Vectorización reutilizable de ToolIA-Bot; el análisis vive en el notebook.

No descarga datos, no entrena un LLM y no ejecuta nada al importar.
Entrada: JSON de scripts/extract_text.py. Salida: Chroma persistente.
Ejemplo: python src/embeddings.py --construir
"""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from urllib.parse import urlparse

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
MODELO = "embeddinggemma:300m"
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if not OLLAMA_URL.startswith(("http://", "https://")):
    OLLAMA_URL = "http://" + OLLAMA_URL
RUTA_INDICE = Path(os.environ.get("TOOLIA_INDICE", str(Path(os.environ.get("LOCALAPPDATA", str(ROOT / ".local"))) / "ToolIA-Bot/crisp_vectorial")))
CUARENTENA = r"declaraci.n.de.renta|declaracion.de.renta|estados.financieros|eeff|curriculum|reporte.directivos|cerl|memoria.economica"


def huella(valor):
    contenido = valor if isinstance(valor, bytes) else json.dumps(valor, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(contenido).hexdigest()


def guardar_json(ruta, contenido):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(contenido, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporal.replace(ruta)


def _leer(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def _oficial(url):
    host = (urlparse(url).hostname or "").lower()
    return host == "utb.edu.co" or host.endswith(".utb.edu.co")


def cargar_documentos(carpeta=None):
    """Carga el formato de Alex, verifica fuentes/hashes y deduplica.

    Admite un catálogo previo y extracciones individuales posteriores. No
    interpreta preguntas.csv, resultados ni JSON sin el esquema documental.
    Devuelve documentos y una auditoría de archivos procesados, no del sitio web.
    """
    carpeta = Path(carpeta or ROOT / "data/processed")
    documentos, auditoria, vistos = [], [], {}
    for ruta in sorted(carpeta.glob("*.json")):
        doc = _leer(ruta)
        if not isinstance(doc, dict) or not {"paginas", "archivo_origen", "fuente_url"} <= doc.keys():
            continue
        archivo = str(doc["archivo_origen"]).replace("\\", "/")
        fila = {"json": ruta.name, "archivo": archivo, "estado": "aceptado", "motivo": ""}
        origen = ROOT / archivo if archivo.startswith("data/") else carpeta.parent / archivo
        if not origen.resolve().is_relative_to(carpeta.parent.resolve()):
            fila.update(estado="excluido", motivo="Ruta de origen fuera de data")
        elif re.search(CUARENTENA, archivo, re.I):
            fila.update(estado="cuarentena", motivo="Minimización: documento fiscal/financiero identificable o currículum")
        elif not _oficial(doc["fuente_url"]):
            fila.update(estado="excluido", motivo="Sin URL oficial UTB verificable")
        elif not origen.exists() or huella(origen.read_bytes()) != doc.get("sha256_origen"):
            fila.update(estado="excluido", motivo="Origen ausente o hash distinto; volver a extraer")
        elif not any(p.get("texto", "").strip() for p in doc["paginas"]):
            fila.update(estado="excluido", motivo="Sin texto")
        else:
            # NFKC recupera ligaduras PDF (por ejemplo, ﬁ -> fi), sin borrar cifras.
            doc["paginas"] = [{**p, "texto": unicodedata.normalize("NFKC", p.get("texto", ""))} for p in doc["paginas"]]
            doc.setdefault("document_id", huella(archivo.removeprefix("data/"))[:20])
            doc.setdefault("titulo", Path(archivo).stem)
            doc["archivo_origen"] = archivo
            doc["urls"] = sorted({doc["fuente_url"], *[u for u in doc.get("urls", []) if _oficial(u)]})
            key = doc["sha256_origen"]
            if key in vistos:
                anterior = vistos[key]
                anterior["urls"] = sorted(set(anterior["urls"] + doc["urls"]))
                fila.update(estado="duplicado", motivo="Mismo hash; se conservan sus URLs como alias")
            else:
                vistos[key] = doc
                documentos.append(doc)
        auditoria.append(fila)
    if not documentos:
        raise ValueError("No hay textos válidos en data/processed. Ejecute scripts/extract_text.py y revise sus avisos.")
    return documentos, auditoria


def _ventanas(texto, max_caracteres, solape):
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + max_caracteres, len(texto))
        if fin < len(texto):
            corte = texto.rfind(" ", inicio + max_caracteres // 2, fin)
            if corte > inicio:
                fin = corte
        parte = texto[inicio:fin].strip()
        if parte:
            yield parte
        if fin == len(texto):
            break
        inicio = max(inicio + 1, fin - solape)


def fragmentar_documentos(documentos, max_caracteres=1600, solape=180):
    """Respeta páginas y encabezados; tamaño en CARACTERES, no en tokens."""
    if max_caracteres < 100 or not 0 <= solape < max_caracteres:
        raise ValueError("Tamaño/solape inválidos")
    fragmentos = {}
    for doc in documentos:
        seccion = ""
        for pagina in doc["paginas"]:
            seccion = pagina.get("seccion", seccion)
            bloques = re.split(r"(?im)(?=^\s*(?:art[ií]culo\s+\d+|#{1,6}\s+))", pagina["texto"])
            for bloque in bloques:
                encabezado = re.match(r"\s*(art[ií]culo\s+\d+[^\n]*|#{1,6}[^\n]+)", bloque, re.I)
                if encabezado:
                    seccion = encabezado.group(1).strip()[:180]
                for i, texto in enumerate(_ventanas(bloque.strip(), max_caracteres, solape)):
                    if len(texto) < 30:
                        continue
                    meta = {"document_id": doc["document_id"], "title": doc["titulo"], "source_url": doc["fuente_url"],
                            "file": doc["archivo_origen"], "page": pagina.get("pagina") or 0, "section": seccion,
                            "source_hash": doc["sha256_origen"], "text_hash": huella(texto)}
                    identificador = huella([doc["document_id"], meta["page"], seccion, i, texto, max_caracteres, solape])
                    fragmentos[identificador] = {"id": identificador, "text": texto, "metadata": meta}
    return list(fragmentos.values())


def _api(endpoint, payload=None):
    with requests.Session() as sesion:
        sesion.trust_env = False  # No enviar Ollama local a un proxy.
        respuesta = sesion.get(OLLAMA_URL + endpoint, timeout=240) if payload is None else sesion.post(OLLAMA_URL + endpoint, json=payload, timeout=240)
        if not respuesta.ok:
            raise RuntimeError(f"Ollama HTTP {respuesta.status_code}: {respuesta.text[:500]}")
        resultado = respuesta.json()
        if resultado.get("error"):
            raise RuntimeError(resultado["error"])
        return resultado


def identidad_modelo(modelo=MODELO):
    modelos = _api("/api/tags")["models"]
    encontrado = next((m for m in modelos if m["name"] == modelo), None)
    if not encontrado:
        raise ValueError(f"Descargue primero el modelo: ollama pull {modelo}")
    return {"name": modelo, "digest": encontrado["digest"], "details": encontrado.get("details", {})}


def validar_vectores(vectores, cantidad=None, dimension=None):
    matriz = np.asarray(vectores, dtype=np.float32)
    if matriz.ndim != 2 or matriz.shape[0] == 0 or matriz.shape[1] == 0:
        raise ValueError("Matriz de embeddings vacía o inválida")
    if cantidad is not None and len(matriz) != cantidad:
        raise ValueError("No hay un vector por entrada")
    if dimension is not None and matriz.shape[1] != dimension:
        raise ValueError("Dimensiones incompatibles")
    if not np.isfinite(matriz).all() or np.any(np.linalg.norm(matriz, axis=1) == 0):
        raise ValueError("Vectores no finitos o de norma cero")
    return matriz


def generar_embeddings(textos, modelo=MODELO, cache=None, lote=24, consulta=False, cache_anterior=None):
    """Caché por identidad del modelo + entrada exacta, no por número de fila.

    cache_anterior es opcional y de solo lectura: permite aprovechar el intento
    interrumpido sin aceptar vectores de otro modelo o texto. truncate=False
    rechaza entradas demasiado largas en lugar de mutilarlas silenciosamente.
    """
    if not textos or lote < 1:
        raise ValueError("Entradas vacías o lote inválido")
    identidad = identidad_modelo(modelo)
    nuevos, reutilizados, anteriores = 0, 0, 0
    vectores = []
    conexion = sqlite3.connect(cache) if cache else None
    antigua = None
    try:
        if conexion:
            conexion.execute("CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector TEXT NOT NULL)")
        if cache_anterior and Path(cache_anterior).exists():
            antigua = sqlite3.connect(Path(cache_anterior).resolve().as_uri() + "?mode=ro", uri=True)
        for inicio in range(0, len(textos), lote):
            entradas = textos[inicio:inicio + lote]
            keys = [huella([identidad["digest"], t]) for t in entradas]
            batch, faltan = [], []
            for i, key in enumerate(keys):
                registro = conexion.execute("SELECT vector FROM embeddings WHERE key=?", (key,)).fetchone() if conexion else None
                desde_anterior = False
                if registro is None and antigua:
                    registro = antigua.execute("SELECT vector FROM embeddings WHERE key=?", (key,)).fetchone()
                    desde_anterior = registro is not None
                batch.append(json.loads(registro[0]) if registro else None)
                if registro:
                    reutilizados += 1
                    anteriores += int(desde_anterior)
                else:
                    faltan.append(i)
            if faltan:
                payload = {"model": modelo, "input": [entradas[i] for i in faltan], "truncate": False, "keep_alive": "15m"}
                if consulta:
                    payload["options"] = {"num_gpu": 0}
                salida = _api("/api/embed", payload)["embeddings"]
                validar_vectores(salida, len(faltan))
                for i, vector in zip(faltan, salida):
                    batch[i] = vector
                nuevos += len(faltan)
            matriz = validar_vectores(batch, len(entradas), vectores[0].shape[1] if vectores else None)
            if conexion:
                conexion.executemany("INSERT OR REPLACE INTO embeddings VALUES (?, ?)", [(key, json.dumps(vector)) for key, vector in zip(keys, batch)])
                conexion.commit()
            vectores.append(matriz)
            if not consulta and inicio % (lote * 20) == 0:
                print(f"Embeddings {min(inicio + lote, len(textos))}/{len(textos)}", flush=True)
    finally:
        if conexion:
            conexion.close()
        if antigua:
            antigua.close()
    return np.vstack(vectores), {"model": identidad, "new": nuevos, "reused": reutilizados, "legacy_reused": anteriores}


def _chroma(ruta):
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(path=str(ruta), settings=Settings(anonymized_telemetry=False))


def construir_indice(fragmentos, ruta=RUTA_INDICE, modelo=MODELO, lote=24, cache_anterior=None):
    """Publica un índice solo después de validar todos los fragmentos.

    Los snapshots anteriores no se borran: una actualización fallida no debe
    destruir el último índice válido. No-op si contenido y modelo no cambian.
    """
    if not fragmentos or len({f["id"] for f in fragmentos}) != len(fragmentos):
        raise ValueError("Fragmentos vacíos o IDs duplicados")
    ruta = Path(ruta)
    ruta.mkdir(parents=True, exist_ok=True)
    identidad = identidad_modelo(modelo)
    firma = huella({"fragments": fragmentos, "model": identidad["digest"], "format": "title-text-v1"})
    estado = _leer(ruta / "estado.json") if (ruta / "estado.json").exists() else {}
    with _chroma(ruta) as cliente:
        if estado.get("fingerprint") == firma:
            coleccion = cliente.get_collection(estado["collection"], embedding_function=None)
            if coleccion.count() != len(fragmentos):
                raise ValueError("El índice persistido está incompleto")
            return {**estado, "status": "sin cambios", "new": 0, "reused": len(fragmentos), "legacy_reused": 0}
        t0 = time.perf_counter()
        entradas = ["title: " + f["metadata"]["title"][:200] + " | text: " + f["text"] for f in fragmentos]
        vectores, estadisticas = generar_embeddings(entradas, modelo, ruta / "cache.sqlite3", lote=lote, cache_anterior=cache_anterior)
        segundos_embeddings = time.perf_counter() - t0
        dimension = validar_vectores(vectores, len(fragmentos)).shape[1]
        nombre = "crisp_" + firma[:24]
        coleccion = cliente.get_or_create_collection(nombre, embedding_function=None, metadata={"hnsw:space": "cosine"})
        t0 = time.perf_counter()
        for inicio in range(0, len(fragmentos), 200):
            batch = fragmentos[inicio:inicio + 200]
            coleccion.upsert(ids=[f["id"] for f in batch], documents=[f["text"] for f in batch],
                            embeddings=vectores[inicio:inicio + 200], metadatas=[f["metadata"] for f in batch])
        if coleccion.count() != len(fragmentos):
            raise ValueError("Conteo vectorial incompleto; no se publica")
        estado = {"fingerprint": firma, "collection": nombre, "count": len(fragmentos), "dimension": int(dimension),
                  "model": identidad, "embedding_seconds": segundos_embeddings, "index_seconds": time.perf_counter() - t0,
                  "status": "construido", **{k: v for k, v in estadisticas.items() if k != "model"}}
        guardar_json(ruta / "estado.json", estado)
    return estado


class IndiceVectorial:
    """Contrato pequeño para el chatbot: buscar() devuelve texto y procedencia."""

    def __init__(self, ruta):
        self.ruta = Path(ruta)
        self.estado = _leer(self.ruta / "estado.json")
        self.cliente = _chroma(self.ruta)
        self.coleccion = self.cliente.get_collection(self.estado["collection"], embedding_function=None)
        if self.coleccion.count() != self.estado["count"]:
            self.close()
            raise ValueError("El índice no coincide con su manifiesto")

    def buscar(self, pregunta, k=5, usar_cache=True):
        if not isinstance(pregunta, str) or not pregunta.strip() or len(pregunta) > 6000 or k < 1:
            raise ValueError("Pregunta o k inválidos")
        actual = identidad_modelo(self.estado["model"]["name"])
        if actual["digest"] != self.estado["model"]["digest"]:
            raise ValueError("El modelo cambió: reconstruir el índice")
        vectores, _ = generar_embeddings(["task: search result | query: " + pregunta], modelo=actual["name"],
                                         cache=self.ruta / "cache.sqlite3" if usar_cache else None, consulta=True)
        validar_vectores(vectores, 1, self.estado["dimension"])
        resultado = self.coleccion.query(query_embeddings=vectores, n_results=min(k, self.estado["count"]), include=["documents", "metadatas", "distances"])
        return [{"id": i, "text": t, "metadata": m, "similarity": float(1 - d)} for i, t, m, d in
                zip(resultado["ids"][0], resultado["documents"][0], resultado["metadatas"][0], resultado["distances"][0])]

    def close(self):
        self.cliente.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def cargar_indice(ruta=RUTA_INDICE):
    return IndiceVectorial(ruta)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Componente vectorial; no ejecuta el chatbot")
    parser.add_argument("--construir", action="store_true")
    parser.add_argument("--pregunta")
    args = parser.parse_args()
    if args.construir:
        docs, _ = cargar_documentos()
        print(json.dumps(construir_indice(fragmentar_documentos(docs)), ensure_ascii=True, indent=2))
    elif args.pregunta:
        with cargar_indice() as indice:
            print(json.dumps(indice.buscar(args.pregunta), ensure_ascii=True, indent=2))
    else:
        parser.print_help()
