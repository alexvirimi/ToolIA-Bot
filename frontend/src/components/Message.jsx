import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import SourceCard from "./SourceCard.jsx";

function prepararCitas(texto, fuentes) {
  const validas = new Set(fuentes.map((f) => f.n));
  return texto
    .replace(/\$(?=[^$]*\\geq?)([^$]*)\$/g, (_, expresion) => expresion.replace(/\\geq?/g, "≥"))
    .replace(/\\geq?/g, "≥")
    .replace(/\[(\d+)\]/g, (m, n) => (validas.has(Number(n)) ? `[\\[${n}\\]](#cita-${n})` : m));
}

export default function Message({ mensaje, onReintentar }) {
  const [resaltada, setResaltada] = useState(null);
  const temporizador = useRef(null);

  useEffect(() => () => clearTimeout(temporizador.current), []);

  if (mensaje.rol === "usuario") {
    return (
      <div id={`msg-${mensaje.id}`} className="mensaje mensaje-usuario">
        <p>{mensaje.texto}</p>
      </div>
    );
  }

  if (mensaje.rol === "error") {
    return (
      <div id={`msg-${mensaje.id}`} className="mensaje mensaje-error" role="alert">
        <p>{mensaje.texto}</p>
        <button type="button" className="boton" onClick={() => onReintentar(mensaje.pregunta)}>
          Intentar de nuevo
        </button>
      </div>
    );
  }

  const fuentes = mensaje.fuentes ?? [];

  function resaltar(n) {
    const tarjeta = document.getElementById(`fuente-${mensaje.id}-${n}`);
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    tarjeta?.scrollIntoView({ block: "nearest", behavior: reducido ? "auto" : "smooth" });
    setResaltada(n);
    clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => setResaltada(null), 1600);
  }

  const componentes = {
    a({ href = "", children }) {
      if (href.startsWith("#cita-")) {
        const n = Number(href.slice(6));
        return (
          <button type="button" className="cita" aria-label={`Ver la fuente ${n}`} onClick={() => resaltar(n)}>
            {children}
          </button>
        );
      }
      if (!href) return <span>{children}</span>;
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
  };

  return (
    <article id={`msg-${mensaje.id}`} className="mensaje mensaje-asistente">
      <div className="texto">
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={componentes} disallowedElements={["img"]}>
          {prepararCitas(mensaje.texto, fuentes)}
        </ReactMarkdown>
      </div>
      {fuentes.length > 0 && (
        <section className="fuentes" aria-label="Fuentes consultadas">
          {fuentes.map((f) => (
            <SourceCard key={f.n} id={`fuente-${mensaje.id}-${f.n}`} fuente={f} resaltada={resaltada === f.n} />
          ))}
        </section>
      )}
    </article>
  );
}
