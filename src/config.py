from langchain_ollama import ChatOllama

MODEL_NAME = "qwen3.5:9b"


def get_llm():
    return ChatOllama(
        model=MODEL_NAME,
        temperature=0,  # Se busca consistencia
        seed=42,  # Para reproducibilidad
        num_predict=500,  # Max numero de tokens a predecir
        # Desactivar razonamiento para respuestas más rápidas (think=false)
        reasoning=False,
    )
