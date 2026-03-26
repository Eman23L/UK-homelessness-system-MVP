from firecrawl import Firecrawl
import json
import time
from datetime import date
from pathlib import Path

API_KEY = "fc-4f8058ef5be548879e160314669cc5f8"

app = Firecrawl(api_key=API_KEY)

CRISIS_URLS = [
    "https://www.crisis.org.uk/get-help/brent/",
    "https://www.crisis.org.uk/get-help/birmingham/",
    "https://www.crisis.org.uk/get-help/croydon/",
    "https://www.crisis.org.uk/get-help/edinburgh/",
    "https://www.crisis.org.uk/get-help/london/",
    "https://www.crisis.org.uk/get-help/merseyside/",
    "https://www.crisis.org.uk/get-help/newcastle/",
    "https://www.crisis.org.uk/get-help/oxford/",
    "https://www.crisis.org.uk/get-help/south-wales/",
]

OUTPUT_DIR = Path("sample-data/crisis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def scrape_page(url):
    result = app.scrape(
        url,
        formats=["markdown"]
    )
    return result


def save_result(result, url):
    slug = url.rstrip("/").split("/")[-1]

    markdown = ""
    html = ""

    if isinstance(result, dict):
        markdown = (
            result.get("markdown")
            or result.get("data", {}).get("markdown", "")
            or ""
        )
        html = (
            result.get("html")
            or result.get("data", {}).get("html", "")
            or ""
        )

    record = {
        "source_url": url,
        "date_collected": str(date.today()),
        "verification_status": "unverified",
        "markdown": markdown,
        "html": html
    }

    file_path = OUTPUT_DIR / f"{slug}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Saved: {file_path}")
    print(f"Markdown length: {len(markdown)}")


def main():
    print("Starting Crisis scrape...")

    for i, url in enumerate(CRISIS_URLS, 1):
        print(f"\n[{i}/{len(CRISIS_URLS)}] {url}")

        try:
            result = scrape_page(url)
            save_result(result, url)
        except Exception as e:
            print(f"Error: {e}")

        if i < len(CRISIS_URLS):
            print("Waiting 8 seconds...")
            time.sleep(8)

    print("\nDone.")


if __name__ == "__main__":
    main()