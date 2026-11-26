"""
Utilidades para modificar un respuestas.csv SIN perder datos.

Reglas que se aplican siempre:
  * Antes de escribir se hace una copia con fecha y hora en <carpeta>/backups/
    (nunca se sobrescribe una copia anterior).
  * Se verifica que ninguna columna existente cambie (salvo las que se
    permiten explicitamente) y que no cambie el numero ni el orden de filas.
  * Las columnas manuales (etiqueta, fidelidad, observaciones, ...) nunca se
    pueden modificar: si se intenta, el script se niega a escribir.
  * Se escribe a un archivo temporal, se vuelve a leer para verificar y solo
    entonces reemplaza al original.
"""
import os
from datetime import datetime
import shutil
from pathlib import Path

import pandas as pd

PROTEGIDAS = {"id", "categoria", "tiene_respuesta", "pregunta",
              "respuesta_referencia", "respuesta_modelo", "latencia_s",
              "latencia_recuperacion_s", "abstencion_auto", "mejor_similitud",
              "fuentes_citadas", "fuentes_recuperadas", "error",
              "etiqueta", "fidelidad", "observaciones"}


def leer(ruta: Path) -> pd.DataFrame:
    """Lee todo como texto, sin convertir celdas vacias ni valores como 'NA'."""
    return pd.read_csv(ruta, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def verificar(orig, nuevo, quitar=(), solo_vacias=(), sobrescribir=()):
    """Devuelve la lista de problemas (vacia si todo esta bien)."""
    errores = []
    if len(orig) != len(nuevo):
        return [f"cambio el numero de filas ({len(orig)} -> {len(nuevo)})"]
    if orig["id"].tolist() != nuevo["id"].tolist():
        return ["cambio el orden o los ids de las filas"]
    for c in orig.columns:
        if c in quitar:
            continue
        if c not in nuevo.columns:
            errores.append(f"se perderia la columna '{c}'")
            continue
        if c in sobrescribir:
            continue
        a, b = orig[c].tolist(), nuevo[c].tolist()
        if c in solo_vacias:   # solo se permite llenar celdas que estaban vacias
            malas = [i for i, (x, y) in enumerate(zip(a, b)) if x != "" and x != y]
        else:
            malas = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        if malas:
            errores.append(f"cambiarian valores de '{c}' en {len(malas)} fila(s)")
    return errores


def guardar_seguro(orig, nuevo, ruta: Path, quitar=(), solo_vacias=(), sobrescribir=()):
    """Guarda 'nuevo' en 'ruta' solo si no se pierde nada. Devuelve la ruta de
    la copia de seguridad, o None si NO se escribio."""
    peligro = PROTEGIDAS & (set(solo_vacias) | set(sobrescribir))
    if peligro:
        raise ValueError(f"Columnas protegidas, no se pueden modificar: {sorted(peligro)}")

    errores = verificar(orig, nuevo, quitar, solo_vacias, sobrescribir)
    if errores:
        print("NO SE ESCRIBIO NADA. Problemas detectados:")
        for e in errores:
            print("  -", e)
        return None

    carpeta = ruta.parent / "backups"
    carpeta.mkdir(exist_ok=True)
    respaldo = carpeta / f"{ruta.stem}_{datetime.now():%Y%m%d_%H%M%S_%f}.csv"
    shutil.copy2(ruta, respaldo)

    tmp = ruta.with_suffix(".csv.tmp")
    nuevo.to_csv(tmp, index=False, encoding="utf-8-sig")
    errores = verificar(orig, leer(tmp), quitar, solo_vacias, sobrescribir)
    if errores:
        tmp.unlink(missing_ok=True)
        print("NO SE ESCRIBIO NADA (fallo la verificacion del archivo temporal):")
        for e in errores:
            print("  -", e)
        return None
    os.replace(tmp, ruta)
    return respaldo
