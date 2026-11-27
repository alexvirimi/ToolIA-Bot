"""Evalúa las seis metas de la propuesta para una corrida RAG.

Recall@5 se operacionaliza como cobertura por pregunta: porcentaje de preguntas
con respuesta documental para las que al menos uno de los cinco fragmentos fue
marcado manualmente como relevante. No es el recall clásico de fragmentos sobre
el conjunto completo de documentos relevantes del corpus.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .asistente import ROOT
from .ejecutar import CAMPOS_PREGUNTAS, cargar_preguntas, nombre_local
from csv_seguro import leer
from embeddings import guardar_json, huella
from metricas import (
    calcular as calcular_metricas,
    cargar_respuestas,
    proporcion,
    validar_abstenciones,
    validar_etiquetas,
)
from rag.evaluate_rag import (
    calcular_rag,
    U_EXACTITUD,
    U_FIDELIDAD,
    U_ALUCINACION,
    U_ABSTENCION,
    U_LATENCIA,
    U_RECALL,
)

MANUALES = {"etiqueta", "fidelidad", "observaciones"}

MEJORA_MINIMA_BASELINE_PP = 15


def preparar_referencia(salida):
    salida = Path(salida)
    if salida.exists():
        raise ValueError(
            "La referencia auditada ya existe; no se sobrescribe.")
    preguntas = cargar_preguntas(ROOT / "data/preguntas.csv", None)
    protocolo = json.loads(
        (ROOT / "rag_test/referencia_desarrollo.json").read_text(encoding="utf-8"))
    cambios = []
    for fila in preguntas:
        ajuste = protocolo["cambios"].get(fila["id"], {})
        for campo in CAMPOS_PREGUNTAS:
            if campo in ajuste:
                cambios.append({"id": fila["id"], "campo": campo, "antes": fila[campo],
                                "despues": ajuste[campo], "motivo": ajuste["justificacion"]})
                fila[campo] = ajuste[campo]
        if "anadir_referencia" in ajuste:
            anterior = fila["respuesta_referencia"]
            fila["respuesta_referencia"] += ajuste["anadir_referencia"]
            cambios.append({"id": fila["id"], "campo": "respuesta_referencia", "antes": anterior,
                            "despues": fila["respuesta_referencia"], "motivo": ajuste["justificacion"]})
    salida.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(preguntas).to_csv(salida, index=False, encoding="utf-8-sig")
    guardar_json(salida.with_suffix(".auditoria.json"), {"version": protocolo["version"], "cambios": cambios,
                 "limitaciones": protocolo["limitaciones"], "huella_preguntas": huella(preguntas),
                 "n_preguntas": len(preguntas), "disponibilidad_sin_cambios": True})
    return preguntas


def _registros_con_saltos_normalizados(df, campos):
    """Prepara registros como en ejecutar.py, normalizando saltos de línea.

    Al escribir y volver a leer un CSV, los saltos internos pueden pasar de
    CRLF (\\r\\n) a LF (\\n). Esa diferencia de representación no debe
    invalidar la huella de los datos originales.
    """
    registros = []
    for fila in df[campos].to_dict("records"):
        registros.append({
            campo: str(valor).replace("\\r\\n", "\\n").replace("\\r", "\\n")
            for campo, valor in fila.items()
        })
    return registros


def verificar_salidas(info, df):
    if (
        len(df) != info["n_preguntas"]
        or huella(_registros_con_saltos_normalizados(df, CAMPOS_PREGUNTAS))
        != info["huella_preguntas"]
    ):
        raise ValueError("Cambiaron preguntas, filas u orden de la corrida.")
    if "huella_salidas" in info:
        huella_actual = huella(
            _registros_con_saltos_normalizados(df, info["campos_fijos"])
        )
        if huella_actual != info["huella_salidas"]:
            raise ValueError(
                "Cambiaron respuestas, latencias u otros datos originales.")


def copiar_auditada(origen, nombre, preguntas):
    """Versiona referencias de una salida anterior; NO vuelve a generar respuestas."""
    origen, destino = Path(origen), ROOT / "rag_test/corridas" / nombre
    if destino.exists():
        raise ValueError("La copia auditada debe tener un nombre nuevo.")
    previo = json.loads((origen / "run_info.json").read_text(encoding="utf-8"))
    df, referencia = leer(origen / "respuestas.csv"), leer(preguntas)
    if df["id"].tolist() != referencia["id"].tolist() or df["pregunta"].tolist() != referencia["pregunta"].tolist():
        raise ValueError(
            "No se pueden trasladar salidas entre preguntas diferentes.")
    for c in CAMPOS_PREGUNTAS:
        df[c] = referencia[c]
    for c in MANUALES:
        df[c] = ""
    if "hit_fuente_at_5" not in df:
        from .asistente import hit_fuente
        recuperacion = {r["id"]: r for r in map(
            json.loads, (origen / "recuperacion.jsonl").read_text(encoding="utf-8").splitlines())}
        df["hit_fuente_at_5"] = [hit_fuente(
            r.fuente_url, r.tiene_respuesta, recuperacion[r.id]["fragmentos"]) for r in df.itertuples()]
    campos_fijos = [c for c in df if c not in MANUALES]
    auditoria = Path(preguntas).with_suffix(".auditoria.json")
    version = json.loads(auditoria.read_text(
        encoding="utf-8"))["version"] if auditoria.exists() else "referencia-versionada"
    info = {**previo, "variante": previo.get("variante", "control"),
            "protocolo": version, "n_preguntas": len(df),
            "huella_preguntas": huella(df[CAMPOS_PREGUNTAS].to_dict("records")),
            "campos_fijos": campos_fijos, "huella_salidas": huella(df[campos_fijos].to_dict("records")),
            "reutilizada_sin_generar": True, "origen_auditoria": str(origen),
            "huella_csv_origen": huella((origen / "respuestas.csv").read_bytes())}
    destino.mkdir(parents=True, exist_ok=False)
    df.to_csv(destino / "respuestas.csv", index=False, encoding="utf-8-sig")
    (destino / "recuperacion.jsonl").write_bytes((origen /
                                                  "recuperacion.jsonl").read_bytes())
    guardar_json(destino / "run_info.json", info)
    return destino


def validar_anotaciones(df, anotaciones):
    ids = df["id"].tolist()
    if len(set(ids)) != len(ids) or len(anotaciones) != len(ids) or [str(r["id"]) for r in anotaciones] != [str(x) for x in ids]:
        raise ValueError(
            "Se requieren exactamente los mismos IDs, únicos y en su orden.")

    nuevo = df.copy()
    for i, (fila, anotacion) in enumerate(zip(df.to_dict("records"), anotaciones)):
        for campo in MANUALES:
            valor = anotacion.get(campo, "")
            if not isinstance(valor, str):
                raise ValueError(f"{fila['id']}: {campo} debe ser texto.")
            nuevo.at[i, campo] = valor
        if not anotacion.get("observaciones", "").strip():
            raise ValueError(f"{fila['id']}: falta justificar etiqueta.")

        disponible = fila["tiene_respuesta"] in {"si", "parcial"}
        if disponible:
            if anotacion.get("evidencia_suficiente") not in {"si", "no"} or not anotacion.get("justificacion_evidencia", "").strip():
                raise ValueError(
                    f"{fila['id']}: falta evaluar y justificar evidencia suficiente.")
            numeros = anotacion.get("fragmentos_evidencia", [])
            if not isinstance(numeros, list) or any(type(n) is not int or not 1 <= n <= 5 for n in numeros):
                raise ValueError(
                    f"{fila['id']}: citas de evidencia no válidas.")
            if anotacion["evidencia_suficiente"] == "si" and not numeros:
                raise ValueError(
                    f"{fila['id']}: evidencia suficiente requiere fragmentos identificados.")

            # Revisión independiente de pertinencia de los cinco resultados.
            # Se permite que falte por ahora para que el informe muestre Recall@5 pendiente.
            if "relevancia_top5" in anotacion:
                relevancia = anotacion["relevancia_top5"]
                if (not isinstance(relevancia, list) or len(relevancia) != 5
                        or any(type(v) is not bool for v in relevancia)):
                    raise ValueError(
                        f"{fila['id']}: relevancia_top5 debe contener exactamente cinco booleanos "
                        "(true=relevante, false=no relevante)."
                    )
        elif anotacion.get("relevancia_top5") not in (None, []):
            raise ValueError(
                f"{fila['id']}: las preguntas sin respuesta documental no entran en Recall@5.")

        etiqueta, fidelidad = anotacion.get(
            "etiqueta"), anotacion.get("fidelidad", "")
        if etiqueta in {"abstencion", "abstencion_fallo"}:
            if fidelidad != "":
                raise ValueError(
                    "La fidelidad debe quedar vacía en abstenciones.")
        elif fidelidad not in {"si", "no"}:
            raise ValueError(
                "Falta fidelidad si/no en una respuesta no abstenida.")

    error = validar_etiquetas(nuevo)
    if error or not validar_abstenciones(nuevo):
        raise ValueError(
            error or "Abstenciones inconsistentes con disponibilidad.")
    return nuevo


def cargar_baseline(ruta, df_rag):
    """Carga línea base y exige el mismo conjunto de preguntas y referencias congeladas."""
    ruta = Path(ruta)
    if not ruta.is_absolute():
        ruta = ROOT / ruta
    if not ruta.exists():
        raise ValueError(f"No existe el CSV de línea base: {ruta}")

    base = cargar_respuestas(ruta)
    error = validar_etiquetas(base)
    if error:
        raise ValueError(f"Línea base: {error}")
    if not validar_abstenciones(base):
        raise ValueError(
            "Línea base: hay inconsistencias en las etiquetas de abstención.")

    columnas = ["id", "pregunta", "tiene_respuesta", "respuesta_referencia"]
    faltantes = [
        c for c in columnas if c not in base.columns or c not in df_rag.columns]
    if faltantes:
        raise ValueError(
            f"No se puede verificar la equivalencia de la línea base; faltan columnas: {faltantes}")
    if base[columnas].astype(str).to_dict("records") != df_rag[columnas].astype(str).to_dict("records"):
        raise ValueError(
            "La línea base no tiene exactamente los mismos IDs, preguntas, disponibilidad y respuestas "
            "de referencia congeladas que la corrida RAG. Versiona la línea base con la misma referencia auditada."
        )
    base["latencia_s"] = pd.to_numeric(base["latencia_s"], errors="coerce")
    if base.empty or not base["latencia_s"].between(0, float("inf"), inclusive="left").all():
        raise ValueError("La línea base tiene latencias vacías o inválidas.")
    return base


def _objetivo_proporcion(n, total, umbral, *, extra=None):
    resultado = proporcion(n, total)
    resultado["umbral_%"] = umbral
    resultado["cumple"] = resultado["valor_%"] is not None and resultado["valor_%"] >= umbral
    if extra:
        resultado.update(extra)
    return resultado


def calcular_calidad(df, anotaciones, baseline_df):
    df = validar_anotaciones(df.reset_index(drop=True), anotaciones)
    df["latencia_s"] = pd.to_numeric(df["latencia_s"], errors="coerce")
    if df.empty or not df["latencia_s"].between(0, float("inf"), inclusive="left").all():
        raise ValueError("Latencias vacías o inválidas.")

    con = df["tiene_respuesta"].isin(["si", "parcial"])
    sin = df["tiene_respuesta"].eq("no")
    respondidas = ~df["etiqueta"].isin(["abstencion", "abstencion_fallo"])
    etiquetas = df["etiqueta"]

    # La rúbrica y el evaluador comparativo existente definen exactitud experimental
    # como correcta + parcial. Se conserva exactitud estricta como métrica secundaria.
    exactas_o_parciales = int(
        (con & etiquetas.isin(["correcta", "parcial"])).sum())
    total_con_respuesta = int(con.sum())
    exactitud = proporcion(exactas_o_parciales, total_con_respuesta)
    exactitud_baseline = calcular_metricas(
        baseline_df)["exactitud_con_parciales_%"]
    exactitud_rag = exactitud["valor_%"]
    delta_exactitud = (round(exactitud_rag - exactitud_baseline, 1)
                       if exactitud_rag is not None and exactitud_baseline is not None else None)

    fidelidad_ok = int((respondidas & df["fidelidad"].eq("si")).sum())
    total_respondidas = int(respondidas.sum())
    alucinaciones = int(etiquetas.eq("alucinacion").sum())
    abstenciones_ok = int((sin & etiquetas.eq("abstencion")).sum())
    total_sin_respuesta = int(sin.sum())

    # Recall@5 operacional de la propuesta: por pregunta, al menos un fragmento
    # pertinente entre los cinco recuperados. Requiere juicio manual de los 5.
    anotaciones_disponibles = [r for r, disponible in zip(
        anotaciones, con.tolist()) if disponible]
    revisadas = [r for r in anotaciones_disponibles if "relevancia_top5" in r]
    recall_pendientes = len(anotaciones_disponibles) - len(revisadas)
    if recall_pendientes == 0 and anotaciones_disponibles:
        hits_relevantes = sum(any(r["relevancia_top5"]) for r in revisadas)
        recall = proporcion(hits_relevantes, len(anotaciones_disponibles))
    else:
        recall = {"valor_%": None, "aciertos": None, "total": len(anotaciones_disponibles),
                  "pendientes": recall_pendientes,
                  "nota": "Completar la revisión de relevancia de los cinco fragmentos para cada pregunta con respuesta."}

    metricas_base = calcular_metricas(baseline_df)
    alucinacion_rag_pct = round(alucinaciones / len(df) * 100, 1)
    alucinacion_base_pct = metricas_base["tasa_alucinacion_%"]
    mejora_alucinacion = (
        alucinacion_base_pct is not None and alucinacion_rag_pct < alucinacion_base_pct)
    supera_baseline = (
        delta_exactitud is not None and delta_exactitud > 0 and mejora_alucinacion)

    latencia_media = float(df["latencia_s"].mean())
    objetivos = {
        "exactitud_con_parciales": {
            **exactitud,
            "umbral_%": U_EXACTITUD,
            "baseline_%": exactitud_baseline,
            "delta_vs_baseline_pp": delta_exactitud,
            "mejora_minima_baseline_pp": MEJORA_MINIMA_BASELINE_PP,
            "cumple": bool(exactitud_rag is not None and exactitud_rag >= U_EXACTITUD
                           and delta_exactitud is not None and delta_exactitud >= MEJORA_MINIMA_BASELINE_PP),
        },
        "fidelidad": _objetivo_proporcion(fidelidad_ok, total_respondidas, U_FIDELIDAD),
        "alucinacion": {
            **proporcion(alucinaciones, len(df)),
            "umbral_maximo_%": U_ALUCINACION,
            "cumple": alucinacion_rag_pct <= U_ALUCINACION,
        },
        "abstencion_adecuada": _objetivo_proporcion(abstenciones_ok, total_sin_respuesta, U_ABSTENCION),
        "latencia_promedio": {
            "valor_s": round(latencia_media, 3),
            "umbral_maximo_s": U_LATENCIA,
            "cumple": latencia_media <= U_LATENCIA,
        },
        "recall_at_5_operacional": {
            **recall,
            "umbral_%": U_RECALL,
            "cumple": bool(recall.get("valor_%") is not None and recall["valor_%"] >= U_RECALL),
        },
    }

    cumplidas = sum(1 for objetivo in objetivos.values()
                    if objetivo["cumple"] is True)
    pendientes = [nombre for nombre, objetivo in objetivos.items()
                  if objetivo.get("valor_%") is None and nombre == "recall_at_5_operacional"]
    todos_medidos = not pendientes
    return {
        "metricas": calcular_rag(df),
        "metricas_complementarias": {
            "exactitud_estricta_%": proporcion(int((con & etiquetas.eq("correcta")).sum()), total_con_respuesta),
            "exactitud_con_parciales_%": exactitud,
            "tasa_alucinacion_%": alucinacion_rag_pct,
            "tasa_alucinacion_baseline_%": alucinacion_base_pct,
            "fidelidad_%": proporcion(fidelidad_ok, total_respondidas),
            "recall_at_5_operacional": recall,
        },
        "objetivos": objetivos,
        "comparacion_baseline": {
            "exactitud_con_parciales_baseline_%": exactitud_baseline,
            "exactitud_con_parciales_rag_%": exactitud_rag,
            "delta_exactitud_pp": delta_exactitud,
            "alucinacion_baseline_%": alucinacion_base_pct,
            "alucinacion_rag_%": alucinacion_rag_pct,
            "supera_baseline_en_exactitud_y_alucinacion": supera_baseline,
        },
        "resumen_cumplimiento": {
            "metas_cumplidas": cumplidas,
            "metas_totales": 6,
            "metas_pendientes": pendientes,
            "evaluacion_completa": todos_medidos,
            "cumple_al_menos_5_de_6": bool(todos_medidos and cumplidas >= 5),
            "exito_segun_propuesta": bool(todos_medidos and cumplidas >= 5 and supera_baseline),
        },
        "latencia_p95_s": round(float(df["latencia_s"].quantile(.95)), 3),
        "truncadas": int(df.get("fin_generacion", pd.Series(dtype=str)).eq("length").sum()),
        "revision": "Etiquetado actualizado; consenso humano independiente pendiente",
        "nota": (
            "Recall@5 se operacionaliza como porcentaje de preguntas con respuesta documental "
            "que tienen al menos un fragmento pertinente entre los cinco recuperados. Requiere "
            "marcar manualmente la relevancia de los cinco fragmentos por pregunta. No es el recall "
            "clásico de fragmentos sobre todos los relevantes del corpus. evidencia_suficiente_at_5 "
            "y hit_fuente_at_5 se reportan aparte y no sustituyen esta medición."
        ),
    }


def evaluar_corrida(nombre, ruta_anotaciones, ruta_baseline):
    carpeta = ROOT / "rag_test/corridas" / nombre
    info = json.loads((carpeta / "run_info.json").read_text(encoding="utf-8"))
    df = leer(carpeta / "respuestas.csv")
    verificar_salidas(info, df)
    if "huella_recuperacion" in info and huella((carpeta / "recuperacion.jsonl").read_bytes()) != info["huella_recuperacion"]:
        raise ValueError(
            "Los fragmentos o el contexto entregado cambiaron después de generar las respuestas.")

    revision = json.loads(Path(ruta_anotaciones).read_text(encoding="utf-8"))
    if revision["corrida"] != nombre or revision["huella_salidas"] != info.get("huella_salidas"):
        raise ValueError("Las anotaciones no corresponden a estas salidas.")
    anotaciones = revision["respuestas"]
    baseline_df = cargar_baseline(ruta_baseline, df)
    nuevo = validar_anotaciones(df, anotaciones)
    informe = calcular_calidad(nuevo, anotaciones, baseline_df)

    # Una etiqueta anterior solo puede confirmarse, no cambiarse silenciosamente.
    for campo in MANUALES:
        if ((df[campo] != "") & (df[campo] != nuevo[campo])).any():
            raise ValueError(
                "Ya hay etiquetas diferentes; crea una revisión/copia explícita.")
    if not nuevo.equals(df):
        respaldo = carpeta / "backups" / \
            f"sin_etiquetas_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.csv"
        respaldo.parent.mkdir(exist_ok=True)
        with respaldo.open("xb") as f:
            f.write((carpeta / "respuestas.csv").read_bytes())
        temporal = carpeta / "respuestas.etiquetadas.tmp"
        if temporal.exists():
            raise ValueError(
                "Hay un temporal previo; revisar antes de escribir.")
        nuevo.to_csv(temporal, index=False, encoding="utf-8-sig")
        verificar_salidas(info, leer(temporal))
        temporal.replace(carpeta / "respuestas.csv")

    informe.update(corrida=nombre, huella_preguntas=info["huella_preguntas"], huella_salidas=info.get("huella_salidas"),
                   baseline=str(ruta_baseline))
    guardar_json(carpeta / "evaluacion_evidencia.json", revision)
    guardar_json(carpeta / "metricas.json", informe)
    return informe


def combinar_revision(nombre, base, cambios, salida):
    """Reutiliza revisiones cotejadas y exige confirmar cada respuesta distinta."""
    base, cambios = Path(base), Path(cambios)
    anterior = json.loads(base.read_text(encoding="utf-8"))
    ajustes = json.loads(cambios.read_text(encoding="utf-8"))
    origen = ROOT / "rag_test/corridas" / anterior["corrida"]
    destino = ROOT / "rag_test/corridas" / nombre
    anteriores = leer(
        origen / "respuestas.csv").set_index("id").to_dict("index")
    actuales = leer(destino / "respuestas.csv").to_dict("records")
    notas = {r["id"]: r for r in anterior["respuestas"]}
    resultado = []
    for fila in actuales:
        id_ = fila["id"]
        if (anteriores[id_]["respuesta_modelo"] != fila["respuesta_modelo"]
                and id_ not in ajustes.get("respuestas", {})
                and id_ not in ajustes.get("respuestas_confirmadas", [])):
            raise ValueError(
                f"{id_}: la respuesta cambió y falta revisión explícita.")
        r = {**notas[id_], **ajustes.get("respuestas", {}).get(
            id_, {}), **ajustes.get("evidencia", {}).get(id_, {})}
        resultado.append(r)
    info = json.loads((destino / "run_info.json").read_text(encoding="utf-8"))
    revision = {"corrida": nombre, "huella_salidas": info["huella_salidas"], "revisor": "IA; consenso humano pendiente",
                "base_revision": str(base), "respuestas": resultado}
    validar_anotaciones(leer(destino / "respuestas.csv"), resultado)
    guardar_json(salida, revision)
    return revision


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="accion", required=True)

    referencia = sub.add_parser("referencia")
    referencia.add_argument("--salida", type=Path, required=True)

    evaluar = sub.add_parser("evaluar")
    evaluar.add_argument("corrida", type=nombre_local)
    evaluar.add_argument("--anotaciones", type=Path, required=True)
    evaluar.add_argument("--baseline", type=Path, required=True,
                         help="CSV de línea base etiquetado con exactamente las mismas preguntas y referencias auditadas.")

    copiar = sub.add_parser("copiar")
    copiar.add_argument("origen", type=Path)
    copiar.add_argument("--nombre", type=nombre_local, required=True)
    copiar.add_argument("--preguntas", type=Path, required=True)

    combinar = sub.add_parser("combinar")
    combinar.add_argument("corrida", type=nombre_local)
    combinar.add_argument("--base", type=Path, required=True)
    combinar.add_argument("--cambios", type=Path, required=True)
    combinar.add_argument("--salida", type=Path, required=True)

    args = p.parse_args()
    if args.accion == "referencia":
        print(
            f"Preparadas {len(preparar_referencia(args.salida))} preguntas auditadas.")
    elif args.accion == "copiar":
        print(copiar_auditada(args.origen, args.nombre, args.preguntas))
    elif args.accion == "combinar":
        print(
            f"Revisión completa: {len(combinar_revision(args.corrida, args.base, args.cambios, args.salida)['respuestas'])} filas.")
    else:
        try:
            informe = evaluar_corrida(
                args.corrida, args.anotaciones, args.baseline)
        except (ValueError, OSError, KeyError) as exc:
            p.exit(1, f"Error: {exc}\n")
        print(json.dumps(informe, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
