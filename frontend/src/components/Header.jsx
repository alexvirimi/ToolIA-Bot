import { Logo } from "../shapes/Shapes.jsx";

export default function Header({ conversando, onNueva }) {
  return (
    <header className={`encabezado${conversando ? " con-linea" : ""}`}>
      <div className="marca">
        <Logo size={26} className="marca-logo" />
        <span className="marca-nombre">ToolIA</span>
      </div>
      {conversando && (
        <nav className="acciones" aria-label="Acciones">
          <a className="boton" href="https://www.utb.edu.co/" target="_blank" rel="noopener noreferrer">
            Visita la página de la UTB
          </a>
          <button className="boton" type="button" onClick={onNueva}>
            Habla con Tooli
          </button>
        </nav>
      )}
    </header>
  );
}
