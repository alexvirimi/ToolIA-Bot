import { useEffect, useLayoutEffect, useRef, useState } from "react";

export default function Composer({ onEnviar, deshabilitado, placeholder }) {
  const [valor, setValor] = useState("");
  const campo = useRef(null);

  useEffect(() => {
    if (window.matchMedia("(pointer: fine)").matches) campo.current?.focus();
  }, []);

  useLayoutEffect(() => {
    const el = campo.current;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [valor]);

  function enviar() {
    const texto = valor.trim();
    if (!texto || deshabilitado) return;
    onEnviar(texto);
    setValor("");
  }

  function alPulsarTecla(e) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      enviar();
    }
  }

  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        enviar();
      }}
    >
      <label htmlFor="pregunta" className="solo-lectores">
        Escribe tu pregunta
      </label>
      <textarea
        id="pregunta"
        ref={campo}
        rows={1}
        maxLength={1000}
        value={valor}
        placeholder={placeholder}
        onChange={(e) => setValor(e.target.value)}
        onKeyDown={alPulsarTecla}
      />
      <button
        type="submit"
        className="composer-enviar"
        aria-label="Enviar pregunta"
        disabled={!valor.trim() || deshabilitado}
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" focusable="false">
          <path d="M9 15V3M9 3L3.5 8.5M9 3L14.5 8.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </form>
  );
}
