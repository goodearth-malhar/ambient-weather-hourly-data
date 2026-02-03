import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import time
import os

# ==========================
# CONFIG (READ FROM ENVIRONMENT VARIABLES)
# ==========================
API_KEY = os.environ.get("AMBIENT_API_KEY")
APP_KEY = os.environ.get("AMBIENT_APP_KEY")

if not API_KEY or not APP_KEY:
    raise Exception("Missing Ambient Weather API keys")

BASE_URL = "https://api.ambientweather.net/v1/devices"

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

# ==========================
# SAFE REQUEST WITH RETRY
# ==========================
def safe_get(url, params, retries=3, delay=5):
    for _ in range(retries):
        response = requests.get(url, params=params)
        if response.status_code == 429:
            time.sleep(delay)
            delay *= 2
            continue
        response.raise_for_status()
        return response.json()
    raise Exception("API rate limit exceeded after retries")

# ==========================
# TIME WINDOW (ALIGNED 30 MIN)
# ==========================
now_ist = datetime.now(IST)

if now_ist.minute >= 30:
    window_end = now_ist.replace(minute=30, second=0, microsecond=0)
else:
    window_end = now_ist.replace(minute=0, second=0, microsecond=0)

window_start = window_end - timedelta(minutes=30)

start_utc = int(window_start.astimezone(UTC).timestamp() * 1000)
end_utc = int(window_end.astimezone(UTC).timestamp() * 1000)

# ==========================
# FETCH DEVICES
# ==========================
devices = safe_get(
    BASE_URL,
    {
        "apiKey": API_KEY,
        "applicationKey": APP_KEY
    }
)

if not devices:
    raise Exception("No devices found")

device = devices[0]
mac = device["macAddress"]

# Mandatory pause for Ambient API
time.sleep(3)

# ==========================
# FETCH HISTORICAL DATA
# ==========================
history_url = f"{BASE_URL}/{mac}"

history_response = safe_get(
    history_url,
    {
        "apiKey": API_KEY,
        "applicationKey": APP_KEY,
        "startDate": start_utc,
        "endDate": end_utc,
        "limit": 288
    }
)

# Handle both API response shapes
if isinstance(history_response, dict):
    records = history_response.get("data", [])
elif isinstance(history_response, list):
    records = history_response
else:
    records = []

if not records:
    raise Exception("No data in selected 30-minute window")

# ==========================
# HELPER
# ==========================
def avg(values):
    nums = [v for v in values if isinstance(v, (int, float))]
    return round(sum(nums) / len(nums), 2) if nums else None

# ==========================
# BUILD RESULT JSON
# ==========================
result = {
    "timestamp": window_end.isoformat(),
    "source": "ambientweather-averaged-30min",
    "outdoor": {
        "temperature": avg([r.get("tempf") for r in records]),
        "feelsLike": avg([r.get("feelsLike") for r in records]),
        "dewPoint": avg([r.get("dewPoint") for r in records]),
        "humidity": avg([r.get("humidity") for r in records]),
    },
    "wind": {
        "speed": avg([r.get("windspeedmph") for r in records]),
        "gust": max((r.get("windgustmph", 0) for r in records), default=0),
        "directionDeg": avg([r.get("winddir") for r in records]),
    },
    "rain": {
        "hourly": max((r.get("hourlyrainin", 0) for r in records), default=0),
        "daily": max((r.get("dailyrainin", 0) for r in records), default=0),
        "weekly": max((r.get("weeklyrainin", 0) for r in records), default=0),
    },
    "pressure": {
        "relative": avg([r.get("baromrelin") for r in records]),
        "absolute": avg([r.get("baromabsin") for r in records]),
    },
    "indoor": {
        "temperature": avg([r.get("tempinf") for r in records]),
        "humidity": avg([r.get("humidityin") for r in records]),
    },
    "solar": {
        "uv": avg([r.get("uv") for r in records]),
        "radiation": avg([r.get("solarradiation") for r in records]),
    }
}

# ==========================
# SAVE TO PROJECT ROOT
# ==========================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

date_folder = window_end.strftime("%Y-%m-%d")
time_file = window_end.strftime("%H-%M.json")

base_dir = os.path.join(PROJECT_ROOT, "data", "hourly", date_folder)
os.makedirs(base_dir, exist_ok=True)

file_path = os.path.join(base_dir, time_file)

if os.path.exists(file_path):
    print(f"File already exists, skipping: {file_path}")
else:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved data to {file_path}")
