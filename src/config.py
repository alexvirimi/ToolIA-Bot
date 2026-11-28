from langchain_ollama import ChatOllama

MODEL_NAME = "qwen3.5:9b"


def get_llm():
    return ChatOllama(
        model=MODEL_NAME,
        temperature=0,  # Consistency is sought
        seed=42,  # For reproducibility
        num_predict=500,  # Max number of tokens to predict
        # Disable reasoning for faster responses (think=false)
        reasoning=False,
    )
