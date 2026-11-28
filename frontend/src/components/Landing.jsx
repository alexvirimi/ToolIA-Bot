import { useState } from "react";
import Composer from "./Composer.jsx";
import { Cuarto, Flor, Hojas } from "../shapes/Shapes.jsx";

const SALUDOS = ["¡Qué alegrIA saludarte!", "¡Ya te querIA ver!", "Qué alegrIA verte de nuevo"];

export default function Landing({ onEnviar, deshabilitado }) {
  const [saludo] = useState(() => SALUDOS[Math.floor(Math.random() * SALUDOS.length)]);

  return (
    <main className="landing">
      <div className="landing-formas" aria-hidden="true">
        <Flor size={240} className="forma forma-flor" />
        <Hojas size={260} className="forma forma-hojas" />
        <Cuarto size={120} className="forma forma-cuarto" />
      </div>
      <div className="landing-centro">
        <h1>{saludo}</h1>
        <Composer onEnviar={onEnviar} deshabilitado={deshabilitado} placeholder="Pregunta lo que quieras" />
      </div>
    </main>
  );
}
