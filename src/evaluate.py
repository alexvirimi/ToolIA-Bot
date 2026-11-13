"""
Calcula las métricas de la línea base a partir de respuestas.csv, después
de llenar a mano la columna 'etiqueta' con alguna de estas opciones:
    correcta | parcial | incorrecta | alucinacion | abstencion
"""
import json
from pathlib import Path

import pandas as pd
from statsmodels.stats.proportion import proportion_confint

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "experiments" / "baseline"
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
        "ic95_inf_%": round(bajo * 100, 1), # límite inferior del intervalo de confianza al 95%
        "ic95_sup_%": round(alto * 100, 1), # límite superior del intervalo de confianza al 95%
    }

def main():
    df = pd.read_csv(DIR / "respuestas.csv", encoding="utf-8-sig")
    df["etiqueta"] = df["etiqueta"].astype(str).fillna("").str.strip().str.lower()

    sin_etiqueta = df[df["etiqueta"] == ""]
    invalidas = df[(df["etiqueta"] != "") & (~df["etiqueta"].isin(VALIDAS))]
    if len(sin_etiqueta):
        print(f"Faltan {len(sin_etiqueta)} respuestas por etiquetar: "
              f"{sin_etiqueta['id'].tolist()}")
        return
    if len(invalidas):
        print("Etiquetas no validas en ids:", invalidas["id"].tolist())
        return

    con = df[df["tiene_respuesta"] == "si"]
    sin = df[df["tiene_respuesta"] == "no"]

    metricas = {
        "n_total": int(len(df)),
        "n_con_respuesta": int(len(con)),
        "n_sin_respuesta": int(len(sin)),
        # Preguntas con respuesta: exactitud, exactitud con parciales, tasa de alucinación
        "exactitud_%": round((con["etiqueta"] == "correcta").mean() * 100, 1),
        "exactitud_con_parciales_%": round(
            con["etiqueta"].isin(["correcta", "parcial"]).mean() * 100, 1),
        "tasa_alucinacion_%": round(
            (df["etiqueta"] == "alucinacion").mean() * 100, 1),
        # Preguntas sin respuesta: tasa de abstención
        "tasa_abstencion_%": round(
            (sin["etiqueta"] == "abstencion").mean() * 100, 1),
        "latencia_promedio_s": round(df["latencia_s"].mean(), 2),
        "latencia_max_s": round(df["latencia_s"].max(), 2),
        "conteo_etiquetas": df["etiqueta"].value_counts().to_dict(),
        "exactitud_por_categoria_%": (
            con.groupby("categoria")["etiqueta"]
            .apply(lambda s: round((s == "correcta").mean() * 100, 1))
            .to_dict()
        ),
    }
    (DIR / "metricas.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metricas, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
