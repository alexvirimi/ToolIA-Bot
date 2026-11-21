import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup

SCRIPTS_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPTS_DIR.parent / "data"
HTML_DIR = DATA_DIR / "raw" / "html"
DOCS_DIR = DATA_DIR / "raw" / "docs"
OUT_DIR = DATA_DIR / "processed"
MANIFEST = DATA_DIR / "manifest.json"
SOURCES = DATA_DIR / "sources.txt"

MIN_CARACTERES = 100
ETIQUETAS_RUIDO = ["script", "style", "noscript", "svg", "nav", "footer", "aside", "form", "iframe"]
ETIQUETAS_TEXTO = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table"]


def cargar_json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def slug_pagina(url):
    path = url.split("://", 1)[-1].split("/", 1)[-1].split("?")[0]
    return path.strip("/").replace("/", "_") or "inicio"


def leer_fuentes():
    lineas = SOURCES.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.strip().startswith("#")]


def limpiar(texto):
    texto = texto.replace("\u00ad", "").replace("\xa0", " ")
    texto = re.sub(r"-\n(?=[a-záéíóúñü])", "", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"^\s*\d{1,3}\s*$", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def pdf_a_paginas(ruta):
    with pymupdf.open(ruta) as doc:
        titulo = (doc.metadata or {}).get("title") or ruta.stem
        paginas = [{"pagina": i, "texto": limpiar(p.get_text())} for i, p in enumerate(doc, start=1)]
    return [p for p in paginas if p["texto"]], titulo


def tabla_a_texto(tabla):
    filas = []
    for tr in tabla.find_all("tr"):
        celdas = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if any(celdas):
            filas.append(" | ".join(celdas))
    return "\n".join(filas)


def html_a_texto(contenido):
    soup = BeautifulSoup(contenido, "html.parser")
    canonico = soup.find("link", rel="canonical")
    url_canonica = canonico["href"] if canonico and canonico.get("href") else ""
    titulo_html = soup.title.get_text(strip=True) if soup.title else ""

    raiz = soup.select_one("main") or soup.select_one("article") or soup.body or soup
    for etiqueta in raiz.find_all(ETIQUETAS_RUIDO):
        etiqueta.decompose()

    h1 = raiz.find("h1")
    titulo = h1.get_text(" ", strip=True) if h1 else titulo_html

    bloques = []
    for el in raiz.find_all(ETIQUETAS_TEXTO):
        if el.name != "table" and el.find_parent("table"):
            continue
        if el.name == "p" and el.find_parent("li"):
            continue
        if el.name == "table":
            texto = tabla_a_texto(el)
        elif el.name == "li":
            for sublista in el.find_all(["ul", "ol"]):
                sublista.extract()
            texto = "- " + el.get_text(" ", strip=True)
        elif el.name == "p":
            texto = el.get_text(" ", strip=True)
        else:
            texto = "#" * int(el.name[1]) + " " + el.get_text(" ", strip=True)
        if texto.strip("- #\n "):
            bloques.append(texto)

    texto = limpiar("\n\n".join(bloques))
    return [{"pagina": None, "texto": texto}] if texto else [], titulo, url_canonica


def procesar(ruta, tipo, url_conocida):
    huella = hashlib.sha256(ruta.read_bytes()).hexdigest()
    salida = OUT_DIR / f"{tipo}_{ruta.stem}.json"
    if salida.exists() and cargar_json(salida).get("sha256_origen") == huella:
        return "sin cambios"

    if tipo == "pdf":
        paginas, titulo = pdf_a_paginas(ruta)
        url = url_conocida
    else:
        paginas, titulo, canonica = html_a_texto(ruta.read_bytes())
        url = url_conocida or canonica

    if sum(len(p["texto"]) for p in paginas) < MIN_CARACTERES:
        return "sin texto"

    salida.write_text(
        json.dumps(
            {
                "tipo": tipo,
                "titulo": titulo,
                "fuente_url": url,
                "archivo_origen": str(ruta.relative_to(DATA_DIR.parent)),
                "sha256_origen": huella,
                "extraido_en": datetime.now(timezone.utc).isoformat(),
                "paginas": paginas,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return "extraido"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = cargar_json(MANIFEST)
    url_por_archivo = {d["archivo"]: url for url, d in manifest.items()}
    url_por_slug = {slug_pagina(u): u for u in leer_fuentes()}

    tareas = [(r, "pdf", url_por_archivo.get(r.name, "")) for r in sorted(DOCS_DIR.glob("*.pdf"))]
    tareas += [(r, "html", url_por_slug.get(r.stem, "")) for r in sorted(HTML_DIR.glob("*.html"))]
    omitidos = [r.name for r in DOCS_DIR.iterdir() if r.suffix.lower() != ".pdf"] if DOCS_DIR.exists() else []

    resumen = {"extraido": 0, "sin cambios": 0, "sin texto": 0, "error": 0}
    for ruta, tipo, url in tareas:
        try:
            estado = procesar(ruta, tipo, url)
        except Exception as e:
            estado = "error"
            print(f"  detalle: {ruta.name}: {e}")
        resumen[estado] += 1
        print(f"[{estado}] {tipo}: {ruta.name}")

    if omitidos:
        print("Omitidos (formato no soportado):", ", ".join(omitidos))
    print("Resumen:", resumen)
    return 1 if resumen["error"] else 0


if __name__ == "__main__":
    sys.exit(main())