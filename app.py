from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
# Allow cross-origin requests so the static HTML can POST from localhost or file://
CORS(app, resources={r"/v1/*": {"origins": "*"}})

def hash_value(value: str) -> str:
    """Return SHA-256 hash of the input string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

@app.route("/ping", methods=["GET"])
def ping():
    """Simple health check endpoint."""
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

    record_dict = submission.dict()

    record_dict["email"] = hash_value(record_dict["email"])
    record_dict["age"] = hash_value(str(record_dict["age"]))

    if not record_dict.get("submission_id"):
        dt = datetime.utcnow().strftime("%Y%m%d%H")
        record_dict["submission_id"] = hash_value(record_dict["email"] + dt)

    record_dict["received_at"] = datetime.now(timezone.utc)
    record_dict["ip"] = request.headers.get("X-Forwarded-For", request.remote_addr or "")

    append_json_line(record_dict)

    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(port=0, debug=True)