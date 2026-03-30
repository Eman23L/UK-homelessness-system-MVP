import time
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from parsers.models import HomelessSupportService
from parsers.utils import (
    clean_text,
    find_email,
    find_phone,
    find_postcode,
    slug_from_url,
)
from db.database import save_service

BASE_URL = "https://homeless.org.uk/homeless-england/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = "sample-data/homeless_england"


def fetch_soup(url: str) -> BeautifulSoup:
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    return BeautifulSoup(res.text, "lxml")


def discover_pages(max_pages: int = 120) -> list[str]:
    start_url = "https://homeless.org.uk/homeless-england/?query=&lat=&lng=&place_id=&service_q=&miles="
    all_links = set()

    first_soup = fetch_soup(start_url)

    with open("homeless_england_page1.html", "w", encoding="utf-8") as f:
        f.write(str(first_soup))

    total_pages = 1
    for a in first_soup.find_all("a", href=True):
        href = a["href"].strip()
        if "page=" not in href:
            continue

        full_url = urljoin(start_url, href)
        parsed = urlparse(full_url)
        params = parse_qs(parsed.query)

        if "page" in params:
            try:
                page_num = int(params["page"][0])
                total_pages = max(total_pages, page_num)
            except (ValueError, TypeError, IndexError):
                pass

    total_pages = min(total_pages, max_pages)
    print(f"Detected total pages from pagination links: {total_pages}")

    for page_num in range(1, total_pages + 1):
        if page_num == 1:
            current_url = start_url
            soup = first_soup
        else:
            current_url = f"{start_url}&page={page_num}"
            print(f"Discovering page {page_num}: {current_url}")
            soup = fetch_soup(current_url)

        if page_num == 1:
            hrefs = [a.get("href") for a in soup.find_all("a", href=True)]
            print("Sample hrefs from page 1:")
            for href in hrefs[:80]:
                print("  ", href)

        links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "service/" in href:
                full_url = urljoin(start_url, href).rstrip("/")
                links.add(full_url)

        print(f"  -> Found {len(links)} service links")

        if not links:
            print(f"  -> No service links found on page {page_num}, stopping.")
            break

        before = len(all_links)
        all_links.update(links)
        after = len(all_links)

        if after == before:
            print(f"  -> No new service links added on page {page_num}.")
            break

        time.sleep(1)

    return sorted(all_links)


def extract_name(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    return clean_text(h1.get_text(" ", strip=True)) if h1 else ""


def extract_service_type(soup: BeautifulSoup) -> str:
    text = soup.get_text("\n", strip=True).lower()

    priority_order = [
        "supported housing",
        "housing department",
        "day centre",
        "resettlement",
        "outreach",
        "advice",
        "accommodation",
    ]

    for label in priority_order:
        if label in text:
            return label

    return ""


def extract_website_url(soup: BeautifulSoup, source_url: str) -> str:
    skip_domains = {
        "homeless.org.uk",
        "www.in-form.org.uk",
        "in-form.org.uk",
        "google.com",
        "maps.google.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "linkedin.com",
        "youtube.com",
    }

    candidates = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = clean_text(a.get_text(" ", strip=True)).lower()

        if not href.startswith("http"):
            continue

        if any(domain in href for domain in skip_domains):
            continue

        score = 0
        if text == "website":
            score += 5
        if "visit website" in text:
            score += 4
        if "website" in text:
            score += 3
        if "contact" in text:
            score += 1
        if "www." in href:
            score += 1

        candidates.append((score, href))

    if not candidates:
        return ""

    candidates.sort(reverse=True)
    return candidates[0][1]


def extract_opening_times(text: str) -> str:
    lines = [clean_text(line) for line in text.split("\n") if clean_text(line)]
    opening_lines = []
    capture = False

    stop_markers = {
        "phone",
        "email",
        "website",
        "services offered",
        "area served",
        "who do we help",
        "how to contact",
        "access",
        "referral",
    }

    for line in lines:
        lower = line.lower()

        if "opening times" in lower:
            capture = True
            continue

        if capture:
            if any(lower == marker or lower.startswith(marker) for marker in stop_markers):
                break
            opening_lines.append(line)

    return " | ".join(opening_lines) if opening_lines else ""


def extract_address_block(text: str) -> str:
    lines = [clean_text(line) for line in text.split("\n") if clean_text(line)]

    heading_variants = {
        "address",
        "referral address",
        "location",
    }

    stop_headings = {
        "phone",
        "email",
        "website",
        "opening times",
        "how to contact",
        "services offered",
        "area served",
        "who do we help",
        "referral",
        "access",
    }

    for i, line in enumerate(lines):
        lower = line.lower().rstrip(":")
        if lower in heading_variants:
            block = []
            for j in range(i + 1, min(i + 6, len(lines))):
                next_lower = lines[j].lower().rstrip(":")
                if next_lower in stop_headings:
                    break
                block.append(lines[j])

            address = ", ".join(block).strip(", ")
            if find_postcode(address):
                return clean_text(address)

    for i, line in enumerate(lines):
        if find_postcode(line):
            start = max(0, i - 2)
            end = min(len(lines), i + 1)

            block = []
            for candidate in lines[start:end + 1]:
                lower = candidate.lower().rstrip(":")
                if lower in stop_headings or any(lower.startswith(word) for word in stop_headings):
                    continue
                block.append(candidate)

            address = ", ".join(block).strip(", ")
            address = clean_text(address)

            for junk in [", phone", ", email", ", website"]:
                if address.lower().endswith(junk):
                    address = address[: -len(junk)].rstrip(", ")

            if find_postcode(address):
                return address

    return ""


def extract_description(text: str) -> str:
    lines = [clean_text(line) for line in text.split("\n") if clean_text(line)]

    heading_variants = {
        "services offered",
        "service offered",
        "description",
        "about the service",
        "about this service",
    }

    stop_headings = {
        "area served",
        "who do we help",
        "how to contact",
        "opening times",
        "phone",
        "email",
        "website",
        "referral",
        "access",
        "address",
        "location",
    }

    for i, line in enumerate(lines):
        lower = line.lower().rstrip(":")
        if lower in heading_variants:
            collected = []
            for j in range(i + 1, min(i + 10, len(lines))):
                next_lower = lines[j].lower().rstrip(":")
                if next_lower in stop_headings:
                    break
                collected.append(lines[j])

            desc = " ".join(collected).strip()
            if desc and len(desc) > 30:
                return desc

    for line in lines:
        lower = line.lower()
        if (
            len(line) > 80
            and "phone" not in lower
            and "email" not in lower
            and "website" not in lower
            and "address" not in lower
        ):
            return line

    return ""


def scrape_page(url: str) -> dict:
    soup = fetch_soup(url)
    text = soup.get_text("\n", strip=True)

    return {
        "name": extract_name(soup),
        "description": extract_description(text),
        "service_type": extract_service_type(soup),
        "provider_name": "homeless_england",
        "website_url": extract_website_url(soup, url),
        "phone_number": find_phone(text),
        "email_address": find_email(text),
        "physical_address": extract_address_block(text),
        "postcode": find_postcode(text),
        "opening_times": extract_opening_times(text),
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
            raw["description"],
        ]
    )
    return has_name and has_signal


def run(limit: int | None = None, save_json: bool = True) -> None:
    urls = discover_pages()

    if limit:
        urls = urls[:limit]

    print(f"Total service URLs to scrape: {len(urls)}")

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] Scraping: {url}")
        try:
            raw = scrape_page(url)

            if not is_valid_service_page(raw):
                print(f"  -> Skipping non-service or weak page: {url}")
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
    run(limit=20, save_json=True)