"""
Calcula las métricas de RAG para comparar con la línea base a partir de respuestas.csv, 
después de llenar manualmente las columnas necesarias (etiqueta y fidelidad).

Ejemplos de uso:
    python src/rag/evaluate_rag.py                  # experiments/rag vs experiments/baseline
    python src/rag/evaluate_rag.py --nombre rag_u055
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from metricas import calcular, cargar_respuestas, proporcion, validar_etiquetas


DIR = ROOT / "experiments"

# Umbrales de éxito de la propuesta
U_EXACTITUD, U_DELTA_EXACTITUD = 75.0, 15.0
U_FIDELIDAD, U_ALUCINACION = 80.0, 15.0
U_ABSTENCION, U_LATENCIA, U_RECALL = 70.0, 10.0, 80.0


def cargar(nombre):
    ruta = DIR / nombre / "respuestas.csv"
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}")
    df = cargar_respuestas(ruta)
    error = validar_etiquetas(df)
    if error:
        raise SystemExit(f"[{nombre}] {error}")
    return df


def calcular_rag(df):
    m = calcular(df)
    # Fidelidad: respuestas no abstenidas respaldadas por los fragmentos
    if "fidelidad" in df.columns:
        resp = df[~df["etiqueta"].isin(["abstencion", "abstencion_fallo"])]
        marca = resp["fidelidad"].str.strip().str.lower()
        pendientes = int((~marca.isin(["si", "no"])).sum())
        if len(resp) and pendientes == 0:
            m["fidelidad_ic"] = proporcion((marca == "si").sum(), len(resp))
        else:
            m["fidelidad_ic"] = {"valor_%": None,
                                 "nota": f"faltan {pendientes} filas por marcar"}

    # Recall@5: la fuente esperada aparece entre los fragmentos recuperados
    if "recall_auto" in df:
        r = df[df["tiene_respuesta"].isin(["si", "parcial"])].copy()
        r["recall_auto"] = (r["recall_auto"].str.strip().str.lower())
        r = r[r["recall_auto"].isin(["si", "no"])]

        if len(r):
            m["recall_at_k_ic"] = proporcion(
                (r["recall_auto"] == "si").sum(), len(r))
        else:
            m["recall_at_k_ic"] = {"valor_%": None,
                                   "nota": "sin datos de recall_auto"}
    return m


def _v(d):
    return d.get("valor_%") if isinstance(d, dict) else None


def _delta(a, b):
    if a is None or b is None:
        return None

    return round(a - b, 1)


def comparar(rag, base):
    """Comparación entre LLM base y con RAG."""

    # Exactitud experimental: correcta + parcial
    ex_r = rag["exactitud_con_parciales_%"]
    ex_b = base["exactitud_con_parciales_%"]

    # Exactitud estricta: solamente correcta
    ex_estricta_r = rag["exactitud_%"]
    ex_estricta_b = base["exactitud_%"]

    al_r = rag["tasa_alucinacion_%"]
    al_b = base["tasa_alucinacion_%"]

    ab_r = rag["tasa_abstencion_adecuada_%"]

    ab_total = rag["tasa_abstencion_total_%"]
    ab_fallo = rag["tasa_abstencion_fallo_%"]

    fid = _v(rag.get("fidelidad_ic"))
    rec = _v(rag.get("recall_at_k_ic"))

    d_ex = _delta(ex_r, ex_b)

    criterios = {
        "exactitud >= 75% y +15 pp sobre línea base": None if d_ex is None else (ex_r >= U_EXACTITUD and d_ex >= U_DELTA_EXACTITUD),
        "fidelidad >= 80%": None if fid is None else fid >= U_FIDELIDAD,
        "alucinación <= 15%": None if al_r is None else al_r <= U_ALUCINACION,
        "abstención adecuada >= 70%": None if ab_r is None else ab_r >= U_ABSTENCION,
        "latencia promedio <= 10 s": None if rag["latencia_promedio_s"] is None else rag["latencia_promedio_s"] <= U_LATENCIA,
        "Recall@5 >= 80%": None if rec is None else rec >= U_RECALL,
    }
    criterios = {k: (None if x is None else bool(x))
                 for k, x in criterios.items()}
    cumplidos = sum(1 for x in criterios.values() if x is True)
    mejora = bool(None not in (ex_r, ex_b, al_r, al_b)
                  and ex_r > ex_b and al_r < al_b)
    return {
        "tabla": {
            "exactitud_con_parciales_%": {"baseline": ex_b, "rag": ex_r, "delta_pp": d_ex},
            "exactitud_estricta_%": {"baseline": ex_estricta_b, "rag": ex_estricta_r},
            "alucinacion_%": {"baseline": al_b, "rag": al_r, "delta_pp": _delta(al_r, al_b)},
            "abstencion_adecuada_%": {"baseline": base["tasa_abstencion_adecuada_%"], "rag": ab_r},
            "abstencion_total_%": {"baseline": base["tasa_abstencion_total_%"], "rag": ab_total},
            "abstencion_fallo_%": {"baseline": base["tasa_abstencion_fallo_%"], "rag": ab_fallo},
            "latencia_promedio_s": {"baseline": base["latencia_promedio_s"], "rag": rag["latencia_promedio_s"]},
            "fidelidad_%": {"rag": fid},
            "recall_at_5_%": {"rag": rec},
        },
        "umbrales": criterios,
        "umbrales_cumplidos": f"{cumplidos}/6",
        "supera_baseline_en_exactitud_y_alucinacion": mejora,
        "exito_segun_propuesta": bool(cumplidos >= 5 and mejora),
        "nota": (
            "La exactitud considera respuestas correctas y parciales. "
            "La abstención adecuada se calcula sobre preguntas sin "
            "información documental. abstencion_fallo identifica "
            "abstenciones ante información disponible. "
            "None = sin dato."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nombre", default="rag")
    parser.add_argument("--base", default="baseline")
    args = parser.parse_args()

    df_rag = cargar(args.nombre)
    print(f"RAG : {(DIR / args.nombre / 'respuestas.csv').resolve()}")
    rag = calcular_rag(df_rag)
    (DIR / args.nombre / "metricas.json").write_text(json.dumps(rag,
                                                                ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{args.nombre}\n")
    print(json.dumps(rag, ensure_ascii=False, indent=2))

    try:
        df_base = cargar(args.base)
    except SystemExit as e:
        print(f"\nNo se pudo comparar con la línea base: {e}")
        return

    print(f"\nBASE: {(DIR / args.base / 'respuestas.csv').resolve()}")
    base = calcular(df_base)
    comp = comparar(rag, base)
    (DIR / f"comparacion_{args.nombre}_vs_{args.base}.json").write_text(
        json.dumps(comp, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{args.nombre} vs {args.base}")
    print(json.dumps(comp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
