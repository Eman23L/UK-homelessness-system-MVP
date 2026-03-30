import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from parsers.models import HomelessSupportService
from parsers.utils import (
    clean_text,
    find_email,
    find_phone,
    find_postcode,
    extract_opening_hours,
    slug_from_url,
)
from db.database import save_service

START_URL = "https://www.crisis.org.uk/get-help/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = "sample-data/crisis"


def extract_address(lines: list[str]) -> str:
    for i, line in enumerate(lines):
        if line.lower().startswith("address:"):
            block = [line.replace("Address:", "").strip()]
            for j in range(i + 1, min(i + 8, len(lines))):
                if any(
                    lines[j].lower().startswith(label)
                    for label in ["visiting us", "phone number", "email address", "opening hours"]
                ):
                    break
                block.append(lines[j])
            return ", ".join(x for x in block if x)
    return ""


def discover_crisis_pages(start_url: str) -> list[str]:
    res = requests.get(start_url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "lxml")

    discovered = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        # Must be real service page
        if not href.startswith("/get-help/"):
            continue

        # Skip anchors and fragments
        if "#" in href:
            continue

        # Skip base page
        if href.rstrip("/") == "/get-help":
            continue

        full_url = urljoin(start_url, href).rstrip("/") + "/"
        discovered.add(full_url)

    return sorted(discovered)


def scrape_page(url: str) -> dict:
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "lxml")
    page_text = soup.get_text("\n", strip=True)
    lines = [clean_text(line) for line in page_text.split("\n") if clean_text(line)]

    return {
        "name": clean_text(soup.find("h1").get_text()) if soup.find("h1") else "Crisis Skylight",
        "description": "Specialist advice and support for people experiencing homelessness.",
        "service_type": "homelessness support centre",
        "provider_name": "crisis",
        "website_url": url,
        "phone_number": find_phone(page_text),
        "email_address": find_email(page_text),
        "physical_address": extract_address(lines),
        "postcode": find_postcode(page_text),
        "opening_times": extract_opening_hours(lines),
        "eligibility": "",
        "notes": "",
        "latitude": None,
        "longitude": None,
        "source_url": url,
    }


def is_valid_service_page(raw: dict) -> bool:
    return any([
        raw["phone_number"],
        raw["email_address"],
        raw["physical_address"],
    ])


def run(save_json: bool = True) -> None:
    urls = discover_crisis_pages(START_URL)

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] Scraping: {url}")
        try:
            raw = scrape_page(url)

            if not is_valid_service_page(raw):
                print(f"  -> Skipping non-service page: {url}")
                continue

            service = HomelessSupportService(**raw)

            save_service(service)
            print(f"  -> Saved to database: {service.name}")

            if save_json:
                filename = slug_from_url(url)
                service.to_json_file(OUTPUT_DIR, filename)
                print(f"  -> Saved JSON backup: {filename}.json")

        except Exception as e:
            print(f"  !! Failed: {url} -> {e}")

        time.sleep(2)


if __name__ == "__main__":
    run(save_json=True)