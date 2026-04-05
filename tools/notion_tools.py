"""
tools/notion_tools.py
=====================
Two LangChain tools for interacting with a Notion recipe database.
Compatible with notion-client 2.x (current stable as of March 2026).

  - get_recipe_list    → returns just the names of all recipes
  - get_recipe_details → fetches the full body (ingredients + instructions) of one recipe
"""

import os
from datetime import datetime, timedelta
from langchain.tools import tool
from notion_client import Client


# Cache for recipe list: (timestamp, data)
_recipe_list_cache = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _get_notion_client() -> Client:
    return Client(auth=os.environ["NOTION_TOKEN"])


def _extract_text_from_blocks(blocks: list) -> str:
    """
    Recursively extracts plain text from a list of Notion block objects.
    Handles: paragraph, bulleted_list_item, numbered_list_item,
             heading_1/2/3, toggle, quote, callout, to_do.
    """
    lines = []

    TEXT_BLOCK_TYPES = {
        "paragraph",
        "bulleted_list_item",
        "numbered_list_item",
        "heading_1",
        "heading_2",
        "heading_3",
        "toggle",
        "quote",
        "callout",
        "to_do",
    }

    for block in blocks:
        block_type = block.get("type", "")

        if block_type in TEXT_BLOCK_TYPES:
            rich_text = block.get(block_type, {}).get("rich_text", [])
            line = "".join(t["plain_text"] for t in rich_text)

            if block_type == "bulleted_list_item":
                line = f"• {line}"
            elif block_type == "numbered_list_item":
                line = f"- {line}"
            elif block_type == "to_do":
                checked = block.get("to_do", {}).get("checked", False)
                line = f"[{'x' if checked else ' '}] {line}"

            if line.strip():
                lines.append(line)

        # Recurse into children if present (e.g. toggles with nested content)
        if block.get("has_children"):
            try:
                notion = _get_notion_client()
                child_blocks = notion.blocks.children.list(block_id=block["id"])
                nested = _extract_text_from_blocks(child_blocks["results"])
                if nested:
                    lines.append(nested)
            except Exception:
                pass

    return "\n".join(lines)


def _get_title_from_page(page: dict) -> str:
    """Extracts the title from a Notion page object regardless of property name."""
    for prop in page["properties"].values():
        if prop["type"] == "title" and prop["title"]:
            return prop["title"][0]["plain_text"]
    return "Unnamed Recipe"


@tool
def get_recipe_list() -> str:
    """
    Returns the names of ALL recipes in the Notion recipe database.
    Use this first to see what recipes are available before fetching details.
    """
    # Check cache
    global _recipe_list_cache
    now = datetime.now()
    if _recipe_list_cache and (now - _recipe_list_cache["timestamp"]).total_seconds() < CACHE_TTL_SECONDS:
        return _recipe_list_cache["data"]
    
    try:
        notion = _get_notion_client()
        db_id = os.environ["NOTION_DB_ID"]

        results = notion.databases.query(database_id=db_id)
        names = [_get_title_from_page(page) for page in results["results"]]

        while results.get("has_more"):
            results = notion.databases.query(
                database_id=db_id,
                start_cursor=results["next_cursor"],
            )
            names.extend(_get_title_from_page(p) for p in results["results"])

        if not names:
            result = "No recipes found."
        else:
            result = ", ".join(names)

        # Cache the result
        _recipe_list_cache = {"timestamp": now, "data": result}
        return result

    except Exception as e:
        return f"Error fetching recipe list: {e}"


@tool
def get_recipe_details(recipe_name: str) -> str:
    """
    Fetches the full body content (ingredients and instructions) of a specific
    recipe from Notion by searching for its name.
    Use this after narrowing down candidates with get_recipe_list.

    Args:
        recipe_name: The name of the recipe to look up (partial match is fine).
    """
    try:
        notion = _get_notion_client()
        db_id = os.environ["NOTION_DB_ID"]

        results = notion.databases.query(
            database_id=db_id,
            filter={
                "property": "Name",
                "title": {
                    "contains": recipe_name
                }
            }
        )

        if not results["results"]:
            return f"Recipe '{recipe_name}' not found."

        page = results["results"][0]
        title = _get_title_from_page(page)
        page_id = page["id"]

        blocks_response = notion.blocks.children.list(block_id=page_id)
        body = _extract_text_from_blocks(blocks_response["results"])

        if not body.strip():
            return f"{title}\n(No content)"

        return f"{title}\n{body}"

    except Exception as e:
        return f"Error fetching recipe: {e}"
