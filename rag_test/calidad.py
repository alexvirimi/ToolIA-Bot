"""Evaluación de cinco metas con evidencia revisada, no coincidencias de URL."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .asistente import ROOT
from .ejecutar import CAMPOS_PREGUNTAS, cargar_preguntas, nombre_local
from csv_seguro import leer
from embeddings import guardar_json, huella
from metricas import proporcion, validar_abstenciones, validar_etiquetas
from rag.evaluate_rag import calcular_rag

MANUALES = {"etiqueta", "fidelidad", "observaciones"}
METAS = {"exactitud_estricta": .8, "fidelidad": .8,
         "evidencia_suficiente_at_5": .8, "abstencion_adecuada": .8, "sin_alucinacion": .8}


def preparar_referencia(salida):
    salida = Path(salida)
    if salida.exists():
        raise ValueError("La referencia auditada ya existe; no se sobrescribe.")
    preguntas = cargar_preguntas(ROOT / "data/preguntas.csv", None)
    protocolo = json.loads((ROOT / "rag_test/referencia_desarrollo.json").read_text(encoding="utf-8"))
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


def verificar_salidas(info, df):
    if len(df) != info["n_preguntas"] or huella(df[CAMPOS_PREGUNTAS].to_dict("records")) != info["huella_preguntas"]:
        raise ValueError("Cambiaron preguntas, filas u orden de la corrida.")
    if "huella_salidas" in info:
        if huella(df[info["campos_fijos"]].to_dict("records")) != info["huella_salidas"]:
            raise ValueError("Cambiaron respuestas, latencias u otros datos originales.")


def copiar_auditada(origen, nombre, preguntas):
    """Versiona referencias de una salida anterior; NO vuelve a generar respuestas."""
    origen, destino = Path(origen), ROOT / "rag_test/corridas" / nombre
    if destino.exists():
        raise ValueError("La copia auditada debe tener un nombre nuevo.")
    previo = json.loads((origen / "run_info.json").read_text(encoding="utf-8"))
    df, referencia = leer(origen / "respuestas.csv"), leer(preguntas)
    if df["id"].tolist() != referencia["id"].tolist() or df["pregunta"].tolist() != referencia["pregunta"].tolist():
        raise ValueError("No se pueden trasladar salidas entre preguntas diferentes.")
    for c in CAMPOS_PREGUNTAS:
        df[c] = referencia[c]
    for c in MANUALES:
        df[c] = ""
    if "hit_fuente_at_5" not in df:
        from .asistente import hit_fuente
        recuperacion = {r["id"]: r for r in map(json.loads, (origen / "recuperacion.jsonl").read_text(encoding="utf-8").splitlines())}
        df["hit_fuente_at_5"] = [hit_fuente(r.fuente_url, r.tiene_respuesta, recuperacion[r.id]["fragmentos"]) for r in df.itertuples()]
    campos_fijos = [c for c in df if c not in MANUALES]
    auditoria = Path(preguntas).with_suffix(".auditoria.json")
    version = json.loads(auditoria.read_text(encoding="utf-8"))["version"] if auditoria.exists() else "referencia-versionada"
    info = {**previo, "variante": previo.get("variante", "control"),
            "protocolo": version, "n_preguntas": len(df),
            "huella_preguntas": huella(df[CAMPOS_PREGUNTAS].to_dict("records")),
            "campos_fijos": campos_fijos, "huella_salidas": huella(df[campos_fijos].to_dict("records")),
            "reutilizada_sin_generar": True, "origen_auditoria": str(origen),
            "huella_csv_origen": huella((origen / "respuestas.csv").read_bytes())}
    destino.mkdir(parents=True, exist_ok=False)
    df.to_csv(destino / "respuestas.csv", index=False, encoding="utf-8-sig")
    (destino / "recuperacion.jsonl").write_bytes((origen / "recuperacion.jsonl").read_bytes())
    guardar_json(destino / "run_info.json", info)
    return destino


def validar_anotaciones(df, anotaciones):
    ids = df["id"].tolist()
    if len(set(ids)) != len(ids) or len(anotaciones) != len(ids) or [r["id"] for r in anotaciones] != ids:
        raise ValueError("Se requieren exactamente los mismos IDs, únicos y en su orden.")
    nuevo = df.copy()
    for i, (fila, anotacion) in enumerate(zip(df.to_dict("records"), anotaciones)):
        for campo in MANUALES:
            valor = anotacion.get(campo, "")
            if not isinstance(valor, str):
                raise ValueError(f"{fila['id']}: {campo} debe ser texto.")
            nuevo.at[i, campo] = valor
        if not anotacion.get("observaciones", "").strip():
            raise ValueError(f"{fila['id']}: falta justificar etiqueta.")
        if fila["tiene_respuesta"] in {"si", "parcial"}:
            if anotacion.get("evidencia_suficiente") not in {"si", "no"} or not anotacion.get("justificacion_evidencia", "").strip():
                raise ValueError(f"{fila['id']}: falta evaluar y justificar evidencia suficiente.")
            numeros = anotacion.get("fragmentos_evidencia", [])
            if not isinstance(numeros, list) or any(type(n) is not int or not 1 <= n <= 5 for n in numeros):
                raise ValueError(f"{fila['id']}: citas de evidencia no válidas.")
            if anotacion["evidencia_suficiente"] == "si" and not numeros:
                raise ValueError(f"{fila['id']}: evidencia suficiente requiere fragmentos identificados.")
        etiqueta, fidelidad = anotacion.get("etiqueta"), anotacion.get("fidelidad", "")
        if etiqueta in {"abstencion", "abstencion_fallo"}:
            if fidelidad != "":
                raise ValueError("La fidelidad debe quedar vacía en abstenciones.")
        elif fidelidad not in {"si", "no"}:
            raise ValueError("Falta fidelidad si/no en una respuesta no abstenida.")
    error = validar_etiquetas(nuevo)
    if error or not validar_abstenciones(nuevo):
        raise ValueError(error or "Abstenciones inconsistentes con disponibilidad.")
    return nuevo


def calcular_calidad(df, anotaciones):
    df = validar_anotaciones(df.reset_index(drop=True), anotaciones)
    df["latencia_s"] = pd.to_numeric(df["latencia_s"], errors="coerce")
    if df.empty or not df["latencia_s"].between(0, float("inf"), inclusive="left").all():
        raise ValueError("Latencias vacías o inválidas.")
    con = df["tiene_respuesta"].isin(["si", "parcial"])
    sin = df["tiene_respuesta"].eq("no")
    resp = ~df["etiqueta"].isin(["abstencion", "abstencion_fallo"])
    evidencia = pd.Series([r.get("evidencia_suficiente", "") for r in anotaciones])
    conteos = {
        "exactitud_estricta": (int((con & df["etiqueta"].eq("correcta")).sum()), int(con.sum())),
        "fidelidad": (int((resp & df["fidelidad"].eq("si")).sum()), int(resp.sum())),
        "evidencia_suficiente_at_5": (int((con & evidencia.eq("si")).sum()), int(con.sum())),
        "abstencion_adecuada": (int((sin & df["etiqueta"].eq("abstencion")).sum()), int(sin.sum())),
        "sin_alucinacion": (int(df["etiqueta"].ne("alucinacion").sum()), len(df)),
    }
    objetivos = {nombre: {**proporcion(n, total), "umbral_%": METAS[nombre] * 100,
                         "cumple": total > 0 and n / total >= METAS[nombre]}
                 for nombre, (n, total) in conteos.items()}
    alucinaciones = int(df["etiqueta"].eq("alucinacion").sum())
    guardas = {"alucinacion_<=15%": alucinaciones / len(df) <= .15,
               "latencia_media_<=10s": float(df["latencia_s"].mean()) <= 10}
    return {"metricas": calcular_rag(df), "objetivos": objetivos, "guardas": guardas,
            "latencia_p95_s": round(float(df["latencia_s"].quantile(.95)), 3),
            "truncadas": int(df.get("fin_generacion", pd.Series(dtype=str)).eq("length").sum()),
            "cumple_cinco_metas_muestrales": all(m["cumple"] for m in objetivos.values()) and all(guardas.values()),
            "revision": "IA; consenso humano pendiente",
            "nota": "Cobertura suficiente@5 es revisión del contenido, no coincidencia de URL. No certifica generalización ni consenso humano."}


def evaluar_corrida(nombre, ruta_anotaciones):
    carpeta = ROOT / "rag_test/corridas" / nombre
    info = json.loads((carpeta / "run_info.json").read_text(encoding="utf-8"))
    df = leer(carpeta / "respuestas.csv")
    verificar_salidas(info, df)
    if "huella_recuperacion" in info and huella((carpeta / "recuperacion.jsonl").read_bytes()) != info["huella_recuperacion"]:
        raise ValueError("Los fragmentos o el contexto entregado cambiaron después de generar las respuestas.")
    revision = json.loads(Path(ruta_anotaciones).read_text(encoding="utf-8"))
    if revision["corrida"] != nombre or revision["huella_salidas"] != info.get("huella_salidas"):
        raise ValueError("Las anotaciones no corresponden a estas salidas.")
    anotaciones = revision["respuestas"]
    nuevo = validar_anotaciones(df, anotaciones)
    informe = calcular_calidad(nuevo, anotaciones)
    # Una etiqueta anterior solo puede confirmarse, no cambiarse silenciosamente.
    for campo in MANUALES:
        if ((df[campo] != "") & (df[campo] != nuevo[campo])).any():
            raise ValueError("Ya hay etiquetas diferentes; crea una revisión/copia explícita.")
    if not nuevo.equals(df):
        respaldo = carpeta / "backups" / f"sin_etiquetas_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.csv"
        respaldo.parent.mkdir(exist_ok=True)
        with respaldo.open("xb") as f:
            f.write((carpeta / "respuestas.csv").read_bytes())
        temporal = carpeta / "respuestas.etiquetadas.tmp"
        if temporal.exists():
            raise ValueError("Hay un temporal previo; revisar antes de escribir.")
        nuevo.to_csv(temporal, index=False, encoding="utf-8-sig")
        verificar_salidas(info, leer(temporal))
        temporal.replace(carpeta / "respuestas.csv")
    informe.update(corrida=nombre, huella_preguntas=info["huella_preguntas"], huella_salidas=info.get("huella_salidas"))
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
    anteriores = leer(origen / "respuestas.csv").set_index("id").to_dict("index")
    actuales = leer(destino / "respuestas.csv").to_dict("records")
    notas = {r["id"]: r for r in anterior["respuestas"]}
    resultado = []
    for fila in actuales:
        id_ = fila["id"]
        if (anteriores[id_]["respuesta_modelo"] != fila["respuesta_modelo"]
                and id_ not in ajustes.get("respuestas", {})
                and id_ not in ajustes.get("respuestas_confirmadas", [])):
            raise ValueError(f"{id_}: la respuesta cambió y falta revisión explícita.")
        r = {**notas[id_], **ajustes.get("respuestas", {}).get(id_, {}), **ajustes.get("evidencia", {}).get(id_, {})}
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
        print(f"Preparadas {len(preparar_referencia(args.salida))} preguntas auditadas.")
    elif args.accion == "copiar":
        print(copiar_auditada(args.origen, args.nombre, args.preguntas))
    elif args.accion == "combinar":
        print(f"Revisión completa: {len(combinar_revision(args.corrida, args.base, args.cambios, args.salida)['respuestas'])} filas.")
    else:
        print(json.dumps(evaluar_corrida(args.corrida, args.anotaciones), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
