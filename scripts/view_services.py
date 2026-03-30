from db.database import get_connection


def main() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, provider_name, name, postcode, source_url
        FROM services
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = cursor.fetchall()

    if not rows:
        print("No services found in database.")
    else:
        for row in rows:
            print(f"""
ID: {row['id']}
Provider: {row['provider_name']}
Name: {row['name']}
Postcode: {row['postcode']}
Source URL: {row['source_url']}
{'-' * 60}
""")

    conn.close()


if __name__ == "__main__":
    main()