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

def format_last_seen_items(items):
    if not isinstance(items, list):
        return [], "N/A"

    tz = pytz.timezone("America/New_York")
    formatted = []
    latest_dt = None

    for item in items:
        seen = item.get("seen")
        if seen:
            try:
                dt = datetime.fromisoformat(seen.rstrip("Z")).astimezone(tz)
                seen_str = dt.strftime("%m/%d/%Y, %I:%M:%S %p")
                formatted.append({
                    "name": item.get("name"),
                    "image": item.get("image"),
                    "emoji": item.get("emoji"),
                    "seen": seen_str,
                })
                if not latest_dt or dt > latest_dt:
                    latest_dt = dt
            except Exception:
                formatted.append({
                    "name": item.get("name"),
                    "image": item.get("image"),
                    "emoji": item.get("emoji"),
                    "seen": "Invalid date",
                })
        else:
            formatted.append({
                "name": item.get("name"),
                "image": item.get("image"),
                "emoji": item.get("emoji"),
                "seen": "N/A",
            })

    last_seen_time = latest_dt.strftime("%I:%M:%S %p") if latest_dt else "N/A"
    return formatted, last_seen_time

def format_stocks(data):
    stocks = data[0].get("result", {}).get("data", {}).get("json")
    if not stocks:
        raise ValueError("Malformed data structure from upstream API")

    weather_items, weather_last_seen = format_last_seen_items(stocks.get("lastSeen", {}).get("Weather", []))
    seeds_items, _ = format_last_seen_items(stocks.get("lastSeen", {}).get("Seeds", []))
    gears_items, _ = format_last_seen_items(stocks.get("lastSeen", {}).get("Gears", []))
    eggs_items, _ = format_last_seen_items(stocks.get("lastSeen", {}).get("Eggs", []))

    return {
        "GearStock": format_stock_items(stocks.get("gearStock", [])),
        "EggStock": format_stock_items(stocks.get("eggStock", [])),
        "SeedsStock": format_stock_items(stocks.get("seedsStock", [])),
        "NightStock": format_stock_items(stocks.get("nightStock", [])),
        "BloodStock": format_stock_items(stocks.get("bloodStock", [])),
        "CosmeticsStock": format_stock_items(stocks.get("cosmeticsStock", [])),
        "HoneyStock": format_stock_items(stocks.get("honeyStock", [])),
        "LastSeen": {
            "Seeds": seeds_items,
            "Gears": gears_items,
            "Eggs": eggs_items,
            "Weather": {
                "lastSeen": weather_last_seen,
                "items": weather_items
            }
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
