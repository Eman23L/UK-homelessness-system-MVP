from pathlib import Path
import sqlite3

from flask import Flask, jsonify, send_from_directory

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = BASE_DIR / "data" / "services.db"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


def get_connection() -> sqlite3.Connection:
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
return conn


@app.route("/services", methods=["GET"])
def get_services():
conn = get_connection()
cursor = conn.cursor()
cursor.execute(
"""
SELECT
id,
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
longitude
FROM services
"""
)
rows = cursor.fetchall()
conn.close()

services = [dict(row) for row in rows]
return jsonify(services)


@app.route("/")
def serve_index():
return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/index.html")
def serve_index_html():
return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/results.html")
def serve_results():
return send_from_directory(FRONTEND_DIR, "results.html")


@app.route("/service.html")
def serve_service():
return send_from_directory(FRONTEND_DIR, "service.html")


@app.route("/manifest.json")
def serve_manifest():
return send_from_directory(FRONTEND_DIR, "manifest.json")


@app.route("/service-worker.js")
def serve_service_worker():
return send_from_directory(FRONTEND_DIR, "service-worker.js")


@app.route("/styles.css")
def serve_styles():
return send_from_directory(FRONTEND_DIR, "styles.css")


@app.route("/app.js")
def serve_app_js():
return send_from_directory(FRONTEND_DIR, "app.js")


@app.route("/<path:filename>")
def serve_static_files(filename: str):
file_path = FRONTEND_DIR / filename
if file_path.exists() and file_path.is_file():
return send_from_directory(FRONTEND_DIR, filename)
return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
app.run(host="0.0.0.0", port=5000, debug=True)
