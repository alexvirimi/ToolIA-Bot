"""
Actualiza un respuestas.csv VIEJO del RAG a la estructura nueva de
run_rag_exp.py, SIN volver a ejecutar el modelo y SIN perder etiquetas.

Usa recuperacion.jsonl (los fragmentos que el RAG ya recupero en esa corrida)
para llenar 'fuentes_recuperadas' y 'recall_auto'.

Que hace:
  * Agrega fuente_url y pagina_o_seccion (de data/preguntas.csv) si faltan o
    estan vacias; nunca cambia una celda que ya tenga datos.
  * Agrega 'fuentes_recuperadas' (top-K en orden de ranking).
  * Llena 'recall_auto' SOLO donde esta vacio (no pisa lo que hayas revisado).
  * Elimina 'fuente_esperada' (lo unico que se borra).
  * Reordena las columnas como run_rag_exp.py.
  * Copia de seguridad con fecha en backups/ y verificacion antes de escribir.

Uso (desde la raiz del proyecto):
    python src/migrar_respuestas.py experiments/rag
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from csv_seguro import guardar_seguro, leer

ROOT = Path(__file__).resolve().parents[1]
PREGUNTAS_CSV = ROOT / "data" / "preguntas.csv"

COLUMNAS = [
    "id", "categoria", "tiene_respuesta", "pregunta", "respuesta_referencia",
    "fuente_url", "pagina_o_seccion",
    "respuesta_modelo", "latencia_s", "latencia_recuperacion_s",
    "abstencion_auto", "mejor_similitud",
    "fuentes_recuperadas", "fuentes_citadas", "recall_auto",
    "error", "etiqueta", "fidelidad", "observaciones",
]


# --- Mismas funciones que run_rag_exp.py (mantener iguales) ------------------
def clave_documento(texto) -> str:
    t = unquote(str(texto)).strip().lower()
    t = re.sub(r"^\[\d+\]\s*", "", t)
    m = re.search(r"([^\s/\\|;,'\"()\[\]]+)\.(pdf|html?|docx?)", t)
    if m:
        t = m.group(1)
    else:
        t = re.sub(r"\s+p\.?\s*\d+(\s*[-–]\s*\d+)?\s*$", "", t)
        t = re.split(r"[\\/]", t.split("?")[0].split("#")[0].rstrip("/\\"))[-1]
    return re.sub(r"[^a-z0-9]+", "", t)


def recall_auto(fuente_url, tiene_respuesta, fragmentos):
    if tiene_respuesta != "si":
        return ""
    esperadas = [clave_documento(u) for u in str(fuente_url or "").split("|") if u.strip()]
    if not esperadas:
        return ""
    recuperadas = set()
    for f in fragmentos:
        m = f.get("metadata", {})
        for campo in ("file", "title", "source_url"):
            if m.get(campo):
                recuperadas.add(clave_documento(m[campo]))
    return "si" if all(e in recuperadas for e in esperadas) else "no"


def fuentes_recuperadas(fragmentos):
    partes = []
    for i, f in enumerate(fragmentos, start=1):
        m = f.get("metadata", {})
        nombre = m.get("file") or m.get("title") or m.get("source_url") or "desconocido"
        pagina = m.get("page") or m.get("pagina") or f.get("pagina") or ""
        partes.append(f"[{i}] {nombre}" + (f" p.{pagina}" if pagina else ""))
    return "; ".join(partes)

def main():
    if len(sys.argv) != 2:
        print("Uso: python src/migrar_respuestas.py experiments/rag")
        return
    carpeta = Path(sys.argv[1])
    if not carpeta.is_absolute():
        carpeta = ROOT / carpeta
    ruta, jsonl = carpeta / "respuestas.csv", carpeta / "recuperacion.jsonl"
    if not ruta.exists() or not jsonl.exists():
        print("Faltan respuestas.csv o recuperacion.jsonl en", carpeta)
        return

    orig = leer(ruta)
    preg = leer(PREGUNTAS_CSV).drop_duplicates(subset="id").set_index("id")
    frag = {}
    for linea in jsonl.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            d = json.loads(linea)
            frag[str(d["id"])] = d["fragmentos"]          # si se repite, gana el ultimo

    nuevo = orig.copy()

    # fuente_url / pagina_o_seccion: crear o llenar solo vacias
    for c in ("fuente_url", "pagina_o_seccion"):
        mapa = nuevo["id"].map(preg[c]).fillna("")
        if c not in nuevo.columns:
            nuevo[c] = mapa
        else:
            vac = nuevo[c] == ""
            nuevo.loc[vac, c] = mapa[vac]

    # fuentes_recuperadas: solo si no existe
    if "fuentes_recuperadas" not in nuevo.columns:
        nuevo["fuentes_recuperadas"] = nuevo["id"].map(
            lambda i: fuentes_recuperadas(frag[i]) if i in frag else "")

    # recall_auto: crear o llenar solo vacias
    calc = [recall_auto(r.fuente_url, r.tiene_respuesta, frag[r.id]) if r.id in frag else ""
            for r in nuevo.itertuples()]
    if "recall_auto" not in nuevo.columns:
        nuevo["recall_auto"] = calc
    else:
        actual = nuevo["recall_auto"].tolist()
        nuevo["recall_auto"] = [calc[i] if actual[i] == "" else actual[i]
                                for i in range(len(actual))]

    quitar = set()
    if "fuente_esperada" in nuevo.columns:
        nuevo = nuevo.drop(columns=["fuente_esperada"])
        quitar.add("fuente_esperada")

    # Orden de columnas como run_rag_exp.py (las desconocidas, al final)
    orden = [c for c in COLUMNAS if c in nuevo.columns] + \
            [c for c in nuevo.columns if c not in COLUMNAS]
    nuevo = nuevo[orden]

    solo_vacias = {"fuente_url", "pagina_o_seccion", "recall_auto"} & set(orig.columns)
    respaldo = guardar_seguro(orig, nuevo, ruta, quitar=quitar, solo_vacias=solo_vacias)
    if not respaldo:
        return

    ev = nuevo[nuevo["recall_auto"] != ""]
    print(f"Listo. Copia de seguridad: {respaldo}")
    print(f"Filas sin fragmentos en el jsonl: {int((~nuevo['id'].isin(frag.keys())).sum())}")
    if len(ev):
        n_si = int((ev["recall_auto"] == "si").sum())
        print(f"recall_auto = si en {n_si} de {len(ev)} preguntas con respuesta "
              f"({n_si/len(ev):.1%})")
        print("Ids con recall_auto = no:", ev[ev["recall_auto"] == "no"]["id"].tolist())
    print("Ahora ejecuta: python src/verificar_integridad.py", ruta.relative_to(ROOT)
          if ruta.is_relative_to(ROOT) else ruta)


if __name__ == "__main__":
    main()