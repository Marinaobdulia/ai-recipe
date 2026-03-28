"""
tests/test_notion_tools.py
===========================
Standalone test for the Notion tools. Runs directly against the Notion API
without invoking the LLM — no OpenAI tokens are spent.

Compatible with notion-client 3.0.0:
  - DB metadata:  notion.databases.retrieve(database_id=...)
  - Query pages:  notion.data_sources.query(data_source_id=...)
  - Page blocks:  notion.blocks.children.list(...)

Usage (from the project root):
    python tests/test_notion_tools.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from tools.notion_tools import (
    _get_notion_client,
    _get_title_from_page,
    get_recipe_list,
    get_recipe_details,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_env_vars():
    section("TEST 1 — Environment variables")
    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_DB_ID")

    if not token:
        print(f"{FAIL}  NOTION_TOKEN is not set in .env")
        return False
    if not db_id:
        print(f"{FAIL}  NOTION_DB_ID is not set in .env")
        return False

    print(f"{PASS}  NOTION_TOKEN found: {token[:12]}...")
    print(f"{PASS}  NOTION_DB_ID found: {db_id}")
    return True


def test_connectivity():
    section("TEST 2 — Notion API connectivity")
    try:
        notion = _get_notion_client()
        notion.users.me()
        print(f"{PASS}  Connected to Notion API successfully")
        return True
    except Exception as e:
        print(f"{FAIL}  Could not connect to Notion: {e}")
        print("       → Check that NOTION_TOKEN is correct and the integration is active")
        return False


def test_database_access():
    section("TEST 3 — Database access")
    try:
        notion = _get_notion_client()
        db_id = os.environ["NOTION_DB_ID"]

        # databases.retrieve still works in notion-client 3.0.0 for fetching DB metadata
        result = notion.databases.retrieve(database_id=db_id)
        db_title = result.get("title", [{}])[0].get("plain_text", "(untitled)")
        print(f"{PASS}  Database found: '{db_title}'")
        print(f"       DB ID: {db_id}")
        print(result)
        return True, result
    except Exception as e:
        print(f"{FAIL}  Could not access the database: {e}")
        print("       → Make sure you shared the database with your Notion integration")
        print("         (Notion DB → ··· menu → Connections → your integration)")
        return False, None


def test_recipe_list():
    section("TEST 4 — get_recipe_list tool")
    try:
        result = get_recipe_list.invoke({})

        if result.startswith("Error"):
            print(f"{FAIL}  Tool returned an error:\n       {result}")
            return False, []

        lines = [l for l in result.splitlines() if l.startswith("- ")]
        count = len(lines)

        if count == 0:
            print(f"{WARN}  Tool ran successfully but found 0 recipes")
            print("       → Is the database empty? Check NOTION_DB_ID points to the right DB")
            return False, []

        print(f"{PASS}  Found {count} recipe(s)")
        for line in lines[:5]:
            print(f"       {line}")
        if count > 5:
            print(f"       ... and {count - 5} more")

        names = [l[2:].strip() for l in lines]
        return True, names

    except Exception as e:
        print(f"{FAIL}  Unexpected exception: {e}")
        return False, []


def test_title_property(db_result: dict):
    section("TEST 5 — Title property name (used by get_recipe_details filter)")
    if not db_result:
        print(f"{WARN}  Skipped — no DB metadata available from Test 3")
        return

    try:
        props = db_result.get("properties", {})
        title_props = [k for k, v in props.items() if v["type"] == "title"]

        if not title_props:
            print(f"{FAIL}  No title property found in the database schema")
            return

        actual_title_prop = title_props[0]

        if actual_title_prop == "Name":
            print(f"{PASS}  Title property is named 'Name' — filter will work correctly")
        else:
            print(f"{WARN}  Title property is named '{actual_title_prop}', not 'Name'")
            print(f"       → Update this line in tools/notion_tools.py:")
            print(f'            filter={{"property": "Name", ...}}')
            print(f"       → Change 'Name' to '{actual_title_prop}'")

        print(f"       All properties found: {list(props.keys())}")

    except Exception as e:
        print(f"{FAIL}  Could not read DB schema: {e}")


def test_recipe_details(names: list):
    section("TEST 6 — get_recipe_details tool (fetches page body)")
    if not names:
        print(f"{WARN}  Skipped — no recipe names available from Test 4")
        return

    first_recipe = names[0]
    print(f"       Testing with: '{first_recipe}'")

    try:
        result = get_recipe_details.invoke({"recipe_name": first_recipe})

        if result.startswith("Error"):
            print(f"{FAIL}  Tool returned an error:\n       {result}")
            return

        if "not found" in result.lower():
            print(f"{FAIL}  Recipe not found via filter")
            print("       → This is likely a title property name mismatch (see TEST 5)")
            print(f"       Full response: {result}")
            return

        if "appears to be empty" in result:
            print(f"{WARN}  Recipe found but page body is empty")
            print(f"       → Add some content to the '{first_recipe}' page in Notion")
            return

        preview = result[:300].replace("\n", "\n       ")
        print(f"{PASS}  Page body retrieved successfully")
        print(f"       Preview:\n       {preview}")
        if len(result) > 300:
            print(f"       ... ({len(result)} total characters)")

    except Exception as e:
        print(f"{FAIL}  Unexpected exception: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  NOTION TOOLS — STANDALONE TEST")
    print("  notion-client 3.0.0 compatible")
    print("  No OpenAI API calls are made in this test.")
    print("=" * 60)

    if not test_env_vars():
        print("\n⛔  Cannot continue without env vars. Check your .env file.\n")
        sys.exit(1)

    if not test_connectivity():
        print("\n⛔  Cannot continue without Notion connectivity.\n")
        sys.exit(1)

    db_ok, db_result = test_database_access()
    if not db_ok:
        print("\n⛔  Cannot continue without database access.\n")
        sys.exit(1)

    ok, names = test_recipe_list()

    test_title_property(db_result)

    if ok:
        test_recipe_details(names)

    print("\n" + "=" * 60)
    if ok and names:
        print("  All core tests passed. Notion tools are working correctly.")
    else:
        print("  Some tests failed. Review the output above for guidance.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
