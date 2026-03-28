"""
tools/calendar_tools.py
========================
LangChain tool that reads your Google Calendar to find meals eaten recently.
It looks back a configurable number of days (default: 14) and returns
the event titles from your dedicated meals calendar.

Setup:
  - Enable the Google Calendar API in Google Cloud Console
  - Download credentials.json (OAuth 2.0 Desktop App)
  - Run `python auth/google_auth.py` once to generate token.json
  - Set MEALS_CALENDAR_ID in your .env file
"""

import os
import datetime
from langchain.tools import tool
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


LOOKBACK_DAYS = 14   # How many days back to check for recently eaten meals
TOKEN_PATH = "auth/token.json"


def _get_calendar_service():
    """Loads credentials from token.json and returns an authenticated Calendar service."""
    creds = Credentials.from_authorized_user_file(
        TOKEN_PATH,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"]
    )

    # Auto-refresh the token if it has expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


@tool
def get_recent_meals() -> str:
    """
    Returns meals eaten in the last 14 days by reading events from
    the Google Calendar dedicated to meal tracking.
    Use this to avoid recommending recipes that were prepared recently.
    """
    try:
        service = _get_calendar_service()

        now = datetime.datetime.utcnow()
        since = (now - datetime.timedelta(days=LOOKBACK_DAYS)).isoformat() + "Z"
        until = now.isoformat() + "Z"

        events_result = service.events().list(
            calendarId=os.environ["MEALS_CALENDAR_ID"],
            timeMin=since,
            timeMax=until,
            maxResults=100,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        if not events:
            return f"No meals recorded in the last {LOOKBACK_DAYS} days."

        meals = []
        for event in events:
            date_str = event["start"].get("date") or event["start"].get("dateTime", "")[:10]
            meals.append(f"- {date_str}: {event['summary']}")

        return (
            f"Meals eaten in the last {LOOKBACK_DAYS} days:\n"
            + "\n".join(meals)
        )

    except Exception as e:
        return f"Error reading Google Calendar: {e}"
