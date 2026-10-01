import os
import re
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
MONTH_ALIASES = {
    "jan": "January",
    "january": "January",
    "feb": "February",
    "february": "February",
    "mar": "March",
    "march": "March",
    "apr": "April",
    "april": "April",
    "may": "May",
    "jun": "June",
    "june": "June",
    "jul": "July",
    "july": "July",
    "aug": "August",
    "august": "August",
    "sep": "September",
    "sept": "September",
    "september": "September",
    "oct": "October",
    "october": "October",
    "nov": "November",
    "november": "November",
    "dec": "December",
    "december": "December",
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


init_db()


def normalize_month_name(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()

    if lowered in MONTH_ALIASES:
        return MONTH_ALIASES[lowered]

    for month in MONTHS:
        if lowered == month.lower() or lowered == month[:3].lower():
            return month

    if text.isdigit():
        month_number = int(text)
        if 1 <= month_number <= 12:
            return MONTHS[month_number - 1]

    return None


def parse_natural_language(message):
    if not message:
        return None, None

    cleaned = message.strip()
    if not cleaned:
        return None, None

    year_match = re.search(r"(19\d{2}|20\d{2}|21\d{2})", cleaned)
    year = int(year_match.group(1)) if year_match else None

    month = None
    for month_name in MONTHS:
        if re.search(rf"\b{month_name.lower()}\b", cleaned.lower()):
            month = month_name
            break

    if month is None:
        for alias, canonical in MONTH_ALIASES.items():
            if re.search(rf"\b{alias}\b", cleaned.lower()):
                month = canonical
                break

    if month is None:
        digit_match = re.search(r"(?<!\d)(0?[1-9]|1[0-2])(?!\d)", cleaned)
        if digit_match:
            month = MONTHS[int(digit_match.group(1)) - 1]

    return year, month


def calculate_stats(images):
    unique_years = {str(image["year"]) for image in images}
    current_month = datetime.now().strftime("%B")
    current_month_uploads = sum(1 for image in images if image["month"] == current_month)
    return {
        "total_images": len(images),
        "total_years": len(unique_years),
        "current_month_uploads": current_month_uploads,
    }


def search_images(year, month):
    normalized_month = normalize_month_name(month)
    try:
        year_int = int(year)
    except (TypeError, ValueError):
        return []

    if normalized_month is None or not (1900 <= year_int <= 2100):
        return []

    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM images WHERE year = ? AND month = ? ORDER BY created_at DESC",
            (year_int, normalized_month),
        ).fetchall()

    return [dict(row) for row in rows]


def validate_image_upload(file_storage):
    if file_storage is None or file_storage.filename == "":
        raise ValueError("Please select an image file.")

    filename = secure_filename(file_storage.filename)
    if not filename or "." not in filename:
        raise ValueError("Invalid image file name.")

    extension = filename.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported image format. Use JPG, JPEG, PNG, or WEBP.")

    if file_storage.mimetype and file_storage.mimetype not in ALLOWED_MIME_TYPES:
        raise ValueError("The uploaded file does not appear to be a valid image.")

    try:
        file_storage.stream.seek(0, os.SEEK_END)
        file_size = file_storage.stream.tell()
        file_storage.stream.seek(0)
    except Exception:
        file_size = 0

    if file_size > MAX_FILE_SIZE:
        raise ValueError("Image size must be 5 MB or less.")

    return filename


@app.route("/")
def index():
    return render_template(
        "index.html",
        results=[],
        performed_search=False,
        searched_year="",
        searched_month="",
        search_query="",
        error_message=None,
        success_message=None,
    )


@app.route("/", methods=["POST"])
def find_image():
    year_value = (request.form.get("year") or "").strip()
    month_value = (request.form.get("month") or "").strip()
    natural_query = (request.form.get("search_query") or "").strip()

    results = []
    performed_search = True
    searched_year = ""
    searched_month = ""
    search_query = natural_query
    error_message = None
    success_message = None

    if year_value or month_value:
        if not year_value or not month_value:
            error_message = "Please provide both a valid year and month."
        else:
            try:
                year_int = int(year_value)
            except ValueError:
                error_message = "Year must be a valid number."
            else:
                if not (1900 <= year_int <= 2100):
                    error_message = "Please enter a year between 1900 and 2100."
                else:
                    normalized_month = normalize_month_name(month_value)
                    if normalized_month is None:
                        error_message = "Please select a valid month."
                    else:
                        searched_year = year_int
                        searched_month = normalized_month
                        results = search_images(year_int, normalized_month)
    elif natural_query:
        parsed_year, parsed_month = parse_natural_language(natural_query)
        if parsed_year is None or parsed_month is None:
            error_message = "Please enter a valid year and month, such as September 2026."
        else:
            searched_year = parsed_year
            searched_month = parsed_month
            results = search_images(parsed_year, parsed_month)
    else:
        error_message = "Please provide a year and month to search."

    if not results and not error_message and performed_search:
        error_message = None

    return render_template(
        "index.html",
        results=results,
        performed_search=performed_search,
        searched_year=searched_year,
        searched_month=searched_month,
        search_query=search_query,
        error_message=error_message,
        success_message=success_message,
    )


@app.route("/admin")
def admin_page():
    images = []
    with get_db_connection() as connection:
        rows = connection.execute("SELECT * FROM images ORDER BY created_at DESC").fetchall()
        images = [dict(row) for row in rows]

    return render_template(
        "admin.html",
        images=images,
        success_message=None,
        error_message=None,
        stats=calculate_stats(images),
    )


@app.route("/admin", methods=["POST"])
def admin_upload():
    year_value = (request.form.get("year") or "").strip()
    month_value = (request.form.get("month") or "").strip()
    uploaded_file = request.files.get("image")

    with get_db_connection() as connection:
        rows = connection.execute("SELECT * FROM images ORDER BY created_at DESC").fetchall()
        images = [dict(row) for row in rows]

    success_message = None
    error_message = None

    if not year_value:
        error_message = "Please provide a year for this image."
    elif not month_value:
        error_message = "Please select a month for this image."
    else:
        try:
            year_int = int(year_value)
        except ValueError:
            error_message = "Year must be a valid number."
        else:
            if not (1900 <= year_int <= 2100):
                error_message = "Year must be between 1900 and 2100."
            else:
                normalized_month = normalize_month_name(month_value)
                if normalized_month is None:
                    error_message = "Please select a valid month."
                else:
                    try:
                        original_name = validate_image_upload(uploaded_file)
                    except ValueError as exc:
                        error_message = str(exc)
                    else:
                        safe_name = secure_filename(original_name)
                        file_token = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                        unique_name = f"{file_token}_{uuid.uuid4().hex[:8]}_{safe_name}"
                        target_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
                        uploaded_file.save(target_path)

                        with get_db_connection() as connection:
                            connection.execute(
                                "INSERT INTO images (year, month, filename) VALUES (?, ?, ?)",
                                (year_int, normalized_month, unique_name),
                            )
                            connection.commit()

                        success_message = f"Image uploaded successfully! {normalized_month} {year_int} - {unique_name}"
                        with get_db_connection() as connection:
                            rows = connection.execute("SELECT * FROM images ORDER BY created_at DESC").fetchall()
                            images = [dict(row) for row in rows]

    return render_template(
        "admin.html",
        images=images,
        success_message=success_message,
        error_message=error_message,
        stats=calculate_stats(images),
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/delete/<int:image_id>", methods=["POST"])
def delete_image(image_id):
    with get_db_connection() as connection:
        row = connection.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        if row is None:
            return jsonify({"success": False, "message": "Image not found."}), 404

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], row["filename"])
        if os.path.exists(file_path):
            os.remove(file_path)

        connection.execute("DELETE FROM images WHERE id = ?", (image_id,))
        connection.commit()

    return jsonify({"success": True, "message": "Image deleted successfully."})


@app.route("/api/search")
def api_search():
    year_value = (request.args.get("year") or "").strip()
    month_value = (request.args.get("month") or "").strip()
    natural_query = (request.args.get("q") or "").strip()

    if year_value and month_value:
        year = year_value
        month = month_value
    elif natural_query:
        year, month = parse_natural_language(natural_query)
    else:
        return jsonify({"success": False, "message": "Missing year or month."}), 400

    if year is None or month is None:
        return jsonify({"success": False, "message": "Unable to detect year and month."}), 400

    results = search_images(year, month)
    payload = {
        "success": True,
        "year": int(year),
        "month": normalize_month_name(month),
        "count": len(results),
        "results": [
            {
                "id": image["id"],
                "year": image["year"],
                "month": image["month"],
                "filename": image["filename"],
                "image_url": f"/uploads/{image['filename']}",
            }
            for image in results
        ],
    }
    return jsonify(payload)


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host="127.0.0.1", port=5000)
