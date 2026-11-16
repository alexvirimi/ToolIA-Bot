import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from langchain_core.output_parsers import StrOutputParser

from config import get_llm
from prompts import base_prompt

ROOT = Path(__file__).resolve().parents[1]
PREGUNTAS_CSV = ROOT / "data" / "preguntas.csv"
OUT_DIR = ROOT / "experiments" / "baseline"
RESPUESTAS_CSV = OUT_DIR / "respuestas.csv"
RUN_INFO_JSON = OUT_DIR / "run_info.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Frases tipicas de abstencion (solo sugerencia; se valida a mano)
FRASES_ABSTENCION = [
    "no tengo información", "no cuento con", "no dispongo",
    "no sé", "no se la respuesta", "no puedo confirmar",
    "no tengo acceso", "no encuentro", "no tengo datos", "no conozco",
]


def detectar_abstencion(texto: str) -> str:
    t = texto.lower()
    return "si" if any(f in t for f in FRASES_ABSTENCION) else "no"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Numero maximo de preguntas a ejecutar")
    args = parser.parse_args()

    df = pd.read_csv(PREGUNTAS_CSV, encoding="utf-8-sig")
    if args.limit:
        df = df.head(args.limit)

    # Reanudar: saltar preguntas ya respondidas
    hechas = set()
    if RESPUESTAS_CSV.exists():
        previas = pd.read_csv(RESPUESTAS_CSV, encoding="utf-8-sig")
        hechas = set(previas["id"].astype(str))

    modelo = get_llm()
    chain = base_prompt | modelo | StrOutputParser()

    # Carga el modelo en memoria; no se mide
    print("Cargando el modelo...")
    chain.invoke({"pregunta": "¡Hola!"})

    # Registro de la configuracion de la información corrida (trazabilidad)
    try:
        prompt_sistema = base_prompt.messages[0].prompt.template
    except Exception:
        prompt_sistema = "no disponible"
    RUN_INFO_JSON.write_text(json.dumps({
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "sistema": "baseline (LLM sin recuperacion)",
        "modelo": getattr(modelo, "model", "desconocido"),
        "temperature": getattr(modelo, "temperature", None),
        "seed": getattr(modelo, "seed", None),
        "num_predict": getattr(modelo, "num_predict", None),
        "prompt_sistema": prompt_sistema,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # calcular preguntas que faltan por ejecutar (no se repite lo ya hecho)
    pendientes = df[~df["id"].astype(str).isin(hechas)]
    print(f"{len(pendientes)} preguntas por ejecutar, "
          f"{len(hechas)} estaban hechas.")

    for i, fila in enumerate(pendientes.itertuples(index=False), start=1):
        t0 = time.perf_counter()
        try:
            respuesta = chain.invoke({"pregunta": fila.pregunta})
            error = ""
        except Exception as e:
            respuesta, error = "", str(e)
        latencia = round(time.perf_counter() - t0, 2)

        registro = pd.DataFrame([{
            "id": fila.id,
            "categoria": getattr(fila, "categoria", ""),
            "tiene_respuesta": fila.tiene_respuesta,
            "pregunta": fila.pregunta,
            "respuesta_referencia": fila.respuesta_referencia,
            "respuesta_modelo": respuesta.strip(),
            "latencia_s": latencia, # tiempo en segundos que tarda en responder el modelo
            "abstencion_auto": detectar_abstencion(respuesta),
            "error": error,
            "etiqueta": "",       # etiqueta manual
            "observaciones": "",  # análisis manual de la respuesta
        }])
        # Guardado incremental: no se pierde nada si se interrumpe
        registro.to_csv(RESPUESTAS_CSV, mode="a", index=False,
                        header=not RESPUESTAS_CSV.exists(),
                        encoding="utf-8-sig")
        print(f"[{i}/{len(pendientes)}] id={fila.id} | {latencia} s")

    print(f"\nListo. Resultados en: {RESPUESTAS_CSV}")
    print("Siguiente paso: abrir el CSV y llenar las columnas 'etiqueta' y 'observaciones'.")


if __name__ == "__main__":
    main()
