import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

START_URL = "https://www.crisis.org.uk/get-help/"
BASE_DOMAIN = "www.crisis.org.uk"
OUTPUT_DIR = Path("sample-data/crisis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def find_email(text: str) -> str:
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else ""


def find_phone(text: str) -> str:
    match = re.search(r"(\+44\s?\d[\d\s]+|\(?0\d[\d\s]{8,}\d)", text)
    return clean_text(match.group(0)) if match else ""


def find_postcode(text: str) -> str:
    match = re.search(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", text, re.I)
    return match.group(0).upper() if match else ""


def extract_address(lines: list[str]) -> str:
    for i, line in enumerate(lines):
        if line.lower().startswith("address:"):
            block = [line.replace("Address:", "").strip()]
            for j in range(i + 1, min(i + 8, len(lines))):
                stop_labels = [
                    "visiting us",
                    "areas covered",
                    "phone number",
                    "email address",
                    "opening hours",
                    "skylight director",
                    "contact us",
                    "our location",
                ]
                if any(lines[j].lower().startswith(label) for label in stop_labels):
                    break
                block.append(lines[j])
            return ", ".join([x for x in block if x])
    return ""


def extract_opening_hours(lines: list[str]) -> str:
    for i, line in enumerate(lines):
        if line.lower().startswith("opening hours"):
            first = line.replace("Opening hours:", "").strip()
            second = lines[i + 1] if i + 1 < len(lines) else ""
            return clean_text(f"{first} {second}")
    return ""


def extract_who_can_access(lines: list[str]) -> str:
    for line in lines:
        if line.lower().startswith("areas covered"):
            return clean_text(line.replace("Areas covered:", "").strip())
    return ""


def extract_description(soup: BeautifulSoup, page_text: str) -> str:
    h1 = soup.find("h1")
    if h1 and h1.parent:
        for sibling in h1.parent.find_all(["p", "div"], recursive=True):
            text = clean_text(sibling.get_text(" ", strip=True))
            if text and text != clean_text(h1.get_text()):
                if "we support" in text.lower() or "homeless" in text.lower():
                    return text

    match = re.search(
        r"We support people who are experiencing homelessness or at risk of homelessness\.?",
        page_text,
        re.I,
    )
    if match:
        return match.group(0)

    return "Support for people who are experiencing homelessness or at risk of homelessness."


def discover_crisis_pages(start_url: str) -> list[str]:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(start_url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    discovered = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(start_url, href)
        parsed = urlparse(full_url)

        if parsed.netloc != BASE_DOMAIN:
            continue

        path = parsed.path.rstrip("/")

        # Keep local help pages only, but not the main /get-help page itself
        if path.startswith("/get-help/") and path != "/get-help":
            discovered.add(full_url.rstrip("/") + "/")

    return sorted(discovered)


def scrape_one(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    page_text = soup.get_text("\n", strip=True)
    lines = [clean_text(line) for line in page_text.split("\n") if clean_text(line)]

    h1 = soup.find("h1")
    name = clean_text(h1.get_text()) if h1 else ""

    email = find_email(page_text)
    phone = find_phone(page_text)
    postcode = find_postcode(page_text)
    physical_address = extract_address(lines)
    opening_times = extract_opening_hours(lines)
    who_can_access = extract_who_can_access(lines)
    description = extract_description(soup, page_text)

    data = {
        "name": name,
        "description": description,
        "service_type": "homelessness support centre",
        "website_url": url,
        "phone_number": phone,
        "email_address": email,
        "attention": "",
        "physical_address": physical_address,
        "postcode": postcode,
        "opening_times": opening_times,
        "accessibility": "",
        "costs": "",
        "demographics": "",
        "specialist_support": [],
        "complex_needs_support": "",
        "pet_policy": "",
        "immigration_status": "",
        "who_can_access": who_can_access,
        "referral_required": "unknown",
        "referral_details": "",
        "support_offered": [],
        "notes": "",
        "source_url": url,
        "date_collected": str(date.today()),
        "verification_status": "unverified",
    }

    return data


def save_record(record: dict, url: str) -> None:
    slug = slug_from_url(url)
    output_file = OUTPUT_DIR / f"{slug}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Saved: {output_file}")


def main() -> None:
    print("Discovering Crisis pages...")
    urls = discover_crisis_pages(START_URL)

    print(f"Found {len(urls)} candidate pages:")
    for u in urls:
        print("-", u)

    for i, url in enumerate(urls, start=1):
        print(f"\n[{i}/{len(urls)}] {url}")
        try:
            record = scrape_one(url)
            save_record(record, url)
            print(f"Name: {record['name']}")
            print(f"Phone: {record['phone_number']}")
            print(f"Email: {record['email_address']}")
            print(f"Postcode: {record['postcode']}")
        except Exception as e:
            print(f"Failed on {url}")
            print(f"Error: {e}")

        if i < len(urls):
            print("Waiting 8 seconds...")
            time.sleep(8)

    print("\nDone.")


if __name__ == "__main__":
    main()