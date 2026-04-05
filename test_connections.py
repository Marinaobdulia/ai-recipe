#!/usr/bin/env python3
"""
test_connections.py
====================
Comprehensive test suite for all service connections in the AI Recipe agent.
Tests: Notion, Google Calendar, Google Drive, OpenAI, and authentication status.

Usage:
    python test_connections.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

# ───────────────────────────────────────────────────────────────────────────
# Color codes for terminal output
# ───────────────────────────────────────────────────────────────────────────

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

PASS = f"{Colors.GREEN}✅ PASS{Colors.ENDC}"
FAIL = f"{Colors.RED}❌ FAIL{Colors.ENDC}"
WARN = f"{Colors.YELLOW}⚠️  WARN{Colors.ENDC}"
INFO = f"{Colors.CYAN}ℹ️  INFO{Colors.ENDC}"

# ───────────────────────────────────────────────────────────────────────────
# Utility functions
# ───────────────────────────────────────────────────────────────────────────

def section(title: str):
    """Print a formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'─' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'─' * 70}{Colors.ENDC}")

def test_result(condition: bool, success_msg: str, fail_msg: str) -> bool:
    """Print a colored test result."""
    if condition:
        print(f"{PASS}  {success_msg}")
        return True
    else:
        print(f"{FAIL}  {fail_msg}")
        return False

def info_msg(msg: str):
    """Print an info message."""
    print(f"{INFO}  {msg}")

def masked_value(value: str, show_chars: int = 12) -> str:
    """Return a masked version of a sensitive value."""
    if len(value) <= show_chars:
        return value
    return f"{value[:show_chars]}..."

# ───────────────────────────────────────────────────────────────────────────
# Test 1: Environment Variables
# ───────────────────────────────────────────────────────────────────────────

def test_env_variables() -> dict:
    """Test that all required environment variables are set."""
    section("TEST 1 — Environment Variables")
    
    results = {}
    required_vars = {
        "NOTION_TOKEN": "Notion API token",
        "NOTION_DB_ID": "Notion database ID",
    }
    
    optional_vars = {
        "MEALS_CALENDAR_ID": "Google Calendar ID for meals",
        "DRIVE_FOLDER_ID": "Google Drive folder ID for tickets",
        "OPENAI_API_KEY": "OpenAI API key",
    }
    
    print(f"\n{Colors.BOLD}Required variables:{Colors.ENDC}")
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"{PASS}  {var:20} → {masked_value(value)}")
            results[f"env_{var}"] = True
        else:
            print(f"{FAIL}  {var:20} → NOT SET")
            results[f"env_{var}"] = False
    
    print(f"\n{Colors.BOLD}Optional variables:{Colors.ENDC}")
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"{PASS}  {var:20} → {masked_value(value)}")
            results[f"env_{var}"] = True
        else:
            print(f"{WARN}  {var:20} → NOT SET (feature may be disabled)")
            results[f"env_{var}"] = False
    
    return results

# ───────────────────────────────────────────────────────────────────────────
# Test 2: File Checks
# ───────────────────────────────────────────────────────────────────────────

def test_files() -> dict:
    """Test that required authentication files exist."""
    section("TEST 2 — Authentication Files")
    
    results = {}
    
    # Check token.json
    token_path = Path("auth/token.json")
    if token_path.exists():
        print(f"{PASS}  auth/token.json exists")
        results["file_token"] = True
        # Show token expiry info if available
        try:
            with open(token_path) as f:
                token_data = json.load(f)
                expiry = token_data.get("expires_in", "Unknown")
                info_msg(f"Token expiry info available")
        except:
            pass
    else:
        print(f"{FAIL}  auth/token.json NOT FOUND")
        print(f"       → Run: python auth/google_auth.py")
        results["file_token"] = False
    
    # Check credentials.json
    creds_path = Path("auth/credentials.json")
    if creds_path.exists():
        print(f"{PASS}  auth/credentials.json exists")
        results["file_credentials"] = True
    else:
        print(f"{WARN}  auth/credentials.json NOT FOUND")
        print(f"       → Download from Google Cloud Console if you need to re-authenticate")
        results["file_credentials"] = False
    
    return results

# ───────────────────────────────────────────────────────────────────────────
# Test 3: Notion Connection
# ───────────────────────────────────────────────────────────────────────────

def test_notion() -> dict:
    """Test Notion API connectivity and database access."""
    section("TEST 3 — Notion API")
    
    results = {}
    
    try:
        from tools.notion_tools import _get_notion_client
        
        # Test API connectivity
        print(f"\n{Colors.BOLD}Notion API connectivity:{Colors.ENDC}")
        try:
            notion = _get_notion_client()
            user = notion.users.me()
            print(f"{PASS}  Connected to Notion API")
            results["notion_api"] = True
        except Exception as e:
            print(f"{FAIL}  Could not connect to Notion API: {e}")
            results["notion_api"] = False
            return results
        
        # Test database access
        print(f"\n{Colors.BOLD}Database access:{Colors.ENDC}")
        try:
            db_id = os.environ.get("NOTION_DB_ID")
            db = notion.databases.retrieve(database_id=db_id)
            db_title = db.get("title", [{}])[0].get("plain_text", "(untitled)")
            print(f"{PASS}  Database accessible: '{db_title}'")
            results["notion_db"] = True
        except Exception as e:
            print(f"{FAIL}  Could not access database: {e}")
            print(f"       → Check NOTION_DB_ID and database sharing with integration")
            results["notion_db"] = False
            return results
        
        # Test recipe tools
        print(f"\n{Colors.BOLD}Recipe tools:{Colors.ENDC}")
        try:
            from tools.notion_tools import get_recipe_list, get_recipe_details
            
            # Test get_recipe_list
            recipe_list = get_recipe_list.invoke({})
            if not recipe_list.startswith("Error"):
                recipes = recipe_list.split("\n")
                print(f"{PASS}  get_recipe_list() works")
                print(f"       Found {len(recipes)} recipes")
                results["notion_tools"] = True
                
                # Try to fetch details of first recipe if available
                if recipes and len(recipes) > 0:
                    first_recipe = recipes[0].strip()
                    if first_recipe:
                        try:
                            details = get_recipe_details.invoke({"recipe_name": first_recipe})
                            if not details.startswith("Error"):
                                print(f"{PASS}  get_recipe_details() works")
                                info_msg(f"Sample recipe: {first_recipe[:50]}...")
                        except Exception as e:
                            print(f"{WARN}  Could not fetch recipe details: {e}")
            else:
                print(f"{FAIL}  get_recipe_list() returned error: {recipe_list}")
                results["notion_tools"] = False
        except Exception as e:
            print(f"{FAIL}  Error testing recipe tools: {e}")
            results["notion_tools"] = False
    
    except ImportError as e:
        print(f"{FAIL}  Could not import Notion tools: {e}")
        results["notion_api"] = False
        results["notion_db"] = False
        results["notion_tools"] = False
    
    return results

# ───────────────────────────────────────────────────────────────────────────
# Test 4: Google Calendar Connection
# ───────────────────────────────────────────────────────────────────────────

def test_google_calendar() -> dict:
    """Test Google Calendar API connectivity."""
    section("TEST 4 — Google Calendar API")
    
    results = {}
    
    try:
        from tools.calendar_tools import _get_calendar_service
        from googleapiclient.errors import HttpError
        
        print(f"\n{Colors.BOLD}Calendar service:{Colors.ENDC}")
        try:
            service = _get_calendar_service()
            print(f"{PASS}  Connected to Google Calendar API")
            results["calendar_api"] = True
        except FileNotFoundError as e:
            print(f"{FAIL}  token.json not found: {e}")
            print(f"       → Run: python auth/google_auth.py")
            results["calendar_api"] = False
            return results
        except Exception as e:
            print(f"{FAIL}  Could not connect to Calendar API: {e}")
            results["calendar_api"] = False
            return results
        
        # Test fetching calendar events
        print(f"\n{Colors.BOLD}Calendar events:{Colors.ENDC}")
        try:
            calendar_id = os.environ.get("MEALS_CALENDAR_ID")
            if not calendar_id:
                print(f"{WARN}  MEALS_CALENDAR_ID not set (skipping events check)")
                results["calendar_events"] = False
            else:
                events = service.events().list(
                    calendarId=calendar_id,
                    maxResults=5,
                    orderBy="startTime",
                    singleEvents=True
                ).execute()
                
                event_list = events.get("items", [])
                print(f"{PASS}  Retrieved calendar events")
                print(f"       Latest {len(event_list)} events from calendar")
                results["calendar_events"] = True
        except HttpError as e:
            if "notFound" in str(e):
                print(f"{FAIL}  Calendar ID not found or not accessible")
                print(f"       → Check MEALS_CALENDAR_ID in .env")
            else:
                print(f"{FAIL}  Could not fetch calendar events: {e}")
            results["calendar_events"] = False
        except Exception as e:
            print(f"{WARN}  Could not fetch calendar events: {e}")
            results["calendar_events"] = False
    
    except ImportError as e:
        print(f"{FAIL}  Could not import calendar tools: {e}")
        results["calendar_api"] = False
        results["calendar_events"] = False
    
    return results

# ───────────────────────────────────────────────────────────────────────────
# Test 5: Google Drive Connection
# ───────────────────────────────────────────────────────────────────────────

def test_google_drive() -> dict:
    """Test Google Drive API connectivity."""
    section("TEST 5 — Google Drive API")
    
    results = {}
    
    try:
        from tools.drive_tools import _get_drive_service
        from googleapiclient.errors import HttpError
        
        print(f"\n{Colors.BOLD}Drive service:{Colors.ENDC}")
        try:
            service = _get_drive_service()
            print(f"{PASS}  Connected to Google Drive API")
            results["drive_api"] = True
        except FileNotFoundError as e:
            print(f"{FAIL}  token.json not found: {e}")
            results["drive_api"] = False
            return results
        except Exception as e:
            print(f"{FAIL}  Could not connect to Drive API: {e}")
            results["drive_api"] = False
            return results
        
        # Test accessing the folder
        print(f"\n{Colors.BOLD}Drive folder access:{Colors.ENDC}")
        try:
            folder_id = os.environ.get("DRIVE_FOLDER_ID")
            if not folder_id:
                print(f"{WARN}  DRIVE_FOLDER_ID not set (skipping folder check)")
                results["drive_folder"] = False
            else:
                # List files in the folder
                results_list = service.files().list(
                    q=f"'{folder_id}' in parents and mimeType='application/pdf'",
                    pageSize=10,
                    fields="files(id, name, mimeType, createdTime)"
                ).execute()
                
                files = results_list.get("files", [])
                print(f"{PASS}  Drive folder accessible")
                print(f"       Found {len(files)} PDF files in folder")
                if files:
                    print(f"       Latest: {files[0]['name']}")
                results["drive_folder"] = True
        except HttpError as e:
            if "notFound" in str(e):
                print(f"{FAIL}  Folder ID not found or not accessible")
                print(f"       → Check DRIVE_FOLDER_ID in .env")
            else:
                print(f"{FAIL}  Could not access drive folder: {e}")
            results["drive_folder"] = False
        except Exception as e:
            print(f"{WARN}  Could not access drive folder: {e}")
            results["drive_folder"] = False
    
    except ImportError as e:
        print(f"{FAIL}  Could not import drive tools: {e}")
        results["drive_api"] = False
        results["drive_folder"] = False
    
    return results

# ───────────────────────────────────────────────────────────────────────────
# Test 6: OpenAI Connection
# ───────────────────────────────────────────────────────────────────────────

def test_openai() -> dict:
    """Test OpenAI API connectivity."""
    section("TEST 6 — OpenAI API")
    
    results = {}
    
    try:
        from openai import OpenAI
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print(f"{WARN}  OPENAI_API_KEY not set")
            results["openai_api"] = False
            return results
        
        print(f"\n{Colors.BOLD}OpenAI API connectivity:{Colors.ENDC}")
        try:
            client = OpenAI(api_key=api_key)
            # Do a simple test call
            response = client.models.list()
            print(f"{PASS}  Connected to OpenAI API")
            print(f"       Available models: {len(response.data)} models accessible")
            results["openai_api"] = True
        except Exception as e:
            print(f"{FAIL}  Could not connect to OpenAI API: {e}")
            print(f"       → Check OPENAI_API_KEY validity")
            results["openai_api"] = False
    
    except ImportError as e:
        print(f"{WARN}  OpenAI library not imported: {e}")
        results["openai_api"] = False
    
    return results

# ───────────────────────────────────────────────────────────────────────────
# Test 7: System Dependencies
# ───────────────────────────────────────────────────────────────────────────

def test_system_dependencies() -> dict:
    """Test that system dependencies are installed."""
    section("TEST 7 — System Dependencies")
    
    results = {}
    import subprocess
    
    dependencies = {
        "tesseract": "Tesseract OCR (needed for scanned PDFs)",
        "poppler-utils": "Poppler (needed by pdf2image)",
    }
    
    print(f"\n{Colors.BOLD}System tools:{Colors.ENDC}")
    for cmd, description in dependencies.items():
        # Try to run the command to check if it exists
        try:
            result = subprocess.run(
                ["which", cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"{PASS}  {description}")
                results[f"sys_{cmd}"] = True
            else:
                print(f"{WARN}  {description} NOT found")
                results[f"sys_{cmd}"] = False
        except Exception as e:
            print(f"{WARN}  Could not check for {cmd}: {e}")
            results[f"sys_{cmd}"] = False
    
    return results

# ───────────────────────────────────────────────────────────────────────────
# Test 8: Python Dependencies
# ───────────────────────────────────────────────────────────────────────────

def test_python_dependencies() -> dict:
    """Test that Python dependencies are installed."""
    section("TEST 8 — Python Dependencies")
    
    results = {}
    
    dependencies = [
        ("langchain", "LangChain"),
        ("langchain_openai", "LangChain OpenAI"),
        ("langgraph", "LangGraph"),
        ("notion_client", "Notion Client"),
        ("google.auth", "Google Auth"),
        ("googleapiclient", "Google API Client"),
        ("pdfplumber", "PDFPlumber"),
        ("pdf2image", "PDF2Image"),
        ("pytesseract", "PyTesseract"),
        ("openai", "OpenAI"),
        ("dotenv", "Python Dotenv"),
        ("telegram", "Python Telegram Bot"),
    ]
    
    print(f"\n{Colors.BOLD}Required Python packages:{Colors.ENDC}")
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"{PASS}  {name}")
            results[f"dep_{module}"] = True
        except ImportError:
            print(f"{FAIL}  {name} NOT installed")
            print(f"       → Run: pip install -r requirements.txt")
            results[f"dep_{module}"] = False
    
    return results

# ───────────────────────────────────────────────────────────────────────────
# Summary Report
# ───────────────────────────────────────────────────────────────────────────

def print_summary(all_results: dict):
    """Print a summary of all test results."""
    section("SUMMARY")
    
    passed = sum(1 for v in all_results.values() if v)
    total = len(all_results)
    
    print(f"\n{Colors.BOLD}Test Results:{Colors.ENDC}")
    print(f"  Passed: {Colors.GREEN}{passed}{Colors.ENDC}/{total}")
    print(f"  Failed: {Colors.RED}{total - passed}{Colors.ENDC}/{total}")
    
    # Calculate success percentage
    percentage = (passed / total * 100) if total > 0 else 0
    
    if percentage == 100:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All systems operational!{Colors.ENDC}")
    elif percentage >= 75:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Most systems operational, some features may be limited{Colors.ENDC}")
    elif percentage >= 50:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some core systems offline, basic operation may be affected{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Multiple failures detected, check configuration{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}Breakdown by category:{Colors.ENDC}")
    
    # Group results by category
    categories = {
        "Environment": [k for k in all_results.keys() if k.startswith("env_")],
        "Files": [k for k in all_results.keys() if k.startswith("file_")],
        "Notion": [k for k in all_results.keys() if k.startswith("notion_")],
        "Calendar": [k for k in all_results.keys() if k.startswith("calendar_")],
        "Drive": [k for k in all_results.keys() if k.startswith("drive_")],
        "OpenAI": [k for k in all_results.keys() if k.startswith("openai_")],
        "System": [k for k in all_results.keys() if k.startswith("sys_")],
        "Dependencies": [k for k in all_results.keys() if k.startswith("dep_")],
    }
    
    for category, keys in categories.items():
        if not keys:
            continue
        cat_passed = sum(1 for k in keys if all_results[k])
        cat_total = len(keys)
        status = Colors.GREEN if cat_passed == cat_total else Colors.RED if cat_passed == 0 else Colors.YELLOW
        print(f"  {status}{category:15} {cat_passed}/{cat_total}{Colors.ENDC}")

# ───────────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────────

def main():
    """Run all tests."""
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("╔" + "─" * 68 + "╗")
    print("║" + " " * 15 + "AI Recipe Agent — Connection Test Suite" + " " * 13 + "║")
    print("╚" + "─" * 68 + "╝")
    print(f"{Colors.ENDC}")
    
    all_results = {}
    
    # Run all tests
    all_results.update(test_env_variables())
    all_results.update(test_files())
    all_results.update(test_notion())
    all_results.update(test_google_calendar())
    all_results.update(test_google_drive())
    all_results.update(test_openai())
    all_results.update(test_system_dependencies())
    all_results.update(test_python_dependencies())
    
    # Print summary
    print_summary(all_results)
    
    print(f"\n{Colors.BOLD}Next steps:{Colors.ENDC}")
    print("  1. Fix any FAIL items above")
    print("  2. Check .env file has all required variables")
    print("  3. Run: python auth/google_auth.py (if needed)")
    print("  4. Re-run this test to confirm everything works")
    print()

if __name__ == "__main__":
    main()
