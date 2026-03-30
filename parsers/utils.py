from urllib.parse import urlparse
import re

DAY_NAMES = [
    "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday"
]

STOP_WORDS = [
    "our national services",
    "our legal aid service",
    "contact us",
    "skylight director",
    "visiting us",
]

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else "record"
    slug = re.sub(r"[^a-zA-Z0-9\-]+", "", slug)
    return slug or "record"

def find_email(text: str) -> str:
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text or "")
    return match.group(0) if match else ""

def find_phone(text: str) -> str:
    match = re.search(r"(\+44\s?\d[\d\s()\-]+|\(?0\d[\d\s()\-]{8,}\d)", text or "")
    return clean_text(match.group(0)) if match else ""

def find_postcode(text: str) -> str:
    match = re.search(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", text or "", re.I)
    return match.group(0).upper() if match else ""

def extract_opening_hours(lines: list[str]) -> str:
    capture = False
    pending_day = None
    combined = []

    for raw_line in lines:
        line = clean_text(raw_line)
        lower = line.lower()

        if not line:
            continue

        if "opening hours" in lower:
            capture = True
            continue

        if not capture:
            continue

        if any(stop in lower for stop in STOP_WORDS):
            break

        if any(lower.startswith(day) for day in DAY_NAMES) and any(x in lower for x in ["am", "pm", "closed"]):
            combined.append(line)
            pending_day = None
            continue

        if lower in DAY_NAMES:
            pending_day = line
            continue

        if pending_day and any(x in lower for x in ["am", "pm", "closed"]):
            combined.append(f"{pending_day}: {line}")
            pending_day = None
            continue

        if combined:
            combined[-1] = f"{combined[-1]} ({line})"

    return " | ".join(combined) if combined else "Contact for hours"