import { Aspas } from "../shapes/Shapes.jsx";

export default function Thinking() {
  return (
    <div className="pensando" role="status">
      <Aspas size={28} className="pensando-icono" />
      <span>Buscando en los documentos de la UTB…</span>
    </div>
  );
}
