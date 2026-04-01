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

SYSTEM_PROMPT = """You are a helpful home chef assistant. Your job is to recommend
the best recipe to cook today. You have access to the following tools:

- get_recipe_list: returns the names of all recipes available in the Notion database.
- get_recipe_details: fetches the full ingredients and instructions for a specific recipe by name.
- get_recent_meals: returns meals eaten in the last 14 days from Google Calendar.
- get_available_ingredients: reads recent supermarket PDF tickets from Google Drive
  and returns a list of recently purchased ingredients.

Follow this reasoning process ALWAYS:
1. Call get_recent_meals to know what has been eaten recently.
2. Call get_recipe_list to see all available recipes.
3. Call get_available_ingredients to know what ingredients are at home.
4. Based on the above, shortlist 2-3 recipes that:
   a. Have NOT been eaten in the last 4 days.
   b. Can be made with ingredients that have been purchased on the last ticket available,
   except for fresh vegetables and fruits, meat and poultry. These won't be shown on the 
   ticket as they are bought separately.
5. Call get_recipe_details for each shortlisted recipe to confirm ingredients.
6. Recommend ONE recipe with a brief, friendly explanation of why it's a great choice today.
7. Answer in Spanish.

Be concise and warm in your final answer. Do not list all recipes or all ingredients —
just give the final recommendation and the key reason."""


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
