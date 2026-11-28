import { COLORES_FUENTES, FORMAS_FUENTES } from "../shapes/Shapes.jsx";

const esUrlWeb = (url) => /^https?:\/\//i.test(url || "");

export default function SourceCard({ id, fuente, resaltada }) {
  const i = (fuente.n - 1) % FORMAS_FUENTES.length;
  const Forma = FORMAS_FUENTES[i];
  const ubicacion = [fuente.pagina && `p. ${fuente.pagina}`, fuente.seccion].filter(Boolean).join(", ");
  const clase = `fuente${resaltada ? " resaltada" : ""}`;

  const contenido = (
    <>
      <Forma size={40} className="fuente-icono" style={{ color: COLORES_FUENTES[i] }} />
      <span className="fuente-texto">
        <span className="fuente-titulo">
          <span className="fuente-n">[{fuente.n}]</span> {fuente.titulo}
        </span>
        {ubicacion && <span className="fuente-ubicacion">{ubicacion}</span>}
        <span className="fuente-url">{fuente.url}</span>
      </span>
    </>
  );

  if (!esUrlWeb(fuente.url)) {
    return (
      <div id={id} className={clase}>
        {contenido}
      </div>
    );
  }
  return (
    <a id={id} className={clase} href={fuente.url} target="_blank" rel="noopener noreferrer">
      {contenido}
      <span className="solo-lectores"> (se abre en una pestaña nueva)</span>
    </a>
  );
}
