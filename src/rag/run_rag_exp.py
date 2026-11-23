"""Corre las preguntas de data/preguntas.csv con el sistema RAG.

Misma estructura de salida que la línea base (respuestas.csv) más columnas de
recuperación, para poder etiquetar a mano y comparar con metricas_rag.py.

Ejemplos:
    python src/run_rag.py                          # k=5, sin umbral (experiments/rag)
    python src/run_rag.py --umbral 0.55 --nombre rag_u055
    python src/run_rag.py --limit 5                # prueba rápida
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from rag import AsistenteRAG
from prompts import TEMPLATE as INSTRUCCIONES

ROOT = Path(__file__).resolve().parents[2]


def recall_auto(fuente_esperada, tiene_respuesta, fragmentos):
    """'si' si la fuente esperada aparece en título/archivo/URL de algún fragmento.
    Es una sugerencia automática, se debe validar manualmente y dejar vacía si no aplica.
    """
    esperado = str(fuente_esperada or "").strip().lower()
    if tiene_respuesta != "si" or not esperado:
        return ""
    for f in fragmentos:
        m = f["metadata"]
        texto = " ".join([m["title"], m["file"], m["source_url"]]).lower()
        if esperado in texto:
            return "si"
    return "no"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preguntas", default=str(ROOT / "data" / "preguntas.csv"))
    parser.add_argument("--nombre", default="rag",
                        help="Carpeta en experiments/ para esta corrida")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--umbral", type=float, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    out_dir = ROOT / "experiments" / args.nombre
    out_dir.mkdir(parents=True, exist_ok=True)
    respuestas_csv = out_dir / "respuestas.csv"
    recuperacion_jsonl = out_dir / "recuperacion.jsonl"

    df = pd.read_csv(args.preguntas, encoding="utf-8-sig",
                     dtype=str, keep_default_na=False)
    if args.limit:
        df = df.head(args.limit)

    hechas = set()
    if respuestas_csv.exists():
        hechas = set(pd.read_csv(respuestas_csv, encoding="utf-8-sig", dtype=str,
                                 keep_default_na=False)["id"])
    pendientes = df[~df["id"].isin(hechas)]
    print(f"{len(pendientes)} preguntas por ejecutar, "
          f"{len(hechas)} estaban hechas.")

    with AsistenteRAG(k=args.k, umbral=args.umbral) as asistente:
        # Calentamiento: carga los modelos en memoria; no se mide.
        print("Cargando modelos...")
        asistente.indice.buscar("¡Hola!", k=1)
        asistente.chain.invoke({"contexto": "", "pregunta": "¡Hola!"})

        llm = asistente.llm
        (out_dir / "run_info.json").write_text(json.dumps({
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "sistema": "rag",
            "modelo": getattr(llm, "model", "desconocido"),
            "temperature": getattr(llm, "temperature", None),
            "seed": getattr(llm, "seed", None),
            "num_predict": getattr(llm, "num_predict", None),
            "k": args.k,
            "umbral_similitud": args.umbral,
            "indice": asistente.indice.estado,
            "prompt_sistema": INSTRUCCIONES,
            "archivo_preguntas": str(args.preguntas),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        for i, fila in enumerate(pendientes.itertuples(index=False), start=1):
            t0 = time.perf_counter()
            res, error = None, ""
            try:
                res = asistente.responder(fila.pregunta)
            except Exception as e:
                error = str(e)
            latencia = round(time.perf_counter() - t0, 2)

            fragmentos = res["fragmentos"] if res else []
            fuentes = "; ".join(
                f"[{f['n']}] {f['titulo']}" +
                (f" p.{f['pagina']}" if f["pagina"] else "")
                for f in res["fuentes"]) if res else ""
            registro = pd.DataFrame([{
                "id": fila.id,
                "categoria": getattr(fila, "categoria", ""),
                "tiene_respuesta": fila.tiene_respuesta,
                "pregunta": fila.pregunta,
                "respuesta_referencia": fila.respuesta_referencia,
                "fuente_esperada": getattr(fila, "fuente_esperada", ""),
                "respuesta_modelo": res["respuesta"] if res else "",
                "latencia_s": latencia,
                "latencia_recuperacion_s": res["latencia_recuperacion_s"] if res else "",
                "abstencion_auto": ("si" if res["abstencion"] else "no") if res else "",
                "mejor_similitud": res["mejor_similitud"] if res else "",
                "fuentes_citadas": fuentes,
                "recall_auto": recall_auto(getattr(fila, "fuente_esperada", ""),
                                           fila.tiene_respuesta, fragmentos),
                "error": error,
                "etiqueta": "",       # etiqueta manual: correcta|parcial|incorrecta|alucinacion|abstencion
                # etiqueta manual: ¿respaldada por los fragmentos? solo si no se abstuvo, si|no
                "fidelidad": "",
                "observaciones": "",  # análisis manual de la respuesta
            }])
            registro.to_csv(respuestas_csv, mode="a", index=False,
                            header=not respuestas_csv.exists(), encoding="utf-8-sig")
            with recuperacion_jsonl.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"id": fila.id, "fragmentos": fragmentos},
                                    ensure_ascii=False) + "\n")
            print(f"[{i}/{len(pendientes)}] id={fila.id} | {latencia} s")

    print(f"\nListo. Resultados en: {respuestas_csv}")
    print("Siguiente paso: abrir el csv, llenar 'etiqueta' y 'fidelidad' (y revisar 'recall_auto'), "
          "luego correr metricas_rag.py.")


if __name__ == "__main__":
    main()
