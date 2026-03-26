import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

START_URL = "https://england.shelter.org.uk/get_help/local_services"
BASE_DOMAIN = "england.shelter.org.uk"

OUTPUT_DIR = Path("sample-data/shelter")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def slug_from_url(url):
    return url.rstrip("/").split("/")[-1]


def find_email(text):
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else ""


def find_phone(text):
    match = re.search(r"(\+44\s?\d[\d\s]+|\(?0\d[\d\s]{8,}\d)", text)
    return clean_text(match.group(0)) if match else ""


def find_postcode(text):
    match = re.search(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", text, re.I)
    return match.group(0).upper() if match else ""


def discover_pages():
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(START_URL, headers=headers, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "lxml")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(START_URL, href)
        parsed = urlparse(full_url)

        if parsed.netloc != BASE_DOMAIN:
            continue

        # Shelter pattern
        if "/get_help/local_services/" in parsed.path:
            if parsed.path != "/get_help/local_services":
                links.add(full_url)

    return sorted(links)


def scrape_page(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "lxml")
    text = soup.get_text("\n", strip=True)

    name = ""
    h1 = soup.find("h1")
    if h1:
        name = clean_text(h1.get_text())

    email = find_email(text)
    phone = find_phone(text)
    postcode = find_postcode(text)

    data = {
        "name": name,
        "description": "Housing advice and homelessness support",
        "service_type": "advice centre",
        "website_url": url,
        "phone_number": phone,
        "email_address": email,
        "physical_address": "",
        "postcode": postcode,
        "opening_times": "",
        "source_url": url,
        "date_collected": str(date.today()),
        "verification_status": "unverified",
    }

    return data


def save_record(record, url):
    slug = slug_from_url(url)
    file_path = OUTPUT_DIR / f"{slug}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Saved: {file_path}")


def main():
    print("Discovering Shelter pages...")

    urls = discover_pages()

    print(f"Found {len(urls)} pages:")
    for u in urls:
        print("-", u)

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")

        try:
            data = scrape_page(url)
            save_record(data, url)

            print("Name:", data["name"])
            print("Phone:", data["phone_number"])
            print("Postcode:", data["postcode"])

        except Exception as e:
            print("Error:", e)

        if i < len(urls):
            print("Waiting 8 seconds...")
            time.sleep(8)

    print("\nDone.")


if __name__ == "__main__":
    main()