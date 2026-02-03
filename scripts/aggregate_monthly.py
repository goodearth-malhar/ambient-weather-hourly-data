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

monthly_buckets = defaultdict(lambda: {
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

    date_part = file.replace(".json", "")  # YYYY-MM-DD
    month_key = date_part[:7]              # YYYY-MM

    with open(os.path.join(DAILY_DIR, file), "r") as f:
        data = json.load(f)

    bucket = monthly_buckets[month_key]

    bucket["temperature"].append(data["outdoor"]["avgTemperature"])
    bucket["humidity"].append(data["outdoor"]["avgHumidity"])
    bucket["pressure"].append(data["pressure"]["avgRelative"])
    bucket["wind_speed"].append(data["wind"]["avgSpeed"])

    bucket["max_gust"] = max(bucket["max_gust"], data["wind"]["maxGust"])
    bucket["total_rain"] += data["rain"]["total"]
    bucket["days"] += 1

# ==========================
# WRITE MONTHLY FILES
# ==========================
for month, values in monthly_buckets.items():
    monthly_summary = {
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

    out_file = os.path.join(MONTHLY_DIR, f"{month}.json")

    with open(out_file, "w") as f:
        json.dump(monthly_summary, f, indent=2)

    print(f"Monthly summary saved: {out_file}")
