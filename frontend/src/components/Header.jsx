import { Logo } from "../shapes/Shapes.jsx";

export default function Header({ conversando, onNueva }) {
  return (
    <header className={`encabezado${conversando ? " con-linea" : ""}`}>
      <div
        className="marca"
        onClick={onNueva}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onNueva();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Iniciar una nueva conversación"
      >
        <Logo size={26} className="marca-logo" />
        <span className="marca-nombre">ToolIA</span>
      </div>
      {conversando && (
        <nav className="acciones" aria-label="Acciones">
          <a className="boton" href="https://www.utb.edu.co/" target="_blank" rel="noopener noreferrer">
            Visita la página de la UTB
          </a>
          <a className="boton" href="https://www.utb.edu.co/tooli/" target="_blank" rel="noopener noreferrer">
            Habla con Tooli
          </a>
        </nav>
      )}
    </header>
  );
}
