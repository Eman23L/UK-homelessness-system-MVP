from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import requests

GIVEFOOD_FOODBANKS_URL = "https://www.givefood.org.uk/api/2/foodbanks/"


def parse_lat_lng(lat_lng: str | None) -> tuple[float | None, float | None]:
    if not lat_lng:
        return None, None

    try:
        lat_str, lng_str = lat_lng.split(",", 1)
        return float(lat_str.strip()), float(lng_str.strip())
    except (ValueError, AttributeError):
        return None, None


def build_notes(item: dict[str, Any]) -> str | None:
    notes_parts: list[str] = []

    network = item.get("network")
    country = item.get("country")
    needs = item.get("needs", {}) or {}
    charity = item.get("charity", {}) or {}
    politics = item.get("politics", {}) or {}

    if network:
        notes_parts.append(f"Network: {network}")

    if country:
        notes_parts.append(f"Country: {country}")

    needs_text = needs.get("needs")
    if needs_text:
        notes_parts.append(f"Current needs: {needs_text}")

    excess_text = needs.get("excess")
    if excess_text:
        notes_parts.append(f"Excess items: {excess_text}")

    needs_found = needs.get("found")
    if needs_found:
        notes_parts.append(f"Needs updated: {needs_found}")

    charity_id = charity.get("registration_id")
    if charity_id:
        notes_parts.append(f"Charity registration: {charity_id}")

    district = politics.get("district")
    if district:
        notes_parts.append(f"District: {district}")

    ward = politics.get("ward")
    if ward:
        notes_parts.append(f"Ward: {ward}")

    mp = politics.get("mp")
    if mp:
        notes_parts.append(f"MP: {mp}")

    if not notes_parts:
        return None

    return "\n".join(notes_parts)


def normalise_foodbank(item: dict[str, Any]) -> dict[str, Any]:
    latitude, longitude = parse_lat_lng(item.get("lat_lng"))
    urls = item.get("urls", {}) or {}
    needs = item.get("needs", {}) or {}

    homepage_url = urls.get("homepage")
    source_url = urls.get("html") or urls.get("self") or GIVEFOOD_FOODBANKS_URL

    name = item.get("name") or "Unknown food bank"
    network = item.get("network")
    description = "Food bank"
    if network:
        description = f"Food bank ({network})"

    return {
        "source_url": source_url,
        "name": name,
        "description": description,
        "service_type": "food",
        "provider_name": "givefood",
        "website_url": homepage_url,
        "phone_number": item.get("phone") or item.get("secondary_phone"),
        "email_address": item.get("email"),
        "physical_address": item.get("address"),
        "postcode": item.get("postcode"),
        "opening_times": None,
        "eligibility": None,
        "notes": build_notes(item),
        "date_collected": datetime.now(timezone.utc).isoformat(),
        "verification_status": "api_import",
        "latitude": latitude,
        "longitude": longitude,
        "external_id": item.get("id"),
        "slug": item.get("slug"),
        "needs_found": needs.get("found"),
        "needs_count": needs.get("number"),
    }


def fetch_food_services(timeout: int = 30) -> list[dict[str, Any]]:
    response = requests.get(GIVEFOOD_FOODBANKS_URL, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError("Unexpected Give Food response: expected a list of food banks")

    services: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        services.append(normalise_foodbank(item))

    return services