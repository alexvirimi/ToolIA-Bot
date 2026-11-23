from langchain_core.output_parsers import StrOutputParser
import sys
from pathlib import Path

# Este archivo está en src/baseline/, src/ es parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prompts import base_prompt
from config import get_llm


chain = base_prompt | get_llm() | StrOutputParser()

while True:
    user_input = input("Pregunta usuario: ")
    if user_input.lower() in ["exit", "quit", "salir", "terminar"]:
        print("¡Hasta luego!")
        break

    respuesta = chain.invoke({"pregunta": user_input})
    print(f"ToolIA: {respuesta}")
