from flask import Flask, jsonify
import requests
from datetime import datetime
import pytz
import time

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

cache = {
    "data": None,
    "timestamp": 0
}

def fetch_stocks():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        return response.json()
    except:
        return None

def format_stock_items(items):
    if not isinstance(items, list):
        return []
    return [
        {
            "name": item.get("name"),
            "value": item.get("value"),
            "image": item.get("image"),
            "emoji": item.get("emoji"),
        }
        for item in items
    ]

def format_last_seen_items(items):
    if not isinstance(items, list):
        return []

    tz = pytz.timezone("America/New_York")
    formatted = []
    for item in items:
        seen = item.get("seen")
        if seen:
            try:
                dt = datetime.fromisoformat(seen.rstrip("Z")).astimezone(tz)
                seen_str = dt.strftime("%m/%d/%Y, %I:%M:%S %p")
            except:
                seen_str = "Invalid date"
        else:
            seen_str = "N/A"

        formatted.append({
            "name": item.get("name"),
            "image": item.get("image"),
            "emoji": item.get("emoji"),
            "seen": seen_str,
        })

    return formatted

def format_stocks(data):
    stocks = data[0].get("result", {}).get("data", {}).get("json")
    if not stocks:
        return None

    return {
        "GearStock": format_stock_items(stocks.get("gearStock", [])),
        "EggStock": format_stock_items(stocks.get("eggStock", [])),
        "SeedsStock": format_stock_items(stocks.get("seedsStock", [])),
        "NightStock": format_stock_items(stocks.get("nightStock", [])),
        "BloodStock": format_stock_items(stocks.get("bloodStock", [])),
        "CosmeticsStock": format_stock_items(stocks.get("cosmeticsStock", [])),
        "HoneyStock": format_stock_items(stocks.get("honeyStock", [])),
        "LastSeen": {
            "Seeds": format_last_seen_items(stocks.get("lastSeen", {}).get("Seeds", [])),
            "Gears": format_last_seen_items(stocks.get("lastSeen", {}).get("Gears", [])),
            "Weather": format_last_seen_items(stocks.get("lastSeen", {}).get("Weather", [])),
            "Eggs": format_last_seen_items(stocks.get("lastSeen", {}).get("Eggs", [])),
        }
    }

@app.route("/api/stock/GetStock", methods=["GET"])
def get_stock():
    now = time.time()
    if not cache["data"] or now - cache["timestamp"] > 30:
        raw_data = fetch_stocks()
        if not raw_data:
            return jsonify({
                "success": False,
                "error": {
                    "code": 502,
                    "message": "Failed to fetch upstream data."
                }
            }), 502

        formatted = format_stocks(raw_data)
        if not formatted:
            return jsonify({
                "success": False,
                "error": {
                    "code": 500,
                    "message": "Failed to process data structure."
                }
            }), 500

        cache["data"] = {
            "success": True,
            "fetched_at": datetime.now(pytz.timezone("America/New_York")).strftime("%m/%d/%Y, %I:%M:%S %p"),
            **formatted
        }
        cache["timestamp"] = now

    return jsonify(cache["data"]), 200
