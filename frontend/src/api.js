const BASE = import.meta.env.VITE_API_URL ?? "";

export async function enviarPregunta(pregunta, sesionId) {
  let respuesta;
  try {
    respuesta = await fetch(`${BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta, sesion_id: sesionId }),
    });
  } catch {
    throw new Error("No se pudo conectar con el servidor de ToolIA. Revisa que el backend esté en ejecución.");
  }

  if (!respuesta.ok) {
    let detalle = "";
    try {
      detalle = (await respuesta.json()).detail;
    } catch {
      detalle = "";
    }
    throw new Error(
      typeof detalle === "string" && detalle ? detalle : `El servidor respondió con el error ${respuesta.status}.`
    );
  }
  return respuesta.json();
}

export function cerrarSesion(sesionId) {
  if (sesionId) navigator.sendBeacon(`${BASE}/api/chat/${sesionId}/cerrar`);
}
