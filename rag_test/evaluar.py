"""Compara corridas etiquetadas sobre el mismo conjunto de preguntas."""

import argparse
import json
from pathlib import Path

from .ejecutar import CAMPOS_PREGUNTAS, CARPETA, CORRIDAS, guardar_json, huella, nombre_local

from csv_seguro import leer
from metricas import cargar_respuestas, proporcion, validar_abstenciones, validar_etiquetas
from rag.evaluate_rag import calcular_rag

INDICADORES = (
    "exactitud_%",
    "exactitud_con_parciales_%",
    "tasa_alucinacion_%",
    "tasa_abstencion_adecuada_%",
    "tasa_abstencion_fallo_%",
    "fidelidad_%",
    "hit_fuente_at_5_%",
    "latencia_promedio_s",
)


def cargar_corrida(carpeta: Path):
    info = json.loads((carpeta / "run_info.json").read_text(encoding="utf-8"))
    ruta = carpeta / "respuestas.csv"
    preguntas = leer(ruta)[CAMPOS_PREGUNTAS].to_dict("records")
    if len(preguntas) != info["n_preguntas"] or huella(preguntas) != info["huella_preguntas"]:
        raise ValueError(f"{carpeta.name}: cambiaron las filas o datos de las preguntas.")

    df = cargar_respuestas(ruta)
    error = validar_etiquetas(df)
    if error:
        raise ValueError(f"{carpeta.name}: {error}")
    if not validar_abstenciones(df):
        raise ValueError(f"{carpeta.name}: revisa las etiquetas de abstención.")
    respondidas = ~df["etiqueta"].isin(["abstencion", "abstencion_fallo"])
    fidelidad = df["fidelidad"].str.strip().str.lower()
    if not fidelidad[respondidas].isin(["si", "no"]).all():
        raise ValueError(f"{carpeta.name}: falta marcar fidelidad con si/no en respuestas no abstenidas.")
    if not df["latencia_s"].between(0, float("inf"), inclusive="left").all():
        raise ValueError(f"{carpeta.name}: hay latencias ausentes o inválidas.")

    metricas = calcular_rag(df)
    hits = df.loc[df["tiene_respuesta"].isin(["si", "parcial"]), "hit_fuente_at_5"]
    medibles = hits.isin(["si", "no"])
    metricas["hit_fuente_at_5_ic"] = proporcion((hits == "si").sum(), medibles.sum())
    metricas["hit_fuente_at_5_%"] = metricas["hit_fuente_at_5_ic"]["valor_%"]
    metricas["fidelidad_%"] = metricas["fidelidad_ic"]["valor_%"]
    return info, metricas, dict(zip(df["id"], df["etiqueta"]))


def comparar(nombres, cambios_permitidos=()):
    permitidos = set(cambios_permitidos)
    if permitidos - {"huella_indice", "num_predict", "num_ctx", "formato"}:
        raise ValueError("Solo se permiten cambios explícitos de índice o límites de generación.")
    if len(set(nombres)) != len(nombres):
        raise ValueError("Cada nombre de corrida debe ser distinto.")
    control, metricas_control, etiquetas_control = cargar_corrida(CORRIDAS / nombres[0])
    if control["variante"] != "control":
        raise ValueError("La primera corrida debe ser de la variante control.")
    resultados = {nombres[0]: {"variante": "control", "metricas": metricas_control}}
    for nombre in nombres[1:]:
        info, metricas, etiquetas = cargar_corrida(CORRIDAS / nombre)
        claves = set(info["config_compartida"]) | set(control["config_compartida"])
        diferencias = {c: {"control": control["config_compartida"].get(c), "variante": info["config_compartida"].get(c)}
                       for c in claves if control["config_compartida"].get(c) != info["config_compartida"].get(c)}
        if (info["huella_preguntas"] != control["huella_preguntas"]
                or set(diferencias) - permitidos
                or info.get("protocolo", "historico") != control.get("protocolo", "historico")):
            raise ValueError(f"{nombre}: preguntas, modelos, parámetros o índice distintos al control.")

        cambios = [
            {"id": id_pregunta, "control": anterior, "variante": etiquetas[id_pregunta]}
            for id_pregunta, anterior in etiquetas_control.items()
            if etiquetas[id_pregunta] != anterior
        ]
        deltas = {}
        for indicador in INDICADORES:
            actual, anterior = metricas[indicador], metricas_control[indicador]
            deltas[indicador] = (round(actual - anterior, 2)
                                 if actual is not None and anterior is not None else None)
        resultados[nombre] = {
            "variante": info["variante"],
            "metricas": metricas,
            "delta_vs_control_pp_o_segundos": deltas,
            "cambios_etiqueta": cambios,
            "cambios_configuracion_declarados": diferencias,
        }

    return {
        "control": nombres[0],
        "n_preguntas": control["n_preguntas"],
        "huella_preguntas": control["huella_preguntas"],
        "config_compartida": control["config_compartida"],
        "factores_experimentales_permitidos": sorted(permitidos),
        "nota": "HitFuente@5 estima coincidencia documental por URL, no recall de evidencia.",
        "resultados": resultados,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corridas", type=nombre_local, nargs="+", help="Primero el control.")
    parser.add_argument("--nombre", type=nombre_local, required=True, help="Nombre nuevo del informe.")
    parser.add_argument("--permitir-cambios", nargs="*", choices=("huella_indice", "num_predict", "num_ctx", "formato"), default=[],
                        help="Factores experimentales explícitos; modelos, preguntas y protocolo siguen siendo obligatoriamente iguales.")
    args = parser.parse_args()
    if len(args.corridas) < 2:
        parser.error("Indica el control y al menos una variante para comparar.")
    try:
        informe = comparar(args.corridas, args.permitir_cambios)
        destino = CARPETA / "evaluaciones" / args.nombre
        destino.mkdir(parents=True, exist_ok=False)
        guardar_json(destino / "comparacion.json", informe)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Comparación guardada en {destino / 'comparacion.json'}")


if __name__ == "__main__":
    main()
