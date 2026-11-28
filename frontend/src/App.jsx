import Header from "./components/Header.jsx";
import Landing from "./components/Landing.jsx";
import ChatView from "./components/ChatView.jsx";
import { useChat } from "./hooks/useChat.js";

export default function App() {
  const { mensajes, cargando, enviar, reintentar, nuevaConversacion } = useChat();
  const conversando = mensajes.length > 0;

  return (
    <div className="app">
      <Header conversando={conversando} onNueva={nuevaConversacion} />
      {conversando ? (
        <ChatView mensajes={mensajes} cargando={cargando} onEnviar={enviar} onReintentar={reintentar} />
      ) : (
        <Landing onEnviar={enviar} deshabilitado={cargando} />
      )}
    </div>
  );
}
