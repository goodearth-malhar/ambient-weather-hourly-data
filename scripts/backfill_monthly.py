import os
import json
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_DIR = os.path.join(PROJECT_ROOT, "data", "daily")
MONTHLY_DIR = os.path.join(PROJECT_ROOT, "data", "monthly")

os.makedirs(MONTHLY_DIR, exist_ok=True)

def avg(values):
    nums = [v for v in values if isinstance(v, (int, float))]
    return round(sum(nums) / len(nums), 2) if nums else None

monthly = defaultdict(lambda: {
    "temperature": [],
    "humidity": [],
    "pressure": [],
    "wind_speed": [],
    "max_gust": 0,
    "total_rain": 0,
    "days": 0
})

for file in os.listdir(DAILY_DIR):
    if not file.endswith(".json"):
        continue

    date = file.replace(".json", "")
    month = date[:7]

    with open(os.path.join(DAILY_DIR, file), "r") as f:
        data = json.load(f)

    bucket = monthly[month]

    bucket["temperature"].append(data["outdoor"]["avgTemperature"])
    bucket["humidity"].append(data["outdoor"]["avgHumidity"])
    bucket["pressure"].append(data["pressure"]["avgRelative"])
    bucket["wind_speed"].append(data["wind"]["avgSpeed"])
    bucket["max_gust"] = max(bucket["max_gust"], data["wind"]["maxGust"])
    bucket["total_rain"] += data["rain"]["total"]
    bucket["days"] += 1

for month, values in monthly.items():
    out_file = os.path.join(MONTHLY_DIR, f"{month}.json")

    if os.path.exists(out_file):
        continue

    summary = {
        "month": month,
        "daysAggregated": values["days"],
        "outdoor": {
            "avgTemperature": avg(values["temperature"]),
            "avgHumidity": avg(values["humidity"])
        },
        "wind": {
            "avgSpeed": avg(values["wind_speed"]),
            "maxGust": round(values["max_gust"], 2)
        },
        "pressure": {
            "avgRelative": avg(values["pressure"])
        },
        "rain": {
            "total": round(values["total_rain"], 2)
        }
    }

    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Backfilled monthly: {out_file}")
