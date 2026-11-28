import { useEffect, useRef } from "react";
import Composer from "./Composer.jsx";
import Message from "./Message.jsx";
import Thinking from "./Thinking.jsx";

export default function ChatView({ mensajes, cargando, onEnviar, onReintentar }) {
  const final = useRef(null);

  useEffect(() => {
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const comportamiento = reducido ? "auto" : "smooth";
    const ultimo = mensajes[mensajes.length - 1];
    if (ultimo?.rol === "asistente") {
      document.getElementById(`msg-${ultimo.id}`)?.scrollIntoView({ block: "start", behavior: comportamiento });
    } else {
      final.current?.scrollIntoView({ block: "end", behavior: comportamiento });
    }
  }, [mensajes, cargando]);

  return (
    <>
      <main className="chat">
        <div className="chat-columna" role="log" aria-label="Conversación" aria-live="polite">
          {mensajes.map((m) => (
            <Message key={m.id} mensaje={m} onReintentar={onReintentar} />
          ))}
          {cargando && <Thinking />}
          <div ref={final} />
        </div>
      </main>
      <footer className="pie">
        <Composer onEnviar={onEnviar} deshabilitado={cargando} placeholder="Pregunta a ToolIA…" />
        <p className="aviso">ToolIA es un asistente que puede cometer errores. Por favor verifica sus respuestas.</p>
      </footer>
    </>
  );
}
