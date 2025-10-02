from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
CORS(app, resources={r"/v1/*": {"origins": "*"}})

def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # Extract raw values
    raw_email = submission.email
    raw_age = submission.age

    # Build stored record
    record = StoredSurveyRecord(
        name=submission.name,
        hashed_email=hash_value(raw_email),
        hashed_age=hash_value(str(raw_age)),
        consent=submission.consent,
        rating=submission.rating,
        comments=submission.comments,
        user_agent=submission.user_agent or request.headers.get("User-Agent"),
        submission_id=submission.submission_id or hash_value(raw_email + datetime.utcnow().strftime("%Y%m%d%H")),
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )

    append_json_line(record.dict())
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)