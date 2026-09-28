import os
import traceback

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from hindsight_service import MeetingPrepAgent

load_dotenv()

BASE_URL = os.environ.get("HINDSIGHT_BASE_URL", "http://localhost:8888")
API_KEY = os.environ.get("HINDSIGHT_API_KEY") or None

app = Flask(__name__)
agent = MeetingPrepAgent(base_url=BASE_URL, api_key=API_KEY)


@app.errorhandler(Exception)
def handle_any_error(e):
    # Always return JSON, never Flask's default HTML error page - the
    # frontend expects JSON on every response. Full traceback goes to the
    # terminal so it's still easy to debug.
    traceback.print_exc()
    return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/contacts", methods=["GET"])
def get_contacts():
    return jsonify(agent.list_contacts())


@app.route("/api/contacts", methods=["POST"])
def add_contact():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    contact = agent.get_or_create_contact(name)
    return jsonify(contact)


@app.route("/api/log", methods=["POST"])
def log_meeting():
    data = request.get_json(force=True)
    name = (data.get("contact") or "").strip()
    notes = (data.get("notes") or "").strip()
    meeting_date = (data.get("date") or "").strip() or None
    if not name or not notes:
        return jsonify({"error": "contact and notes are required"}), 400
    try:
        result = agent.log_meeting(name, notes, meeting_date=meeting_date)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify(result)


@app.route("/api/next-meeting", methods=["POST"])
def set_next_meeting():
    data = request.get_json(force=True)
    name = (data.get("contact") or "").strip()
    date = (data.get("date") or "").strip() or None
    if not name:
        return jsonify({"error": "contact is required"}), 400
    result = agent.set_next_meeting(name, date)
    return jsonify(result)


@app.route("/api/prep", methods=["POST"])
def prep_meeting():
    data = request.get_json(force=True)
    name = (data.get("contact") or "").strip()
    if not name:
        return jsonify({"error": "contact is required"}), 400
    try:
        result = agent.prep_briefing(name)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify(result)


@app.route("/api/timeline", methods=["POST"])
def timeline():
    data = request.get_json(force=True)
    name = (data.get("contact") or "").strip()
    if not name:
        return jsonify({"error": "contact is required"}), 400
    try:
        result = agent.timeline(name)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
