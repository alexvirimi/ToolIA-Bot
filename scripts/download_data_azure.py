"""Descarga las fuentes de la UTB en un trabajo programado de Azure."""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from portalocker import Lock
from portalocker.exceptions import AlreadyLocked


RAIZ = Path(__file__).resolve().parent.parent
SOURCES = RAIZ / "data" / "sources.txt"

DOMINIO = "utb.edu.co"
EXTENSIONES = (".pdf", ".doc", ".docx", ".xls", ".xlsx")
PAUSA_SEGUNDOS = 3.0
MAX_INTENTOS_DESCARGA = 5
ESTADOS_REINTENTABLES = (429, 500, 502, 503, 504)
TITULOS_VERIFICACION = ("just a moment", "un momento", "attention required", "verificación de seguridad")


class ErrorHTTP(Exception):
    def __init__(self, status, url):
        super().__init__(f"HTTP {status} en {url}")
        self.status = status


def es_dominio_utb(url):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return parsed.scheme in ("http", "https") and (host == DOMINIO or host.endswith("." + DOMINIO))


def es_documento(url):
    return urlparse(url).path.lower().endswith(EXTENSIONES)


def leer_fuentes():
    lineas = SOURCES.read_text(encoding="utf-8").splitlines()
    return [linea for texto in lineas if (linea := texto.strip()) and not linea.startswith("#")]


def cargar_json(ruta):
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    return {}


def guardar_archivo(ruta, contenido):
    # El temporal debe estar en el mismo volumen para reemplazar el archivo de una vez.
    temporal = NamedTemporaryFile(dir=ruta.parent, suffix=".tmp", delete=False)
    ruta_temporal = Path(temporal.name)
    try:
        with temporal:
            temporal.write(contenido)
        ruta_temporal.replace(ruta)
    finally:
        ruta_temporal.unlink(missing_ok=True)


def guardar_json(ruta, datos):
    guardar_archivo(ruta, json.dumps(datos, indent=2, ensure_ascii=False).encode("utf-8"))


def ahora():
    return datetime.now(timezone.utc).isoformat()


def nombre_archivo(url, manifest):
    nombre = re.sub(r"[^\w.\-]+", "_", unquote(Path(urlparse(url).path).name))
    if any(d["archivo"].casefold() == nombre.casefold() for d in manifest.values()):
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


def hay_verificacion(page, html):
    titulo = page.title().strip().lower()
    html = html.lower()
    return (
        titulo.startswith(TITULOS_VERIFICACION)
        or "window._cf_chl_opt" in html
        or (len(html) < 30000 and "captcha" in html)
    )


def guardar_pagina(page, url, html_dir):
    respuesta = page.goto(url, wait_until="domcontentloaded", timeout=60000)
    status = respuesta.status if respuesta is not None else 0
    if status < 400:
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightError:
            pass
    if not es_dominio_utb(page.url):
        raise ValueError(f"redirección fuera de la UTB: {page.url}")

    html = page.content()
    if hay_verificacion(page, html):
        raise ValueError("la página requiere verificación; se conserva la última copia válida")
    if status >= 400:
        raise ErrorHTTP(status, url)

    contenido = html.encode("utf-8")
    slug = urlparse(url).path.strip("/").replace("/", "_") or "inicio"
    guardar_archivo(html_dir / f"{slug}.html", contenido)
    return contenido


def pedir_archivo(contexto, url):
    for intento in range(MAX_INTENTOS_DESCARGA):
        respuesta = contexto.request.get(url, timeout=60000)
        try:
            if not es_dominio_utb(respuesta.url):
                raise ValueError(f"redirección fuera de la UTB: {respuesta.url}")
            if respuesta.ok:
                if "text/html" in respuesta.headers.get("content-type", "").lower():
                    raise ValueError("se recibió una página HTML en lugar del documento")
                return respuesta.body()
            status = respuesta.status
            retry_after = respuesta.headers.get("retry-after")
        finally:
            respuesta.dispose()

        if status not in ESTADOS_REINTENTABLES or intento == MAX_INTENTOS_DESCARGA - 1:
            raise ErrorHTTP(status, url)
        espera = 2 ** (intento + 1)
        if retry_after:
            try:
                espera = max(espera, float(retry_after))
            except ValueError:
                pass
        if espera > 60:
            raise ErrorHTTP(status, url)
        print(f"  HTTP {status}; reintentando en {espera:g} s: {url}")
        time.sleep(espera)


def descargar_documento(contexto, url, manifest, origen, docs_dir):
    contenido = pedir_archivo(contexto, url)
    if urlparse(url).path.lower().endswith(".pdf") and not contenido.startswith(b"%PDF"):
        raise ValueError("la respuesta no es un PDF (posible bloqueo del sitio)")

    huella = hashlib.sha256(contenido).hexdigest()
    previo = manifest.get(url)
    nombre = previo["archivo"] if previo else nombre_archivo(url, manifest)
    ruta = docs_dir / nombre
    if previo and previo["sha256"] == huella and ruta.exists():
        with ruta.open("rb") as archivo:
            huella_local = hashlib.file_digest(archivo, "sha256").hexdigest()
        if huella_local == huella:
            previo["estado"] = "ok"
            previo["ultima_verificacion"] = ahora()
            return "sin cambios"

    guardar_archivo(ruta, contenido)
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


def procesar_documentos(contexto, enlaces, vistos, manifest, fuente, docs_dir, resumen, alertas):
    for enlace in enlaces:
        if enlace in vistos:
            continue
        vistos.add(enlace)
        time.sleep(PAUSA_SEGUNDOS)
        try:
            estado = descargar_documento(contexto, enlace, manifest, fuente, docs_dir)
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


def procesar_fuentes(contexto, fuentes, data_dir, resumen, alertas):
    html_dir = data_dir / "raw" / "html"
    docs_dir = data_dir / "raw" / "docs"
    html_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    ruta_manifest = data_dir / "manifest.json"
    ruta_paginas = data_dir / "pages.json"
    manifest = cargar_json(ruta_manifest)
    paginas = cargar_json(ruta_paginas)
    vistos = set()
    page = contexto.new_page()

    for fuente in fuentes:
        if es_documento(fuente):
            enlaces = [fuente]
        else:
            time.sleep(PAUSA_SEGUNDOS)
            try:
                contenido = guardar_pagina(page, fuente, html_dir)
            except (PlaywrightError, ErrorHTTP, ValueError) as e:
                print(f"[error] {fuente}: {e}")
                resumen["error"] += 1
                continue
            enlaces = extraer_enlaces_documentos(page.url, contenido)
            print(f"{fuente} -> {len(enlaces)} documentos encontrados")
            enlaces += comparar_pagina(fuente, enlaces, paginas, alertas)

        procesar_documentos(contexto, enlaces, vistos, manifest, fuente, docs_dir, resumen, alertas)
        guardar_json(ruta_manifest, manifest)
        guardar_json(ruta_paginas, paginas)


def descargar_fuentes(fuentes, data_dir):
    resumen = {"nuevo": 0, "actualizado": 0, "sin cambios": 0, "desaparecido": 0, "error": 0}
    alertas = []

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=True)
        try:
            contexto = navegador.new_context()
            procesar_fuentes(contexto, fuentes, data_dir, resumen, alertas)
        finally:
            navegador.close()

    for linea in alertas:
        print("ALERTA:", linea)
    if alertas or resumen["nuevo"] or resumen["actualizado"]:
        with (data_dir / "changes.log").open("a", encoding="utf-8") as archivo:
            archivo.write(f"{ahora()} {resumen}\n")
            archivo.writelines(f"  {linea}\n" for linea in alertas)

    print("Resumen:", resumen)
    return 1 if resumen["error"] or resumen["desaparecido"] else 0


def main():
    destino = os.environ.get("TOOLIA_DATA_DIR")
    if not destino:
        print("Define TOOLIA_DATA_DIR con la ruta de salida.", file=sys.stderr)
        return 2
    data_dir = Path(destino).resolve()
    if data_dir == SOURCES.parent:
        print("Usa un directorio de salida distinto de data/.", file=sys.stderr)
        return 2

    fuentes = leer_fuentes()
    if not fuentes or any(not es_dominio_utb(fuente) for fuente in fuentes):
        print(f"{SOURCES} debe contener fuentes válidas de la UTB.", file=sys.stderr)
        return 2

    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        with Lock(data_dir / ".download.lock", timeout=0):
            print(f"Descargando {len(fuentes)} fuentes de la UTB en {data_dir}")
            return descargar_fuentes(fuentes, data_dir)
    except AlreadyLocked:
        print("Ya hay una ejecución usando el directorio de salida.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
