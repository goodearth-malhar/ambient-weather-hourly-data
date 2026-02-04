import os
import json
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_KEY = os.environ["AMBIENT_API_KEY"]
APP_KEY = os.environ["AMBIENT_APP_KEY"]
BASE_URL = "https://api.ambientweather.net/v1/devices"

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY_DIR = os.path.join(PROJECT_ROOT, "data", "hourly")

def safe_get(url, params, retries=3, delay=5):
    for _ in range(retries):
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 429:
            time.sleep(delay)
            delay *= 2
            continue
        r.raise_for_status()
        return r.json()
    raise Exception("Ambient API rate limit exceeded")

def expected_slots(now):
    slots = []
    end = now.replace(minute=30 if now.minute >= 30 else 0, second=0, microsecond=0)
    start = end - timedelta(hours=6)

    cur = start
    while cur <= end:
        slots.append(cur)
        cur += timedelta(minutes=30)

    return slots

def slot_path(ts):
    date_dir = ts.strftime("%Y-%m-%d")
    file_name = ts.strftime("%H-%M.json")
    return os.path.join(HOURLY_DIR, date_dir, file_name)

# ----------------------------
# Fetch device
# ----------------------------
devices = safe_get(BASE_URL, {
    "apiKey": API_KEY,
    "applicationKey": APP_KEY
})

mac = devices[0]["macAddress"]

now_ist = datetime.now(IST)

slots = expected_slots(now_ist)

for slot_end in slots:
    path = slot_path(slot_end)
    if os.path.exists(path):
        continue

    slot_start = slot_end - timedelta(minutes=30)

    start_utc = int(slot_start.astimezone(UTC).timestamp() * 1000)
    end_utc = int(slot_end.astimezone(UTC).timestamp() * 1000)

    records = safe_get(
        f"{BASE_URL}/{mac}",
        {
            "apiKey": API_KEY,
            "applicationKey": APP_KEY,
            "startDate": start_utc,
            "endDate": end_utc,
            "limit": 288
        }
    )

    if not records:
        continue

    def avg(vals):
        vals = [v for v in vals if isinstance(v, (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else None

    out = {
        "timestamp": slot_end.isoformat(),
        "source": "ambientweather-self-healing",
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
        "pressure": {
            "relative": avg([r.get("baromrelin") for r in records]),
            "absolute": avg([r.get("baromabsin") for r in records]),
        },
        "solar": {
            "uv": avg([r.get("uv") for r in records]),
            "radiation": avg([r.get("solarradiation") for r in records]),
        }
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Backfilled slot {slot_end}")
