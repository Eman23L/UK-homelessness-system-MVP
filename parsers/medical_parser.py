from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "ODS General Search.csv"


def row_to_service(row: list[str]) -> dict[str, Any] | None:
    if len(row) < 12:
        return None

    org_code = (row[0] or "").strip()
    name = (row[1] or "").strip()
    org_type = (row[2] or "").strip()
    status = (row[8] or "").strip()
    address_1 = (row[9] or "").strip()
    city = (row[10] or "").strip()
    postcode = (row[11] or "").strip()

    if not name or not postcode:
        return None

    if status.lower() != "active":
        return None

    combined = f"{name} {org_type}".lower()

    medical_keywords = [
        "gp",
        "practice",
        "clinic",
        "medical",
        "health centre",
        "healthcenter",
        "surgery",
        "primary care",
        "hospital",
        "walk-in",
        "walk in",
        "urgent care",
    ]

    if not any(keyword in combined for keyword in medical_keywords):
        return None

    physical_address = ", ".join(part for part in [address_1, city, postcode] if part)

    return {
        "source_url": None,
        "name": name,
        "description": f"NHS medical service ({org_type})" if org_type else "NHS medical service",
        "service_type": "medical",
        "provider_name": "nhs_ods",
        "website_url": None,
        "phone_number": None,
        "email_address": None,
        "physical_address": physical_address,
        "postcode": postcode,
        "opening_times": None,
        "eligibility": None,
        "notes": f"ODS code: {org_code}" if org_code else None,
        "date_collected": datetime.now(timezone.utc).isoformat(),
        "verification_status": "csv_import",
        "latitude": None,
        "longitude": None,
        "external_id": org_code or None,
        "slug": None,
        "needs_found": None,
        "needs_count": None,
    }


def fetch_medical_services() -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []

    with open(DATA_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)

        for row in reader:
            service = row_to_service(row)
            if service:
                services.append(service)

    return services