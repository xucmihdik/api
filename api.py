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
        response = requests.get(URL, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return {
                "status": response.status_code,
                "message": f"Request failed with status {response.status_code}. Body: {response.text[:200]}"
            }, None

        try:
            data = response.json()
        except ValueError as e:
            return {
                "status": 500,
                "message": f"Invalid JSON response: {str(e)}. Received: {response.text[:200]}"
            }, None

        return None, data
    except requests.exceptions.Timeout:
        return {
            "status": 504,
            "message": "Request timed out"
        }, None
    except requests.exceptions.RequestException as e:
        return {
            "status": 502,
            "message": f"Problem with request: {str(e)}"
        }, None

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

def convert_seen_and_add_lastseen(item):
    tz = pytz.timezone("America/New_York")
    seen_raw = item.get("seen")
    if seen_raw:
        try:
            dt_utc = datetime.fromisoformat(seen_raw.replace("Z", "+00:00"))
            dt_local = dt_utc.astimezone(tz)
            # Format just time for "seen"
            item["seen"] = dt_local.strftime("%I:%M:%S %p").lstrip("0")
            # Format full date + time for "lastSeen"
            item["lastSeen"] = dt_local.strftime("%m/%d/%Y, %I:%M:%S %p").lstrip("0")
        except Exception:
            item["seen"] = "Invalid date"
            item["lastSeen"] = "Invalid date"
    else:
        item["seen"] = "N/A"
        item["lastSeen"] = "N/A"
    return item

def format_last_seen_items(items):
    if not isinstance(items, list):
        return []
    return [convert_seen_and_add_lastseen(item) for item in items]

def format_weather_items(items):
    return format_last_seen_items(items)

def format_stocks(data):
    stocks = data[0].get("result", {}).get("data", {}).get("json")
    if not stocks:
        raise ValueError("Malformed data structure from upstream API")

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
            "Weather": format_weather_items(stocks.get("lastSeen", {}).get("Weather", [])),
            "Eggs": format_last_seen_items(stocks.get("lastSeen", {}).get("Eggs", [])),
        }
    }

@app.route("/api/stock/GetStock", methods=["GET"])
def get_stock():
    error, data = fetch_stocks()
    if error:
        return jsonify({
            "success": False,
            "error": {
                "code": error.get("status", 500),
                "message": error.get("message", "Unknown error")
            }
        }), error.get("status", 500)

    try:
        formatted = format_stocks(data)
        return jsonify({
            "success": True,
            **formatted
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": 500,
                "message": f"Error processing stock data: {str(e)}"
            }
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
