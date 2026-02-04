import os
import json
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =====================
# CONFIG
# =====================
API_KEY = os.environ.get("AMBIENT_API_KEY")
APP_KEY = os.environ.get("AMBIENT_APP_KEY")

if not API_KEY or not APP_KEY:
    raise Exception("Missing Ambient Weather API keys")

BASE_URL = "https://api.ambientweather.net/v1/devices"

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY_DIR = os.path.join(PROJECT_ROOT, "data", "hourly")

MAX_LOOKBACK_HOURS = 6   # safe + cheap
SLOT_MINUTES = 30

# =====================
# HELPERS
# =====================
def safe_get(url, params, retries=3, delay=5):
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 429:
                time.sleep(delay)
                delay *= 2
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(delay)

def expected_slots(now):
    end = now.replace(
        minute=30 if now.minute >= 30 else 0,
        second=0,
        microsecond=0
    )
    start = end - timedelta(hours=MAX_LOOKBACK_HOURS)

    slots = []
    cur = start
    while cur <= end:
        slots.append(cur)
        cur += timedelta(minutes=SLOT_MINUTES)

    return slots

def slot_path(ts):
    date_dir = ts.strftime("%Y-%m-%d")
    file_name = ts.strftime("%H-%M.json")
    return os.path.join(HOURLY_DIR, date_dir, file_name)

def avg(values):
    clean = [v for v in values if isinstance(v, (int, float))]
    return round(sum(clean) / len(clean), 2) if clean else None

def max_or_none(values):
    clean = [v for v in values if isinstance(v, (int, float))]
    return max(clean) if clean else None

# =====================
# FETCH DEVICE
# =====================
devices = safe_get(BASE_URL, {
    "apiKey": API_KEY,
    "applicationKey": APP_KEY
})

if not devices:
    raise Exception("No Ambient Weather devices found")

mac = devices[0]["macAddress"]

now_ist = datetime.now(IST)
slots = expected_slots(now_ist)

# =====================
# MAIN LOOP
# =====================
for slot_end in slots:
    out_path = slot_path(slot_end)

    if os.path.exists(out_path):
        continue  # already collected

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
        print(f"No data for slot {slot_end}")
        continue

    data = {
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
            "gust": max_or_none([r.get("windgustmph") for r in records]),
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

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Recovered slot: {slot_end}")
