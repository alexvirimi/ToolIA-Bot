import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SCRIPTS_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPTS_DIR.parent / "data"
HTML_DIR = DATA_DIR / "raw" / "html"
DOCS_DIR = DATA_DIR / "raw" / "docs"
MANIFEST = DATA_DIR / "manifest.json"
PAGINAS = DATA_DIR / "pages.json"
CAMBIOS_LOG = DATA_DIR / "changes.log"
SOURCES = SCRIPTS_DIR / "sources.txt"

DOMINIO = "utb.edu.co"
EXTENSIONES = (".pdf", ".doc", ".docx", ".xls", ".xlsx")
PAUSA_SEGUNDOS = 1.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}


def crear_sesion():
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    reintentos = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    sesion.mount("https://", HTTPAdapter(max_retries=reintentos))
    sesion.mount("http://", HTTPAdapter(max_retries=reintentos))
    return sesion


def es_dominio_utb(url):
    host = urlparse(url).hostname or ""
    return host == DOMINIO or host.endswith("." + DOMINIO)


def es_documento(url):
    return urlparse(url).path.lower().endswith(EXTENSIONES)


def leer_fuentes():
    lineas = SOURCES.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.strip().startswith("#")]


def cargar_json(ruta):
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    return {}


def guardar_json(ruta, datos):
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")


def ahora():
    return datetime.now(timezone.utc).isoformat()


def nombre_archivo(url, manifest):
    nombre = re.sub(r"[^\w.\-]+", "_", unquote(Path(urlparse(url).path).name))
    usado_por = [u for u, d in manifest.items() if d["archivo"] == nombre and u != url]
    if usado_por:
        nombre = hashlib.sha1(url.encode()).hexdigest()[:8] + "_" + nombre
    return nombre


def extraer_enlaces_documentos(pagina_url, contenido):
    soup = BeautifulSoup(contenido, "html.parser")
    enlaces = set()
    for a in soup.find_all("a", href=True):
        url = urljoin(pagina_url, a["href"].split("#")[0])
        if es_documento(url) and es_dominio_utb(url):
            enlaces.add(url)
    return sorted(enlaces)


def guardar_pagina(sesion, url):
    r = sesion.get(url, timeout=30)
    r.raise_for_status()
    slug = urlparse(url).path.strip("/").replace("/", "_") or "inicio"
    (HTML_DIR / f"{slug}.html").write_bytes(r.content)
    return r.content


def descargar_documento(sesion, url, manifest, origen):
    r = sesion.get(url, timeout=60)
    r.raise_for_status()
    contenido = r.content
    if url.lower().endswith(".pdf") and not contenido.startswith(b"%PDF"):
        raise ValueError("la respuesta no es un PDF (posible bloqueo del sitio)")

    huella = hashlib.sha256(contenido).hexdigest()
    previo = manifest.get(url)
    if previo and previo["sha256"] == huella and (DOCS_DIR / previo["archivo"]).exists():
        previo["estado"] = "ok"
        previo["ultima_verificacion"] = ahora()
        return "sin cambios"

    nombre = previo["archivo"] if previo else nombre_archivo(url, manifest)
    (DOCS_DIR / nombre).write_bytes(contenido)
    manifest[url] = {
        "archivo": nombre,
        "sha256": huella,
        "bytes": len(contenido),
        "pagina_origen": origen,
        "estado": "ok",
        "descargado_en": ahora(),
        "ultima_verificacion": ahora(),
    }
    return "nuevo" if previo is None else "actualizado"


def comparar_pagina(fuente, enlaces, paginas, alertas):
    previos = set(paginas.get(fuente, []))
    actuales = set(enlaces)
    if not actuales:
        if previos:
            alertas.append(f"{fuente}: sin enlaces (¿captcha o cambio de estructura?); no se comparó")
        return []
    ausentes = []
    if previos:
        for url in sorted(actuales - previos):
            alertas.append(f"enlace nuevo en {fuente}: {url}")
        ausentes = sorted(previos - actuales)
        for url in ausentes:
            alertas.append(f"enlace que ya no aparece en {fuente}: {url}")
    paginas[fuente] = sorted(actuales)
    return ausentes


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    manifest = cargar_json(MANIFEST)
    paginas = cargar_json(PAGINAS)
    sesion = crear_sesion()
    resumen = {"nuevo": 0, "actualizado": 0, "sin cambios": 0, "desaparecido": 0, "error": 0}
    vistos = set()
    alertas = []

    try:
        for fuente in leer_fuentes():
            if es_documento(fuente):
                enlaces = [fuente]
            else:
                try:
                    contenido = guardar_pagina(sesion, fuente)
                except requests.RequestException as e:
                    print(f"[error] {fuente}: {e}")
                    resumen["error"] += 1
                    continue
                enlaces = extraer_enlaces_documentos(fuente, contenido)
                print(f"{fuente} -> {len(enlaces)} documentos encontrados")
                if not enlaces:
                    print("  aviso: sin enlaces; revisa data/raw/html/ para ver qué devolvió el sitio")
                enlaces += comparar_pagina(fuente, enlaces, paginas, alertas)

            for enlace in enlaces:
                if enlace in vistos:
                    continue
                vistos.add(enlace)
                time.sleep(PAUSA_SEGUNDOS)
                try:
                    estado = descargar_documento(sesion, enlace, manifest, fuente)
                except requests.HTTPError as e:
                    if e.response is not None and e.response.status_code in (404, 410):
                        estado = "desaparecido"
                        if enlace in manifest:
                            manifest[enlace]["estado"] = "no_disponible"
                            manifest[enlace]["ultima_verificacion"] = ahora()
                        alertas.append(f"documento ya no existe: {enlace}")
                    else:
                        estado = "error"
                        print(f"  detalle: {e}")
                except (requests.RequestException, ValueError) as e:
                    estado = "error"
                    print(f"  detalle: {e}")
                resumen[estado] += 1
                print(f"[{estado}] {enlace}")
    finally:
        guardar_json(MANIFEST, manifest)
        guardar_json(PAGINAS, paginas)

    for linea in alertas:
        print("ALERTA:", linea)
    if alertas or resumen["nuevo"] or resumen["actualizado"]:
        with CAMBIOS_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{ahora()} {resumen}\n")
            f.writelines(f"  {linea}\n" for linea in alertas)

    print("Resumen:", resumen)
    return 1 if resumen["error"] or resumen["desaparecido"] else 0


if __name__ == "__main__":
    sys.exit(main())
