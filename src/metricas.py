"""Funciones de métricas compartidas por línea base y RAG."""
from statsmodels.stats.proportion import proportion_confint
import pandas as pd

VALIDAS = {"correcta", "parcial", "incorrecta",
           "alucinacion", "abstencion", "abstencion_fallo"}

DISPONIBILIDAD_VALIDA = {"si", "parcial", "no"}


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
    df = pd.read_csv(ruta, encoding="utf-8-sig",
                     dtype=str, keep_default_na=False)
    df["etiqueta"] = df["etiqueta"].str.strip().str.lower()
    df["tiene_respuesta"] = df["tiene_respuesta"].str.strip().str.lower()
    df["latencia_s"] = pd.to_numeric(df["latencia_s"], errors="coerce")
    return df


def validar_etiquetas(df):
    """Devuelve un mensaje de error si hay etiquetas vacías o inválidas; None si todo está bien."""
    vacias = df[df["etiqueta"] == ""]["id"].tolist()
    invalidas = df[(df["etiqueta"] != "") & ~
                   df["etiqueta"].isin(VALIDAS)]["id"].tolist()

    disponibilidad_invalida = df[
        ~df["tiene_respuesta"].isin(DISPONIBILIDAD_VALIDA)
    ]["id"].tolist()

    if vacias:
        return f"Faltan {len(vacias)} respuestas por etiquetar: {vacias}"
    if invalidas:
        return f"Etiquetas no válidas en ids: {invalidas}"
    if disponibilidad_invalida:
        return (
            "Disponibilidad documental no válida en ids: "
            f"{disponibilidad_invalida}"
        )
    return None


def _pct(condicion):
    return round(condicion.mean() * 100, 1) if len(condicion) else None


def calcular(df):
    """Métricas comunes."""
    con = df[df["tiene_respuesta"].isin(["si", "parcial"])]
    # Información documental completamente disponible
    con_total = df[df["tiene_respuesta"] == "si"]
    # Información documental parcialmente disponible
    con_parcial = df[df["tiene_respuesta"] == "parcial"]
    sin = df[df["tiene_respuesta"] == "no"]

    # Abstenciones
    abstenciones = df["etiqueta"].isin([
        "abstencion",
        "abstencion_fallo"
    ])
    # Abstenciones cuando no existe información
    abstencion = sin["etiqueta"] == "abstencion"
    # Abstenciones cuando sí existe información
    abstencion_fallo = con["etiqueta"] == "abstencion_fallo"

    return {
        "n_total": int(len(df)),
        "n_con_respuesta": int(len(con)),
        "n_con_respuesta_total": int(len(con_total)),
        "n_con_respuesta_parcial": int(len(con_parcial)),
        "n_sin_respuesta": int(len(sin)),

        # Exactitud preguntas con información
        "exactitud_%": _pct(con["etiqueta"] == "correcta"),
        "exactitud_con_parciales_%": _pct(con["etiqueta"].isin(["correcta", "parcial"])),

        # Alucinaciones sobre todas las preguntas
        "tasa_alucinacion_%": _pct(df["etiqueta"] == "alucinacion"),
        # Abstención total sobre todas las preguntas
        "tasa_abstencion_total_%": _pct(abstenciones),
        # Abstención adecuada: preguntas sin información
        "tasa_abstencion_adecuada_%": _pct(abstencion),
        # Abstención incorrecta: existe información disponible
        "tasa_abstencion_fallo_%": _pct(
            abstencion_fallo
        ),

        # Latencia
        "latencia_promedio_s": round(df["latencia_s"].mean(), 2),
        "latencia_max_s": round(df["latencia_s"].max(), 2),

        # Conteo de etiquetas
        "conteo_etiquetas": df["etiqueta"].value_counts().to_dict(),

        # Exactitud por categoria
        "exactitud_por_categoria_%": (
            con.groupby("categoria")["etiqueta"]
            .apply(lambda s: round(s.isin(["correcta", "parcial"]).mean() * 100, 1)).to_dict()),

        # Intervalos de confianza
        "exactitud_ic": proporcion((con["etiqueta"] == "correcta").sum(), len(con)),
        "alucinacion_ic": proporcion((df["etiqueta"] == "alucinacion").sum(), len(df)),
        "abstencion_ic": proporcion((sin["etiqueta"] == "abstencion").sum(), len(sin)),
        "abstencion_fallo_ic": proporcion((con["etiqueta"] == "abstencion_fallo").sum(), len(con)),
    }
