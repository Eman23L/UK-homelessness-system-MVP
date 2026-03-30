import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from parsers.models import HomelessSupportService
from parsers.utils import (
    clean_text,
    slug_from_url,
    find_email,
    find_phone,
    find_postcode,
    extract_opening_hours,
)
from db.database import save_service

START_URL = "https://england.shelter.org.uk/get_help/local_services"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = "sample-data/shelter"


def discover_pages() -> list[str]:
    res = requests.get(START_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "lxml")

    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/get_help/local_services/" in href:
            full_url = urljoin(START_URL, href)
            if urlparse(full_url).path.rstrip("/") != "/get_help/local_services":
                links.add(full_url.rstrip("/"))

    return sorted(links)


def extract_address(soup: BeautifulSoup) -> str:
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "google.com/maps" in href or "maps.google" in href:
            text = clean_text(a.get_text(" ", strip=True))
            if text:
                return text
    return ""


def scrape_page(url: str) -> dict:
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "lxml")

    page_text = soup.get_text("\n", strip=True)
    lines = [clean_text(x) for x in page_text.split("\n") if clean_text(x)]

    name = clean_text(soup.find("h1").get_text()) if soup.find("h1") else "Shelter service"
    address = extract_address(soup)

    return {
        "name": name,
        "description": "Housing advice and homelessness support",
        "service_type": "advice centre",
        "provider_name": "shelter",
        "website_url": url,
        "phone_number": find_phone(page_text),
        "email_address": find_email(page_text),
        "physical_address": address,
        "postcode": find_postcode(page_text),
        "opening_times": extract_opening_hours(lines),
        "eligibility": "",
        "notes": "",
        "latitude": None,
        "longitude": None,
        "source_url": url,
    }


def is_valid_service_page(raw: dict) -> bool:
    has_name = bool(raw["name"])
    has_signal = any(
        [
            raw["phone_number"],
            raw["email_address"],
            raw["physical_address"],
            raw["postcode"],
        ]
    )
    return has_name and has_signal


def run(save_json: bool = True) -> None:
    urls = discover_pages()

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