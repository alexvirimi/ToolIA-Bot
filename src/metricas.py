"""Funciones de métricas compartidas por línea base y RAG."""
from statsmodels.stats.proportion import proportion_confint
import pandas as pd

VALIDAS = {"correcta", "parcial", "incorrecta", "alucinacion", "abstencion"}


def proporcion(aciertos: int, total: int) -> dict:
    """Devuelve porcentaje, conteo e intervalo de confianza 95% (Wilson)."""
    if total == 0:
        return {"valor_%": None, "aciertos": 0, "total": 0,
                "ic95_inf_%": None, "ic95_sup_%": None}
    bajo, alto = proportion_confint(aciertos, total, method="wilson")
    return {
        "valor_%": round(aciertos / total * 100, 1),
        "aciertos": int(aciertos),
        "total": int(total),
        # límite inferior del intervalo de confianza al 95%
        "ic95_inf_%": round(bajo * 100, 1),
        # límite superior del intervalo de confianza al 95%
        "ic95_sup_%": round(alto * 100, 1),
    }

def cargar_respuestas(ruta):
    """Lee respuestas.csv todo como texto (sin que un vacío se vuelva 'nan') y normaliza."""
    df = pd.read_csv(ruta, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df["etiqueta"] = df["etiqueta"].str.strip().str.lower()
    df["tiene_respuesta"] = df["tiene_respuesta"].str.strip().str.lower()
    df["latencia_s"] = pd.to_numeric(df["latencia_s"], errors="coerce")
    return df

def validar_etiquetas(df):
    """Devuelve un mensaje de error si hay etiquetas vacías o inválidas; None si todo está bien."""
    vacias = df[df["etiqueta"] == ""]["id"].tolist()
    invalidas = df[(df["etiqueta"] != "") & ~df["etiqueta"].isin(VALIDAS)]["id"].tolist()
    if vacias:
        return f"Faltan {len(vacias)} respuestas por etiquetar: {vacias}"
    if invalidas:
        return f"Etiquetas no válidas en ids: {invalidas}"
    return None

def _pct(condicion):
    return round(condicion.mean() * 100, 1) if len(condicion) else None

def calcular(df):
    """Métricas comunes."""
    con = df[df["tiene_respuesta"] == "si"]
    sin = df[df["tiene_respuesta"] == "no"]
    return {
        "n_total": int(len(df)),
        "n_con_respuesta": int(len(con)),
        "n_sin_respuesta": int(len(sin)),
        # Preguntas con respuesta
        "exactitud_%": _pct(con["etiqueta"] == "correcta"),
        "exactitud_con_parciales_%": _pct(con["etiqueta"].isin(["correcta", "parcial"])),
        # Sobre todas las preguntas
        "tasa_alucinacion_%": _pct(df["etiqueta"] == "alucinacion"),
        # Preguntas sin respuesta
        "tasa_abstencion_%": _pct(sin["etiqueta"] == "abstencion"),
        "latencia_promedio_s": round(df["latencia_s"].mean(), 2),
        "latencia_max_s": round(df["latencia_s"].max(), 2),
        "conteo_etiquetas": df["etiqueta"].value_counts().to_dict(),
        "exactitud_por_categoria_%": (
            con.groupby("categoria")["etiqueta"]
            .apply(lambda s: round((s == "correcta").mean() * 100, 1)).to_dict()),
        "exactitud_ic": proporcion((con["etiqueta"] == "correcta").sum(), len(con)),
        "alucinacion_ic": proporcion((df["etiqueta"] == "alucinacion").sum(), len(df)),
        "abstencion_ic": proporcion((sin["etiqueta"] == "abstencion").sum(), len(sin)),
    }