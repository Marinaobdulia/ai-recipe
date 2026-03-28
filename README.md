# 🍽️ Recipe Recommendation Agent

A LangChain AI agent that answers **"What should I cook today?"** by combining:

- 📒 **Notion** — your personal recipe database (reads page body for ingredients)
- 📅 **Google Calendar** — your meal history (avoids recent repeats)
- 🛒 **Google Drive** — supermarket ticket PDFs (tailors to available ingredients)

---

## Project Structure

```
recipe_agent/
├── agent.py                  # Main entry point
├── tools/
│   ├── notion_tools.py       # get_recipe_list + get_recipe_details
│   ├── calendar_tools.py     # get_recent_meals
│   └── drive_tools.py        # get_available_ingredients (PDF tickets)
├── auth/
│   ├── google_auth.py        # Run once to generate token.json
│   └── credentials.json      # ← You provide this (from Google Cloud)
├── .env.example              # Copy to .env and fill in your values
└── requirements.txt
```

---

## Setup Guide

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Install Tesseract OCR on your system (needed only for scanned/image PDFs):

```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu / Debian
sudo apt install tesseract-ocr tesseract-ocr-spa
```

Install Poppler (needed by pdf2image):

```bash
# macOS
brew install poppler

# Ubuntu / Debian
sudo apt install poppler-utils
```

---

### 2. Set up Notion

1. Go to https://www.notion.so/my-integrations and create a new integration.
2. Copy the **Internal Integration Token** → this is your `NOTION_TOKEN`.
3. Open your recipe database in Notion → click the `...` menu → **Connections** → add your integration.
4. Copy the database ID from the URL:
   `notion.so/yourworkspace/DATABASE_ID_HERE?v=...`
   → this is your `NOTION_DB_ID`.

**Your recipe pages can have any structure** — the agent reads the full page body,
so ingredients and instructions can be in paragraphs, bullet lists, toggles, etc.

If your title property is not named `"Name"`, update this line in `tools/notion_tools.py`:
```python
filter={"property": "Name", ...}
```

---

### 3. Set up Google APIs

#### Enable APIs
1. Go to https://console.cloud.google.com
2. Create a project (or use an existing one).
3. Enable these two APIs:
   - **Google Calendar API**
   - **Google Drive API**

#### Create OAuth credentials
1. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
2. Choose **Desktop App**.
3. Download the JSON file and save it as `auth/credentials.json`.

#### Authenticate (run once)
```bash
python auth/google_auth.py
```
This opens a browser window. Log in with your Google account and grant access.
A `auth/token.json` file will be created — the agent uses this automatically from now on.

---

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to find it |
|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `NOTION_TOKEN` | Notion integrations page |
| `NOTION_DB_ID` | Notion database URL |
| `MEALS_CALENDAR_ID` | Google Calendar → Settings → your calendar → Calendar ID |
| `DRIVE_FOLDER_ID` | Google Drive folder URL (the last part after `/folders/`) |

---

### 5. Set up your Google Drive folder

Create a folder in Google Drive where you'll drop your supermarket ticket PDFs.
Copy the folder ID from the URL and set it as `DRIVE_FOLDER_ID` in `.env`.

The agent supports:
- **Digital PDFs** (e.g. emailed receipts) → extracted with `pdfplumber`
- **Scanned PDFs** (e.g. photographed paper tickets, exported as PDF) → OCR with `pytesseract`

---

## Running the Agent

```bash
python agent.py
```

Example output:
```
============================================================
🍽️  TODAY'S RECOMMENDATION
============================================================
I'd suggest making **Pasta e Fagioli** tonight! You haven't
had it in over two weeks, and you recently bought canned
beans, pasta, and tomatoes — so you have everything you need.
It's hearty, quick, and perfect for a weekday dinner.
============================================================
```

---

## How the Agent Reasons

1. **get_recent_meals** → finds what you've eaten in the last 14 days
2. **get_recipe_list** → fetches all recipe names from Notion
3. **get_available_ingredients** → reads your last 5 supermarket ticket PDFs
4. Shortlists 2–3 recipes that haven't been made recently and match available ingredients
5. **get_recipe_details** → reads the page body for each candidate to confirm ingredients
6. Returns ONE recommendation with a friendly explanation

---

## Tips

- **Add meals to Calendar** as all-day events with the recipe name as the title.
- **Drop PDF tickets** into your Drive folder after each supermarket trip.
- You can adjust `LOOKBACK_DAYS` in `calendar_tools.py` (default: 14 days).
- You can adjust `MAX_TICKETS` in `drive_tools.py` (default: last 5 tickets).
