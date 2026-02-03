import os
import json
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
    daily_file = os.path.join(DAILY_DIR, f"{day}.json")

    if not os.path.isdir(day_path):
        continue

    if os.path.exists(daily_file):
        continue  # already exists

    data_points = defaultdict(list)
    max_gust = 0
    total_rain = 0

    for file in os.listdir(day_path):
        if not file.endswith(".json"):
            continue

        with open(os.path.join(day_path, file), "r") as f:
            data = json.load(f)

        data_points["temperature"].append(data["outdoor"]["temperature"])
        data_points["humidity"].append(data["outdoor"]["humidity"])
        data_points["pressure"].append(data["pressure"]["relative"])
        data_points["wind_speed"].append(data["wind"]["speed"])

        max_gust = max(max_gust, data["wind"]["gust"])
        total_rain += data["rain"]["hourly"]

    if not data_points["temperature"]:
        continue

    daily_summary = {
        "date": day,
        "outdoor": {
            "avgTemperature": avg(data_points["temperature"]),
            "avgHumidity": avg(data_points["humidity"]),
        },
        "wind": {
            "avgSpeed": avg(data_points["wind_speed"]),
            "maxGust": round(max_gust, 2)
        },
        "pressure": {
            "avgRelative": avg(data_points["pressure"])
        },
        "rain": {
            "total": round(total_rain, 2)
        }
    }

    with open(daily_file, "w") as f:
        json.dump(daily_summary, f, indent=2)

    print(f"Backfilled daily: {daily_file}")
