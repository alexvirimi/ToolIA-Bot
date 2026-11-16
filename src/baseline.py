
from config import get_llm
from prompts import base_prompt
from langchain_core.output_parsers import StrOutputParser

chain = base_prompt | get_llm() | StrOutputParser()

while True:
    user_input = input("Usuario: ")
    if user_input.lower() in ["exit", "quit", "salir", "terminar"]:
        print("¡Hasta luego!")
        break

    respuesta = chain.invoke({"pregunta": user_input})
    print(f"ToolIA: {respuesta}")
