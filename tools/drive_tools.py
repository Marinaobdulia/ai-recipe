"""
tools/drive_tools.py
=====================
LangChain tool that reads supermarket ticket PDFs from a Google Drive folder
and extracts purchased ingredients using two strategies:

  1. pdfplumber  — fast text extraction for digital/native PDFs
  2. OCR fallback — pdf2image + pytesseract for scanned/image-based PDFs

The extracted text is then summarised by GPT-4o-mini into a clean ingredient list.

Setup:
  - Enable the Google Drive API in Google Cloud Console
  - The same token.json used for Calendar works (add the Drive scope)
  - Set DRIVE_FOLDER_ID in your .env (folder where you drop ticket PDFs)
  - pip install pdfplumber pdf2image pytesseract
  - Install Tesseract OCR on your system:
      macOS:  brew install tesseract
      Ubuntu: sudo apt install tesseract-ocr
"""

import os
import io
import tempfile
import datetime
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_PATH = "auth/token.json"
MAX_TICKETS = 2          # How many recent PDFs to read
MIN_TEXT_LENGTH = 50     # Characters threshold to decide if OCR is needed

# Cache for ingredients: (timestamp, data)
_ingredients_cache = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _get_drive_service():
    """Loads credentials from token.json and returns an authenticated Drive service."""
    creds = Credentials.from_authorized_user_file(
        TOKEN_PATH,
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def _download_pdf_bytes(service, file_id: str) -> bytes:
    """Downloads a file from Google Drive and returns its raw bytes."""
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def _extract_text_pdfplumber(pdf_bytes: bytes) -> str:
    """Extracts text from a native/digital PDF using pdfplumber."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)


def _extract_text_ocr(pdf_bytes: bytes) -> str:
    """
    Fallback: converts PDF pages to images and runs Tesseract OCR.
    Used when pdfplumber returns little or no text (scanned receipts).
    """
    import pytesseract
    from pdf2image import convert_from_bytes

    images = convert_from_bytes(pdf_bytes, dpi=200)
    text_parts = []
    for image in images:
        text = pytesseract.image_to_string(image, lang="spa+eng")  # Spanish + English
        if text.strip():
            text_parts.append(text)

    return "\n".join(text_parts)


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Smart extraction: tries pdfplumber first.
    Falls back to OCR if the extracted text is too short (scanned PDF).
    """
    text = _extract_text_pdfplumber(pdf_bytes)

    if len(text.strip()) < MIN_TEXT_LENGTH:
        print("  [drive_tools] Native text extraction yielded little content — falling back to OCR")
        text = _extract_text_ocr(pdf_bytes)

    return text


def _summarise_ingredients(raw_texts: list[str]) -> str:
    """
    Sends the raw receipt texts to GPT-4o-mini (cheaper than GPT-4o) and asks it to extract
    a clean, deduplicated list of food ingredients/products.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    combined = "\n\n---\n\n".join(raw_texts)

    prompt = f"""Extract food products from supermarket receipts.
- Ignore non-food items
- Deduplicate similar items
- Return comma-separated list only

{combined}"""
    response = llm.invoke([{"role": "user", "content": prompt}])
    return response.content.strip()


@tool
def get_available_ingredients() -> str:
    """
    Reads recent supermarket ticket PDFs from Google Drive and returns
    a list of recently purchased food ingredients.
    """
    # Check cache
    global _ingredients_cache
    now = datetime.datetime.utcnow()
    if _ingredients_cache and (now - _ingredients_cache["timestamp"]).total_seconds() < CACHE_TTL_SECONDS:
        return _ingredients_cache["data"]
    
    try:
        service = _get_drive_service()

        # List the most recent PDF files in the configured folder
        results = service.files().list(
            q=(
                f"'{os.environ['DRIVE_FOLDER_ID']}' in parents "
                f"and mimeType='application/pdf' "
                f"and trashed=false"
            ),
            orderBy="createdTime desc",
            pageSize=MAX_TICKETS,
            fields="files(id, name, createdTime)"
        ).execute()

        files = results.get("files", [])

        if not files:
            result = "No recent ticket PDFs."
            _ingredients_cache = {"timestamp": now, "data": result}
            return result

        print(f"  [drive_tools] Found {len(files)} PDF ticket(s) to process")

        raw_texts = []
        for f in files:
            print(f"  [drive_tools] Processing: {f['name']} ({f['createdTime'][:10]})")
            try:
                pdf_bytes = _download_pdf_bytes(service, f["id"])
                text = _extract_text_from_pdf(pdf_bytes)
                if text.strip():
                    raw_texts.append(f"# {f['name']}\n{text}")
                else:
                    print(f"  [drive_tools] Warning: no text extracted from {f['name']}")
            except Exception as e:
                print(f"  [drive_tools] Error processing {f['name']}: {e}")
                continue

        if not raw_texts:
            result = "Could not extract text from PDFs."
            _ingredients_cache = {"timestamp": now, "data": result}
            return result

        ingredients = _summarise_ingredients(raw_texts)
        result = f"Ingredients: {ingredients}"
        
        # Cache the result
        _ingredients_cache = {"timestamp": now, "data": result}
        return result

    except Exception as e:
        return f"Error reading tickets: {e}"
