import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp


SCRIPTS_DIR = Path(__file__).resolve().parent
RAIZ = SCRIPTS_DIR.parent
DATA_DIR = RAIZ / "data"
HTML_DIR = DATA_DIR / "raw" / "html"
DOCS_DIR = DATA_DIR / "raw" / "docs"
MANIFEST = DATA_DIR / "manifest.json"
PAGINAS = DATA_DIR / "pages.json"
CAMBIOS_LOG = DATA_DIR / "changes.log"
SOURCES = DATA_DIR / "sources.txt"

DOMINIO = "utb.edu.co"
EXTENSIONES = (".pdf", ".doc", ".docx", ".xls", ".xlsx")
PAUSA_SEGUNDOS = 3.0
MAX_INTENTOS_DESCARGA = 5
ESTADOS_REINTENTABLES = (429, 500, 502, 503, 504)
TITULOS_VERIFICACION = ("just a moment", "un momento", "attention required", "verificaci")


class ErrorHTTP(Exception):
    def __init__(self, status, url):
        super().__init__(f"HTTP {status} en {url}")
        self.status = status


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
        href = a.get("href")
        if not isinstance(href, str):
            continue
        url = urljoin(pagina_url, href.split("#")[0])
        if es_documento(url) and es_dominio_utb(url):
            enlaces.add(url)
    return sorted(enlaces)


def hay_verificacion(page):
    titulo = page.title().lower()
    html = page.content().lower()
    por_titulo = any(t in titulo for t in TITULOS_VERIFICACION)
    return por_titulo or (len(html) < 30000 and "captcha" in html)


def guardar_pagina(page, url):
    respuesta = page.goto(url, wait_until="domcontentloaded", timeout=60000)
    if hay_verificacion(page):
        input(f"Verificación en {url}. Resuélvela tú en la ventana del navegador y pulsa Enter aquí... ")
        page.wait_for_load_state("domcontentloaded")
        if hay_verificacion(page):
            raise ValueError("la verificación no se completó")
    elif respuesta is not None and respuesta.status >= 400:
        raise ErrorHTTP(respuesta.status, url)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightError:
        pass
    contenido = page.content().encode("utf-8")
    slug = urlparse(url).path.strip("/").replace("/", "_") or "inicio"
    (HTML_DIR / f"{slug}.html").write_bytes(contenido)
    return contenido


def pedir_archivo(contexto, url):
    respuesta = None
    for intento in range(MAX_INTENTOS_DESCARGA):
        respuesta = contexto.request.get(url, timeout=60000)
        if respuesta.status not in ESTADOS_REINTENTABLES or intento == MAX_INTENTOS_DESCARGA - 1:
            break
        espera = 2 ** (intento + 1)
        retry_after = respuesta.headers.get("retry-after")
        if retry_after:
            try:
                espera = max(espera, float(retry_after))
            except ValueError:
                pass
        print(f"  HTTP {respuesta.status}; reintentando en {espera:g} s: {url}")
        time.sleep(espera)
    if respuesta is None:
        raise RuntimeError("no se obtuvo respuesta al descargar el archivo")
    if not respuesta.ok:
        raise ErrorHTTP(respuesta.status, url)
    return respuesta.body()


def descargar_documento(contexto, url, manifest, origen):
    contenido = pedir_archivo(contexto, url)
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


def procesar_fuentes(contexto, page, manifest, paginas, resumen, alertas):
    vistos = set()
    for fuente in leer_fuentes():
        if es_documento(fuente):
            enlaces = [fuente]
        else:
            try:
                contenido = guardar_pagina(page, fuente)
            except (PlaywrightError, ErrorHTTP, ValueError) as e:
                print(f"[error] {fuente}: {e}")
                resumen["error"] += 1
                continue
            enlaces = extraer_enlaces_documentos(fuente, contenido)
            print(f"{fuente} -> {len(enlaces)} documentos encontrados")
            if not enlaces:
                print("  aviso: sin enlaces; revisa data/raw/html/ para ver qué devolvió el sitio")
            enlaces += comparar_pagina(fuente, enlaces, paginas, alertas)
            time.sleep(PAUSA_SEGUNDOS)

        for enlace in enlaces:
            if enlace in vistos:
                continue
            vistos.add(enlace)
            time.sleep(PAUSA_SEGUNDOS)
            try:
                estado = descargar_documento(contexto, enlace, manifest, fuente)
            except ErrorHTTP as e:
                if e.status in (404, 410):
                    estado = "desaparecido"
                    if enlace in manifest:
                        manifest[enlace]["estado"] = "no_disponible"
                        manifest[enlace]["ultima_verificacion"] = ahora()
                    alertas.append(f"documento ya no existe: {enlace}")
                else:
                    estado = "error"
                    print(f"  detalle: {e}")
            except (PlaywrightError, ValueError) as e:
                estado = "error"
                print(f"  detalle: {e}")
            resumen[estado] += 1
            print(f"[{estado}] {enlace}")


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    manifest = cargar_json(MANIFEST)
    paginas = cargar_json(PAGINAS)
    resumen = {"nuevo": 0, "actualizado": 0, "sin cambios": 0, "desaparecido": 0, "error": 0}
    alertas = []

    sb = sb_cdp.Chrome(incognito=True)
    endpoint_url = sb.get_endpoint_url()

    try:
        with sync_playwright() as p:
            navegador = p.chromium.connect_over_cdp(endpoint_url)
            contexto = (
                navegador.contexts[0]
                if navegador.contexts
                else navegador.new_context()
            )
            try:
                page = contexto.pages[0] if contexto.pages else contexto.new_page()
                procesar_fuentes(contexto, page, manifest, paginas, resumen, alertas)
            finally:
                contexto.close()
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