import Composer from "./Composer.jsx";
import { Cuarto, Flor, Hojas } from "../shapes/Shapes.jsx";

export default function Landing({ onEnviar, deshabilitado }) {
  return (
    <main className="landing">
      <div className="landing-formas" aria-hidden="true">
        <Flor size={240} className="forma forma-flor" />
        <Hojas size={260} className="forma forma-hojas" />
        <Cuarto size={120} className="forma forma-cuarto" />
      </div>
      <div className="landing-centro">
        <h1>¡Qué alegrIA saludarte!</h1>
        <Composer onEnviar={onEnviar} deshabilitado={deshabilitado} placeholder="Pregunta lo que quieras" />
      </div>
    </main>
  );
}
