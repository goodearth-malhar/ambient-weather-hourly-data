import os
import json
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY_DIR = os.path.join(PROJECT_ROOT, "data", "hourly")
DAILY_DIR = os.path.join(PROJECT_ROOT, "data", "daily")

os.makedirs(DAILY_DIR, exist_ok=True)

def avg(values):
    nums = [v for v in values if isinstance(v, (int, float))]
    return round(sum(nums) / len(nums), 2) if nums else None

for day in os.listdir(HOURLY_DIR):
    day_path = os.path.join(HOURLY_DIR, day)
    if not os.path.isdir(day_path):
        continue

    daily_data = defaultdict(list)
    max_gust = 0
    total_rain = 0

    for file in os.listdir(day_path):
        if not file.endswith(".json"):
            continue

        with open(os.path.join(day_path, file), "r") as f:
            data = json.load(f)

        daily_data["temperature"].append(data["outdoor"]["temperature"])
        daily_data["humidity"].append(data["outdoor"]["humidity"])
        daily_data["pressure"].append(data["pressure"]["relative"])
        daily_data["wind_speed"].append(data["wind"]["speed"])

        max_gust = max(max_gust, data["wind"]["gust"])
        total_rain += data["rain"]["hourly"]

    daily_summary = {
        "date": day,
        "outdoor": {
            "avgTemperature": avg(daily_data["temperature"]),
            "avgHumidity": avg(daily_data["humidity"]),
        },
        "wind": {
            "avgSpeed": avg(daily_data["wind_speed"]),
            "maxGust": round(max_gust, 2)
        },
        "pressure": {
            "avgRelative": avg(daily_data["pressure"])
        },
        "rain": {
            "total": round(total_rain, 2)
        }
    }

    out_file = os.path.join(DAILY_DIR, f"{day}.json")

    with open(out_file, "w") as f:
        json.dump(daily_summary, f, indent=2)

    print(f"Daily summary saved: {out_file}")
