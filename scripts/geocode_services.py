import time
from urllib.parse import quote

import requests

from db.database import get_connection


HEADERS = {
    "User-Agent": "homeless-support-project/1.0"
}


def geocode_postcode(postcode: str):
    if not postcode:
        return None, None

    cleaned = postcode.strip().upper()
    url = f"https://api.postcodes.io/postcodes/{quote(cleaned)}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()

        if data.get("status") != 200 or not data.get("result"):
            return None, None

        result = data["result"]
        lat = result.get("latitude")
        lon = result.get("longitude")

        if lat is None or lon is None:
            return None, None

        return float(lat), float(lon)

    except Exception as e:
        print(f"Geocoding failed for {postcode}: {e}")
        return None, None


def run(limit: int | None = None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, postcode, physical_address
        FROM services
        WHERE latitude IS NULL OR longitude IS NULL
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()

    if limit:
        rows = rows[:limit]

    print(f"Services to geocode: {len(rows)}")

    for i, row in enumerate(rows, start=1):
        service_id = row["id"]
        postcode = row["postcode"]

        print(f"[{i}/{len(rows)}] Geocoding ID {service_id} - {postcode}")

        lat, lon = geocode_postcode(postcode)

        if lat is not None and lon is not None:
            cursor.execute("""
                UPDATE services
                SET latitude = ?, longitude = ?
                WHERE id = ?
            """, (lat, lon, service_id))

            print(f"  -> Saved coordinates: {lat}, {lon}")
        else:
            print("  -> No coordinates found")

        conn.commit()
        time.sleep(0.2)

    conn.close()
    print("Geocoding complete.")


if __name__ == "__main__":
    run(limit=20)