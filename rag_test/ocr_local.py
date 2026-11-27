"""Transcribe PDFs escaneados con el Qwen local; NO publica texto sin revisar."""

import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
import requests

from .asistente import ROOT
from embeddings import OLLAMA_URL, guardar_json, identidad_modelo

PROMPT_OCR = """Transcribe literalmente TODO el texto visible en esta página de un
documento institucional en español, en orden de lectura. Conserva encabezados,
artículos, parágrafos, listas, tablas, porcentajes, cifras, fechas y negaciones.
No resumas, interpretes ni respondas preguntas. No completes palabras o pasajes
que no puedas leer: marca [ILEGIBLE]. No omitas texto repetido. Devuelve únicamente
la transcripción, sin introducción ni conclusiones."""


def sha(datos):
    return hashlib.sha256(datos).hexdigest()


def transcribir(pdf, salida, dpi=160):
    pdf, salida = Path(pdf).resolve(), Path(salida)
    if dpi < 100 or dpi > 220:
        raise ValueError("Usa entre 100 y 220 DPI para no agotar la memoria local.")
    identidad = identidad_modelo("qwen3.5:9b")
    huella_pdf = sha(pdf.read_bytes())
    salida.mkdir(parents=True, exist_ok=True)
    manifiesto = salida / "origen.json"
    if manifiesto.exists():
        previo = json.loads(manifiesto.read_text(encoding="utf-8"))
        if previo["sha256_pdf"] != huella_pdf or previo["modelo"]["digest"] != identidad["digest"] or previo["dpi"] != dpi:
            raise ValueError("El origen, modelo o DPI cambió; usa una carpeta nueva.")
    with pymupdf.open(pdf) as doc:
        guardar_json(manifiesto, {
            "pdf": str(pdf.relative_to(ROOT)), "sha256_pdf": huella_pdf,
            "paginas": len(doc), "dpi": dpi, "modelo": identidad,
            "fecha": datetime.now(timezone.utc).isoformat(),
            "estado": "borrador_pendiente_revision_visual", "prompt": PROMPT_OCR,
        })
        with requests.Session() as sesion:
            sesion.trust_env = False
            for numero, pagina in enumerate(doc, 1):
                imagen = salida / f"pagina_{numero:03}.png"
                texto = salida / f"pagina_{numero:03}.md"
                registro = salida / f"pagina_{numero:03}.json"
                if registro.exists() and texto.exists():
                    dato = json.loads(registro.read_text(encoding="utf-8"))
                    if dato.get("done_reason") == "stop" and dato.get("sha256_texto") == sha(texto.read_bytes()):
                        print(f"Página {numero}: borrador existente, no se repite.", flush=True)
                        continue
                    raise ValueError(f"Página {numero}: borrador incompleto o editado; revisar antes de continuar.")
                pagina.get_pixmap(dpi=dpi, alpha=False).save(imagen)
                print(f"Transcribiendo página {numero}/{len(doc)}...", flush=True)
                respuesta = sesion.post(OLLAMA_URL + "/api/chat", json={
                    "model": identidad["name"], "stream": False, "think": False,
                    "keep_alive": "10m", "messages": [{"role": "user", "content": PROMPT_OCR,
                        "images": [base64.b64encode(imagen.read_bytes()).decode("ascii")]}],
                    "options": {"temperature": 0, "seed": 42, "num_ctx": 8192,
                                "num_predict": 4096, "presence_penalty": 0},
                }, timeout=900)
                respuesta.raise_for_status()
                dato = respuesta.json()
                if dato.get("error"):
                    raise RuntimeError(dato["error"])
                contenido = dato.get("message", {}).get("content", "").strip()
                if not contenido:
                    raise ValueError(f"Transcripción vacía en página {numero}.")
                texto.write_text(contenido + "\n", encoding="utf-8")
                guardar_json(registro, {**dato, "pagina": numero, "sha256_pdf": huella_pdf,
                    "sha256_imagen": sha(imagen.read_bytes()), "sha256_texto": sha(texto.read_bytes()),
                    "verificado": False})
                print(f"Página {numero}: {len(contenido)} caracteres; fin={dato.get('done_reason')}", flush=True)
                if dato.get("done_reason") != "stop":
                    raise ValueError(f"Página {numero} truncada; NO puede publicarse como evidencia.")
    print(f"Borradores en {salida}. Falta verificación visual; no se modificó el corpus.", flush=True)


def publicar(entrada, revision, salida, fuente_url, titulo):
    """Exige revisión explícita de cada imagen/texto y no reemplaza extracciones."""
    from embeddings import _oficial

    entrada, salida = Path(entrada), Path(salida)
    origen = json.loads((entrada / "origen.json").read_text(encoding="utf-8"))
    aprobacion = json.loads(Path(revision).read_text(encoding="utf-8"))
    if salida.exists() or not _oficial(fuente_url):
        raise ValueError("La salida debe ser nueva y la URL debe ser oficial UTB.")
    pdf = (ROOT / origen["pdf"]).resolve()
    if not pdf.is_relative_to(ROOT / "data") or sha(pdf.read_bytes()) != origen["sha256_pdf"]:
        raise ValueError("El PDF cambió o no pertenece al corpus.")
    if aprobacion.get("tipo_revision") != "visual_IA" or set(aprobacion["paginas"]) != {str(i) for i in range(1, origen["paginas"] + 1)}:
        raise ValueError("Falta revisión visual de alguna página.")
    paginas = []
    for i in range(1, origen["paginas"] + 1):
        dato = aprobacion["paginas"][str(i)]
        imagen, texto = entrada / f"pagina_{i:03}.png", entrada / f"pagina_{i:03}.md"
        registro = json.loads((entrada / f"pagina_{i:03}.json").read_text(encoding="utf-8"))
        if (dato["sha256_texto"] != sha(texto.read_bytes()) or dato["sha256_imagen"] != sha(imagen.read_bytes())
                or registro.get("done_reason") != "stop" or dato.get("verificada") is not True):
            raise ValueError(f"Página {i}: falta revisión o cambió después de revisarla.")
        contenido = texto.read_text(encoding="utf-8")
        for cambio in dato.get("correcciones", []):
            if contenido.count(cambio["antes"]) != 1:
                raise ValueError(f"Página {i}: corrección no unívoca.")
            contenido = contenido.replace(cambio["antes"], cambio["despues"], 1)
        paginas.append({"pagina": i, "texto": contenido.strip(), "needs_ocr": False,
                        "revision_visual": "IA; pendiente consenso humano"})
    guardar_json(salida, {
        "tipo": "pdf", "titulo": titulo, "fuente_url": fuente_url,
        "archivo_origen": origen["pdf"], "sha256_origen": origen["sha256_pdf"],
        "extractor_version": "qwen-vision-revision-visual-v1",
        "extraido_en": datetime.now(timezone.utc).isoformat(),
        "modelo_transcripcion": origen["modelo"], "revision": aprobacion,
        "paginas": paginas,
    })
    print(f"Publicadas {len(paginas)} páginas verificadas visualmente por IA en {salida}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--publicar", type=Path, help="Publica en este JSON, tras revisión visual explícita.")
    parser.add_argument("--revision", type=Path)
    parser.add_argument("--fuente-url")
    parser.add_argument("--titulo")
    args = parser.parse_args()
    if args.publicar:
        if not all((args.revision, args.fuente_url, args.titulo)):
            parser.error("Publicar requiere --revision, --fuente-url y --titulo.")
        publicar(args.salida, args.revision, args.publicar, args.fuente_url, args.titulo)
    else:
        transcribir(args.pdf, args.salida, args.dpi)


if __name__ == "__main__":
    main()
