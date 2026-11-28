import { COLORES_FUENTES, FORMAS_FUENTES } from "../shapes/Shapes.jsx";

const esUrlWeb = (url) => /^https?:\/\//i.test(url || "");

export default function SourceCard({ id, fuente, resaltada }) {
  const indiceForma = (fuente.n - 1) % FORMAS_FUENTES.length;
  const color = COLORES_FUENTES[(fuente.n - 1) % COLORES_FUENTES.length];
  const Forma = FORMAS_FUENTES[indiceForma];
  const ubicacion = [fuente.pagina && `p. ${fuente.pagina}`, fuente.seccion].filter(Boolean).join(", ");
  const clase = `fuente${resaltada ? " resaltada" : ""}`;

  const contenido = (
    <>
      <span className="fuente-icono-fondo">
        <Forma size={32} className="fuente-icono" />
      </span>
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
      <div id={id} className={clase} style={{ "--fuente-color": color }}>
        {contenido}
      </div>
    );
  }
  return (
    <a
      id={id}
      className={clase}
      href={fuente.url}
      target="_blank"
      rel="noopener noreferrer"
      style={{ "--fuente-color": color }}
    >
      {contenido}
      <span className="solo-lectores"> (se abre en una pestaña nueva)</span>
    </a>
  );
}
