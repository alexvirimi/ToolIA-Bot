"""
Calcula las métricas de la línea base a partir de respuestas.csv, después
de llenar a mano la columna 'etiqueta' con alguna de estas opciones:
    correcta | parcial | incorrecta | alucinacion | abstencion
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from metricas import calcular, cargar_respuestas, validar_etiquetas


DIR = ROOT / "experiments" / "baseline"


def main():
    df = cargar_respuestas(DIR / "respuestas.csv")
    error = validar_etiquetas(df)
    if error:
        print(error)
        return

    metricas = calcular(df)
    (DIR / "metricas.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metricas, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
