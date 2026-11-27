import copy
import json

import pandas as pd
import pytest

from rag_test.calidad import calcular_calidad, validar_anotaciones, verificar_salidas
from rag_test.ejecutar import CAMPOS_PREGUNTAS
from rag_test.mejora import fragmentar_integral, sin_duplicados, unidades_documento
from embeddings import huella


def documento(paginas):
    return {"document_id": "doc", "titulo": "Reglamento", "fuente_url": "https://www.utb.edu.co/reglamento",
            "archivo_origen": "raw/docs/reglamento.pdf", "sha256_origen": "hash",
            "paginas": [{"pagina": i, "texto": t} for i, t in enumerate(paginas, 1)]}


def test_articulo_y_condicion_en_pagina_siguiente():
    doc = documento(["ARTÍCULO 68: Debe conservar PPA mínimo 3,20.\nSi inicia en PAT y no logra PPP 3,20,",
                     "queda excluido.\nEste artículo aplica con créditos superiores al primer nivel.\nARTÍCULO 69: Recuperación Académica."])
    fs = fragmentar_integral([doc])
    assert "primer nivel" in fs[0]["text"]
    assert "ARTÍCULO 69" not in fs[0]["text"]
    assert fs[0]["metadata"]["page"] == 1 and fs[0]["metadata"]["page_end"] == 2


def test_articulos_no_se_mezclan():
    fs = fragmentar_integral([documento(["ARTÍCULO 1. Primer requisito académico publicado.\nARTÍCULO 2. Segundo requisito diferente publicado."])])
    assert len(fs) == 2
    assert "Segundo" not in fs[0]["text"]


def test_encabezado_html_preserva_beca():
    doc = documento(["## Beca A\nBeneficio publicado para esta beca.\n##### Requisitos\nPromedio mínimo 4,0 y ninguna sanción."])
    doc["titulo"] = "Beca A"
    fs = fragmentar_integral([doc])
    assert "Beca A > Requisitos" in fs[1]["text"]
    assert "ninguna sanción" in fs[1]["text"]


def test_modales_no_heredan_el_ultimo_encabezado_ajeno():
    doc = documento(["## Incentivos Saber Pro\nBeneficios para puntajes.\n### Requisitos de inscripción\nCertificar nivel B2 para el estímulo de inglés."])
    doc["titulo"] = "Conoce los estímulos de la UTB"
    fs = fragmentar_integral([doc])
    assert "Incentivos Saber Pro > Requisitos" not in fs[1]["text"]
    assert "Conoce los estímulos de la UTB > Requisitos" in fs[1]["text"]


def test_articulos_con_ordinal_se_separan():
    fs = fragmentar_integral([documento(["ARTÍCULO 1°. Exoneración de los derechos de grado.\nARTÍCULO 2°. Becas para los mejores puntajes académicos."])])
    assert len(fs) == 2


def test_vigencia_es_literal_y_no_se_inventa():
    doc = documento(["CONSEJO ACADÉMICO\nRESOLUCIÓN No. 01 DE 2025\nARTÍCULO 1°. Incentivos académicos.\nARTÍCULO 5°. La presente Resolución deroga la Resolución No. 05 del 15 de junio de 2023 y modifica el artículo 4° de la Resolución 02 del 19 de julio de 2024.\nARTÍCULO 6°. Rige desde su expedición."])
    fs = fragmentar_integral([doc])
    assert fs[0]["metadata"]["norma"] == "consejo_academico:1:2025"
    assert fs[0]["metadata"]["deroga_normas"] == "consejo_academico:5:2023"
    assert "deroga la Resolución No. 05" in fs[0]["metadata"]["disposiciones_vigencia"]


def test_tabla_entre_paginas_conserva_filas_y_no_roba_la_siguiente():
    doc = documento(["Tabla 5. Estudiantes de Honor\nNombre Programa PPA\nAna Derecho 4,9",
                     "Luis Ingeniería 4,8\nFuente: Vicerrectoría\nTabla 6. Otros reconocimientos\nMaría Economía 4,7"])
    unidades = list(unidades_documento(doc))
    texto = "\n".join(unidades[0]["lineas"])
    assert "Ana" in texto and "Luis" in texto and "María" not in texto
    assert "María" in "\n".join(unidades[1]["lineas"])


def test_no_borra_numeros_importantes():
    fs = fragmentar_integral([documento(["ARTÍCULO 1. Puntaje mínimo de ingreso\n280\nPPA mínimo\n3,20"])])
    assert "280" in fs[0]["text"] and "3,20" in fs[0]["text"]


def test_duplicados_y_versiones_diferentes():
    fs = [{"text": "Máximo 18 créditos.", "id": "1"}, {"text": "Máximo 18 créditos.", "id": "2"},
          {"text": "Máximo 18,5 créditos.", "id": "3"}]
    assert [f["id"] for f in sin_duplicados(fs)] == ["1", "3"]


@pytest.fixture
def ejemplo():
    filas, anotaciones = [], []
    for i in range(10):
        con = i < 5
        etiqueta = "correcta" if i < 4 else "incorrecta" if con else "abstencion"
        filas.append({"id": str(i), "tiene_respuesta": "si" if con else "no", "latencia_s": "2",
                      "categoria": "prueba", "etiqueta": "", "fidelidad": "", "observaciones": "",
                      "hit_fuente_at_5": "si"})
        anotaciones.append({"id": str(i), "etiqueta": etiqueta, "fidelidad": "si" if con else "",
                            "observaciones": "Cotejada con los documentos.", "evidencia_suficiente": "si" if i < 4 else "no" if con else "",
                            "justificacion_evidencia": "El contexto incluye o no incluye los datos solicitados.",
                            "fragmentos_evidencia": [1] if i < 4 else []})
    return pd.DataFrame(filas), anotaciones


def test_cinco_metas_y_denominadores(ejemplo):
    df, a = ejemplo
    m = calcular_calidad(df, a)
    assert m["objetivos"]["exactitud_estricta"]["total"] == 5
    assert m["objetivos"]["fidelidad"]["total"] == 5
    assert m["objetivos"]["sin_alucinacion"]["total"] == 10
    assert m["objetivos"]["exactitud_estricta"]["valor_%"] == 80
    assert m["cumple_cinco_metas_muestrales"]


def test_url_no_es_evidencia(ejemplo):
    df, a = ejemplo
    for r in a:
        if r["evidencia_suficiente"] == "si":
            r["evidencia_suficiente"] = "no"
            r["fragmentos_evidencia"] = []
    m = calcular_calidad(df, a)
    assert m["objetivos"]["evidencia_suficiente_at_5"]["valor_%"] == 0
    assert not m["cumple_cinco_metas_muestrales"]


@pytest.mark.parametrize("campo,valor", [("etiqueta", ""), ("fidelidad", ""), ("observaciones", ""),
                                       ("evidencia_suficiente", ""), ("fragmentos_evidencia", [6])])
def test_rechaza_pendientes(ejemplo, campo, valor):
    df, a = ejemplo
    a[0][campo] = valor
    with pytest.raises(ValueError):
        validar_anotaciones(df, a)


def test_abstencion_con_informacion_es_fallo(ejemplo):
    df, a = ejemplo
    a[0].update(etiqueta="abstencion", fidelidad="")
    with pytest.raises(ValueError):
        validar_anotaciones(df, a)


def test_latencia_incluida_en_guardas(ejemplo):
    df, a = ejemplo
    df["latencia_s"] = "10.001"
    assert not calcular_calidad(df, a)["cumple_cinco_metas_muestrales"]


def test_no_aprueba_por_redondear_a_80(ejemplo):
    df, a = ejemplo
    filas, anotaciones = [], []
    for i in range(2501):
        fila, nota = df.iloc[0].to_dict(), dict(a[0])
        fila["id"] = nota["id"] = str(i)
        nota["etiqueta"] = "correcta" if i < 2000 else "parcial"
        filas.append(fila)
        anotaciones.append(nota)
    m = calcular_calidad(pd.DataFrame(filas), anotaciones)
    assert m["objetivos"]["exactitud_estricta"]["valor_%"] == 80.0
    assert not m["objetivos"]["exactitud_estricta"]["cumple"]


def test_truncamiento_informado(ejemplo):
    df, a = ejemplo
    df["fin_generacion"] = ["length"] + ["stop"] * 9
    assert calcular_calidad(df, a)["truncadas"] == 1


def test_limite_sesion_impide_iniciar_corrida(tmp_path):
    from argparse import Namespace
    from rag_test.ejecutar import ejecutar
    sesion = tmp_path / "sesion.json"
    sesion.write_text(json.dumps({"limite": "2000-01-01T00:00:00+00:00"}), encoding="utf-8")
    with pytest.raises(ValueError, match="presupuesto temporal"):
        ejecutar(Namespace(sesion=sesion))


def test_fidelidad_sin_denominador_no_cumple(ejemplo):
    df, a = ejemplo
    for r in a[:5]:
        r.update(etiqueta="abstencion_fallo", fidelidad="")
    m = calcular_calidad(df, a)
    assert not m["objetivos"]["fidelidad"]["cumple"]


def test_huella_protege_respuestas():
    fila = {c: c for c in CAMPOS_PREGUNTAS}
    fila.update(respuesta_modelo="Respuesta original", latencia_s="2")
    df = pd.DataFrame([fila])
    info = {"n_preguntas": 1, "huella_preguntas": huella(df[CAMPOS_PREGUNTAS].to_dict("records")),
            "campos_fijos": list(df), "huella_salidas": huella(df.to_dict("records"))}
    verificar_salidas(info, df)
    df.at[0, "respuesta_modelo"] = "Otra respuesta"
    with pytest.raises(ValueError):
        verificar_salidas(info, df)


def test_comparador_no_permite_cambiar_modelos(monkeypatch):
    from rag_test import evaluar
    info = {"variante": "control", "huella_preguntas": "q", "n_preguntas": 1,
            "config_compartida": {"modelo_generador": "original", "huella_indice": "a"}}
    variante = copy.deepcopy(info)
    variante["config_compartida"].update(modelo_generador="otro", huella_indice="b")
    respuestas = iter([(info, {}, {"1": "correcta"}), (variante, {}, {"1": "correcta"})])
    monkeypatch.setattr(evaluar, "cargar_corrida", lambda _: next(respuestas))
    with pytest.raises(ValueError):
        evaluar.comparar(["control", "nuevo"], ["huella_indice"])


def test_comparador_exige_declarar_indice(monkeypatch):
    from rag_test import evaluar
    info = {"variante": "control", "huella_preguntas": "q", "n_preguntas": 1,
            "config_compartida": {"modelo_generador": "original", "huella_indice": "a"}}
    variante = copy.deepcopy(info)
    variante["config_compartida"]["huella_indice"] = "b"
    metricas = {k: 0 for k in evaluar.INDICADORES}
    monkeypatch.setattr(evaluar, "cargar_corrida", lambda p: (info if p.name == "control" else variante, metricas, {"1": "correcta"}))
    with pytest.raises(ValueError):
        evaluar.comparar(["control", "nuevo"])
    resultado = evaluar.comparar(["control", "nuevo"], ["huella_indice"])
    assert resultado["resultados"]["nuevo"]["cambios_configuracion_declarados"]["huella_indice"]["variante"] == "b"


def test_division_por_limite_no_trunca_texto(tmp_path, monkeypatch):
    from rag_test import preparacion
    texto = " ".join(f"dato{i:04}" for i in range(200))
    doc = documento(["ARTÍCULO 1. " + texto])
    monkeypatch.setattr(preparacion, "identidad_modelo", lambda: {"name": "local", "digest": "digest"})

    def api(endpoint, payload):
        assert payload["truncate"] is False
        if any(len(t) > 400 for t in payload["input"]):
            raise RuntimeError("Ollama HTTP 400: the input length exceeds the context length")
        return {"embeddings": [[1.0, 2.0] for _ in payload["input"]]}

    monkeypatch.setattr(preparacion, "_api", api)
    monkeypatch.setattr(preparacion, "construir_indice", lambda f, ruta: {"count": len(f)})
    resultado = preparacion.preparar_integral([doc], tmp_path)
    fr = json.loads((tmp_path / "fragmentos.json").read_text(encoding="utf-8"))
    palabras = set(" ".join(f["text"] for f in fr).split())
    assert set(texto.split()) <= palabras
    assert resultado["count"] > 1
    assert json.loads((tmp_path / "preparacion.json").read_text(encoding="utf-8"))["truncamiento"] is False


def test_ocr_rechaza_revision_incompleta(tmp_path):
    from rag_test.ocr_local import publicar
    (tmp_path / "origen.json").write_text(json.dumps({"pdf": "data/preguntas.csv", "sha256_pdf": "no_valido", "paginas": 4}), encoding="utf-8")
    revision = tmp_path / "revision.json"
    revision.write_text(json.dumps({"tipo_revision": "visual_IA", "paginas": {}}), encoding="utf-8")
    with pytest.raises(ValueError):
        publicar(tmp_path, revision, tmp_path / "salida.json", "https://www.utb.edu.co/doc.pdf", "Documento")


def test_ocr_rechaza_fuente_externa(tmp_path):
    from rag_test.ocr_local import publicar
    (tmp_path / "origen.json").write_text("{}", encoding="utf-8")
    revision = tmp_path / "revision.json"
    revision.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="oficial UTB"):
        publicar(tmp_path, revision, tmp_path / "salida.json", "https://example.org/doc.pdf", "Documento")


def test_renderizar_no_inventa_contenido():
    from rag_test.mejora import renderizar_estructura
    dato = {"sin_evidencia": False, "respuesta": "El descuento es del 50%.",
            "condiciones": ["Sujeto a apertura del curso."], "excepciones": [], "citas": [2]}
    texto = renderizar_estructura(json.dumps(dato), 5)
    assert "50%" in texto and "apertura" in texto and "[2]" in texto
    assert "100%" not in texto


def test_estructura_no_acepta_abstencion_con_datos():
    from rag_test.mejora import renderizar_estructura
    with pytest.raises(ValueError):
        renderizar_estructura(json.dumps({"sin_evidencia": True, "respuesta": "Son 123 personas.",
            "condiciones": [], "excepciones": [], "citas": []}), 5)


def test_estructura_no_acepta_cita_inexistente():
    from rag_test.mejora import renderizar_estructura
    with pytest.raises(ValueError):
        renderizar_estructura(json.dumps({"sin_evidencia": False, "respuesta": "Dato publicado.",
            "condiciones": [], "excepciones": [], "citas": [6]}), 5)
