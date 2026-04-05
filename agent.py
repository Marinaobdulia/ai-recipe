"""
Recipe Recommendation Agent
============================
Main entry point. Runs the LangChain agent that recommends what to cook today
based on:
  - Your Notion recipe database (ingredients stored inside each page body)
  - Your Google Calendar meal history (avoids recent repeats)
  - Your supermarket PDF tickets from Google Drive (tailors to available ingredients)

Uses LangGraph's create_react_agent (current recommended approach as of LangChain 0.3+).
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from tools.notion_tools import get_recipe_list, get_recipe_details
from tools.calendar_tools import get_recent_meals
from tools.drive_tools import get_available_ingredients

load_dotenv()

SYSTEM_PROMPT = """Asistente de cocina casera.

Herramientas:
- get_recent_meals
- get_recipe_list
- get_available_ingredients
- get_recipe_details

Siempre:
1. Consulta comidas recientes.
2. Consulta recetas disponibles.
3. Consulta ingredientes comprados.
4. Elige 2 recetas no comidas en 7 días y compatibles con el último ticket (pueden faltar frutas, verduras frescas, carne y pollo).
5. Verifica cada una con get_recipe_details.
6. Recomienda UNA con motivo breve.
7. Responde en español.

Sé cálido, breve y da solo la recomendación final con la razón principal."""


def build_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    tools = [
        get_recipe_list,
        get_recipe_details,
        get_recent_meals,
        get_available_ingredients,
    ]

    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

def run_agent():
    agent = build_agent()

    response = agent.invoke({
        "messages": [HumanMessage(content="What recipe should I make today?")]
    })

    # The final answer is the last message in the response
    return response["messages"][-1].content


def main():
    final_message = run_agent()

    print("\n" + "=" * 60)
    print("🍽️  RECOMENDACIÓN DEL DÍA")
    print("=" * 60)
    print(final_message)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
