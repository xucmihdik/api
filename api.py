from flask import Flask, jsonify
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=1, i",
    "referer": "https://growagarden.gg/stocks",
    "trpc-accept": "application/json",
    "x-trpc-source": "gag",
    "User-Agent": "Python Requests Client/1.0 (GAG Backend Integration)",
}

URL = "https://growagarden.gg/api/ws/stocks.getAll?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%2C%22meta%22%3A%7B%22values%22%3A%5B%22undefined%22%5D%7D%7D%7D"


def fetch_stocks():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": str(e)}


def format_seen(seen_iso):
    try:
        utc_time = datetime.fromisoformat(seen_iso.replace("Z", "+00:00"))
        local_time = utc_time.astimezone(pytz.timezone("America/New_York"))
        return local_time.strftime("%I:%M:%S %p")  # Just time
    except Exception:
        return "Invalid time"


@app.route("/")
def home():
    return jsonify({"message": "GAG Stocks API"})


@app.route("/api/stocks")
def stocks():
    data = fetch_stocks()
    if "error" in data:
        return jsonify({"error": data["error"]}), 500

    try:
        items = data[0]["result"]["data"]["json"]["items"]
    except (KeyError, IndexError, TypeError):
        return jsonify({"error": "Unexpected data structure"}), 500

    output = {
        "Plants": [],
        "Weather": [],
        "Other": []
    }

    for item in items:
        item_type = item.get("type")
        base = {
            "emoji": item.get("emoji"),
            "image": item.get("image"),
            "name": item.get("name"),
        }

        if item_type == "plant":
            base["value"] = item.get("value")
            output["Plants"].append(base)
        elif item_type == "weather":
            seen_iso = item.get("seen")
            time_str = format_seen(seen_iso)
            base["seen"] = time_str
            base["lastSeen"] = time_str
            output["Weather"].append(base)
        elif item_type == "other":
            base["value"] = item.get("value")
            output["Other"].append(base)

    return jsonify(output)
