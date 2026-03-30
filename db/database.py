import sqlite3
from pathlib import Path
from parsers.models import HomelessSupportService

DB_PATH = Path("data/services.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        description TEXT,
        service_type TEXT,
        provider_name TEXT NOT NULL,
        website_url TEXT,
        phone_number TEXT,
        email_address TEXT,
        physical_address TEXT,
        postcode TEXT,
        opening_times TEXT,
        eligibility TEXT,
        notes TEXT,
        latitude REAL,
        longitude REAL,
        date_collected TEXT NOT NULL,
        verification_status TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def save_service(service: HomelessSupportService) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
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
        latitude,
        longitude,
        date_collected,
        verification_status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source_url) DO UPDATE SET
        name = excluded.name,
        description = excluded.description,
        service_type = excluded.service_type,
        provider_name = excluded.provider_name,
        website_url = excluded.website_url,
        phone_number = excluded.phone_number,
        email_address = excluded.email_address,
        physical_address = excluded.physical_address,
        postcode = excluded.postcode,
        opening_times = excluded.opening_times,
        eligibility = excluded.eligibility,
        notes = excluded.notes,
        latitude = excluded.latitude,
        longitude = excluded.longitude,
        date_collected = excluded.date_collected,
        verification_status = excluded.verification_status
    """, (
        service.source_url,
        service.name,
        service.description,
        service.service_type,
        service.provider_name,
        service.website_url,
        service.phone_number,
        service.email_address,
        service.physical_address,
        service.postcode,
        service.opening_times,
        service.eligibility,
        service.notes,
        service.latitude,
        service.longitude,
        service.date_collected,
        service.verification_status,
    ))

    conn.commit()
    conn.close()