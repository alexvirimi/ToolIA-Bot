import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp


DOMINIO = "utb.edu.co"
SITEMAP_URL = f"https://www.{DOMINIO}/sitemap.xml"
SOURCES = Path(__file__).with_name("sources.txt")


def es_dominio_utb(url):
    host = urlparse(url).hostname or ""
    return host == DOMINIO or host.endswith("." + DOMINIO)


def extraer_urls_sitemap(contenido):
    raiz = ET.fromstring(contenido)
    urls = {
        texto
        for elemento in raiz.iter()
        if elemento.tag.endswith("loc")
        and (texto := (elemento.text or "").strip())
        and es_dominio_utb(texto)
    }
    return sorted(urls)


def guardar_sources(urls):
    SOURCES.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")


def main():
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
                respuesta = page.goto(SITEMAP_URL, wait_until="domcontentloaded", timeout=60000)
                if respuesta is None:
                    raise RuntimeError(f"no se obtuvo respuesta de {SITEMAP_URL}")

                sb.solve_captcha()
                page.wait_for_timeout(1500)
                urls = extraer_urls_sitemap(page.content())
            finally:
                contexto.close()
    finally:
        sb.driver.quit()

    guardar_sources(urls)
    print(f"{len(urls)} URLs guardadas en {SOURCES}")


if __name__ == "__main__":
    main()
