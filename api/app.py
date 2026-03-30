from flask import Flask, jsonify
from flask_cors import CORS
from db.database import get_connection

app = Flask(__name__)
CORS(app)


@app.route("/services", methods=["GET"])
def get_services():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
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
            source_url,
            date_collected,
            verification_status
        FROM services
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
        ORDER BY name ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    services = []
    for row in rows:
        services.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "service_type": row["service_type"],
            "provider_name": row["provider_name"],
            "website_url": row["website_url"],
            "phone_number": row["phone_number"],
            "email_address": row["email_address"],
            "physical_address": row["physical_address"],
            "postcode": row["postcode"],
            "opening_times": row["opening_times"],
            "eligibility": row["eligibility"],
            "notes": row["notes"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "source_url": row["source_url"],
            "date_collected": row["date_collected"],
            "verification_status": row["verification_status"],
        })

    return jsonify(services)


@app.route("/", methods=["GET"])
def home():
    return {
        "message": "Homeless support API is running.",
        "endpoints": [
            "/services"
        ]
    }


if __name__ == "__main__":
    app.run(debug=True)