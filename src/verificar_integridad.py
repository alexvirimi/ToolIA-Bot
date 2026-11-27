"""
Comprueba que NO se hayan perdido etiquetas ni comentarios manuales.

Compara el respuestas.csv actual con cada copia de seguridad de la carpeta
backups/ (las que crean agregar_fuentes.py y calcular_recall.py) y avisa si
alguna celda manual que tenia datos ahora esta vacia o fue cambiada.
Tambien muestra cuantas celdas llenas tiene hoy cada columna manual.

Uso (desde la raiz del proyecto):
    python src/verificar_integridad.py experiments/rag/respuestas.csv
    python src/verificar_integridad.py experiments/rag/respuestas.csv --contra ruta/a/otra_copia.csv
"""
import argparse
from pathlib import Path

from csv_seguro import leer

ROOT = Path(__file__).resolve().parents[1]
MANUALES = ["etiqueta", "fidelidad", "observaciones"]


def comparar(actual, copia, nombre):
    """Devuelve True si no se perdio nada respecto a esa copia."""
    ok = True
    if "id" not in copia.columns:
        print(f"  [{nombre}] sin columna id, se omite")
        return True
    act = actual.set_index("id")
    cop = copia.set_index("id")
    for c in MANUALES:
        if c not in cop.columns:
            continue
        if c not in act.columns:
            print(f"  [{nombre}] FALTA la columna '{c}' en el archivo actual")
            ok = False
            continue
        perdidas, cambiadas = [], []
        for i, v in cop[c].items():
            if v == "":
                continue
            if i not in act.index:
                perdidas.append(i)
            elif act.at[i, c] == "":
                perdidas.append(i)
            elif act.at[i, c] != v:
                cambiadas.append(i)
        if perdidas:
            print(f"  [{nombre}] '{c}': {len(perdidas)} celda(s) con datos ahora vacias (ids {perdidas})")
            ok = False
        if cambiadas:
            print(f"  [{nombre}] '{c}': {len(cambiadas)} celda(s) con texto distinto (ids {cambiadas})")
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ruta")
    ap.add_argument("--contra", default=None, help="Copia especifica con la que comparar")
    args = ap.parse_args()

    ruta = Path(args.ruta)
    if not ruta.is_absolute():
        ruta = ROOT / ruta
    actual = leer(ruta)

    print(f"Archivo: {ruta}  ({len(actual)} filas)\n")
    print("Celdas manuales con contenido HOY:")
    for c in MANUALES:
        if c in actual.columns:
            print(f"  {c:14s}: {(actual[c] != '').sum()} de {len(actual)}")
        else:
            print(f"  {c:14s}: la columna NO existe")

    if args.contra:
        copias = [Path(args.contra)]
    else:
        copias = sorted((ruta.parent / "backups").glob(f"{ruta.stem}_*.csv"))
    if not copias:
        print("\nNo hay copias en backups/ para comparar. "
              "Usa --contra con una copia tuya, o compara con git (git diff).")
        return

    print(f"\nComparando contra {len(copias)} copia(s):")
    todo_ok = True
    for cp in copias:
        todo_ok &= comparar(actual, leer(cp), cp.name)
    print("\nRESULTADO:", "OK, no se perdio ningun dato manual." if todo_ok
          else "ATENCION: se perdieron o cambiaron datos manuales (ver arriba).")


if __name__ == "__main__":
    main()
