from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from parsers.food_parser import fetch_food_services

DB_PATH = BASE_DIR / "data" / "services.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(services)")
    existing_columns = {row["name"] for row in cursor.fetchall()}

    optional_columns = {
        "external_id": "TEXT",
        "slug": "TEXT",
        "needs_found": "TEXT",
        "needs_count": "INTEGER",
    }

    for column_name, column_type in optional_columns.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE services ADD COLUMN {column_name} {column_type}")

    conn.commit()


def clear_existing_givefood_rows(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM services WHERE provider_name = ?", ("givefood",))
    conn.commit()


def insert_services(conn: sqlite3.Connection, services: list[dict]) -> None:
    cursor = conn.cursor()

    for service in services:
        cursor.execute(
            """
            INSERT INTO services (
                source_url,
                name,
                description,
                service_type,
                provider_name,
                website_url,
                phone_number,
                email_address,
                physical_address,
                postcode,
                opening_times,
                eligibility,
                notes,
                date_collected,
                verification_status,
                latitude,
                longitude,
                external_id,
                slug,
                needs_found,
                needs_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                service.get("source_url"),
                service.get("name"),
                service.get("description"),
                service.get("service_type"),
                service.get("provider_name"),
                service.get("website_url"),
                service.get("phone_number"),
                service.get("email_address"),
                service.get("physical_address"),
                service.get("postcode"),
                service.get("opening_times"),
                service.get("eligibility"),
                service.get("notes"),
                service.get("date_collected"),
                service.get("verification_status"),
                service.get("latitude"),
                service.get("longitude"),
                service.get("external_id"),
                service.get("slug"),
                service.get("needs_found"),
                service.get("needs_count"),
            ),
        )

    conn.commit()


def main() -> None:
    print("Fetching Give Food food banks...")
    services = fetch_food_services()
    print(f"Fetched {len(services)} food services.")

    conn = get_connection()
    try:
        ensure_columns(conn)
        clear_existing_givefood_rows(conn)
        insert_services(conn, services)
    finally:
        conn.close()

    print("Give Food import complete.")


if __name__ == "__main__":
    main()
