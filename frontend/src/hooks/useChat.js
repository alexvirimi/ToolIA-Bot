import { useCallback, useEffect, useRef, useState } from "react";
import { cerrarSesion, enviarPregunta } from "../api.js";

export function useChat() {
  const [mensajes, setMensajes] = useState([]);
  const [cargando, setCargando] = useState(false);
  const sesionId = useRef(null);
  const contador = useRef(0);
  const ocupado = useRef(false);

  const nuevoId = () => ++contador.current;

  useEffect(() => {
    const alSalir = () => cerrarSesion(sesionId.current);
    window.addEventListener("pagehide", alSalir);
    return () => window.removeEventListener("pagehide", alSalir);
  }, []);

  const pedir = useCallback(async (pregunta) => {
    ocupado.current = true;
    setCargando(true);
    try {
      const r = await enviarPregunta(pregunta, sesionId.current);
      sesionId.current = r.sesion_id;
      setMensajes((prev) => [
        ...prev,
        { id: nuevoId(), rol: "asistente", texto: r.respuesta, fuentes: r.fuentes, abstencion: r.abstencion },
      ]);
    } catch (e) {
      setMensajes((prev) => [...prev, { id: nuevoId(), rol: "error", texto: e.message, pregunta }]);
    } finally {
      ocupado.current = false;
      setCargando(false);
    }
  }, []);

  const enviar = useCallback(
    (texto) => {
      const pregunta = texto.trim();
      if (!pregunta || ocupado.current) return;
      setMensajes((prev) => [
        ...prev.filter((m) => m.rol !== "error"),
        { id: nuevoId(), rol: "usuario", texto: pregunta },
      ]);
      pedir(pregunta);
    },
    [pedir]
  );

  const reintentar = useCallback(
    (pregunta) => {
      if (ocupado.current) return;
      setMensajes((prev) => prev.filter((m) => m.rol !== "error"));
      pedir(pregunta);
    },
    [pedir]
  );

  const nuevaConversacion = useCallback(() => {
    cerrarSesion(sesionId.current);
    sesionId.current = null;
    setMensajes([]);
  }, []);

  return { mensajes, cargando, enviar, reintentar, nuevaConversacion };
}
