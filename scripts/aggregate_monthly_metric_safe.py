import os
import json
from collections import defaultdict
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_DIR = os.path.join(PROJECT_ROOT, "data", "daily")
MONTHLY_DIR = os.path.join(PROJECT_ROOT, "data", "monthly")

os.makedirs(MONTHLY_DIR, exist_ok=True)

def clean(values):
    return [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]

def avg(values):
    vals = clean(values)
    return round(sum(vals) / len(vals), 2) if vals else None

monthly = defaultdict(lambda: {
    "temp": [],
    "feels": [],
    "dew": [],
    "hum": [],
    "wind_speed": [],
    "wind_dir": [],
    "max_gust": None,
    "pressure": [],
    "uv": [],
    "radiation": [],
    "rain": 0.0,
    "days": 0
})

# ==========================
# READ DAILY FILES
# ==========================
for file in sorted(os.listdir(DAILY_DIR)):
    if not file.endswith(".json"):
        continue

    date = file.replace(".json", "")
    month = date[:7]

    with open(os.path.join(DAILY_DIR, file), "r", encoding="utf-8") as f:
        d = json.load(f)

    m = monthly[month]

    o = d.get("outdoor", {})
    w = d.get("wind", {})
    p = d.get("pressure", {})
    s = d.get("solar", {})
    r = d.get("rain", {})

    m["temp"].append(o.get("avgTemperature"))
    m["feels"].append(o.get("avgFeelsLike"))
    m["dew"].append(o.get("avgDewPoint"))
    m["hum"].append(o.get("avgHumidity"))

    m["wind_speed"].append(w.get("avgSpeed"))
    m["wind_dir"].append(w.get("avgDirection"))

    gust = w.get("maxGust")
    if isinstance(gust, (int, float)) and not math.isnan(gust):
        m["max_gust"] = gust if m["max_gust"] is None else max(m["max_gust"], gust)

    m["pressure"].append(p.get("avgRelative"))
    m["uv"].append(s.get("avgUv"))
    m["radiation"].append(s.get("avgRadiation"))

    rain = r.get("total")
    if isinstance(rain, (int, float)) and not math.isnan(rain):
        m["rain"] += rain

    m["days"] += 1

# ==========================
# WRITE MONTHLY FILES
# ==========================
for month, m in monthly.items():
    out_file = os.path.join(MONTHLY_DIR, f"{month}.json")

    monthly_data = {
        "month": month,
        "units": {
            "temperature": "C",
            "wind": "m/s",
            "pressure": "hPa",
            "rain": "mm"
        },
        "daysAggregated": m["days"],
        "outdoor": {
            "avgTemperature": avg(m["temp"]),
            "avgFeelsLike": avg(m["feels"]),
            "avgDewPoint": avg(m["dew"]),
            "avgHumidity": avg(m["hum"])
        },
        "wind": {
            "avgSpeed": avg(m["wind_speed"]),
            "maxGust": round(m["max_gust"], 2) if m["max_gust"] is not None else None,
            "avgDirection": avg(m["wind_dir"])
        },
        "pressure": {
            "avgRelative": avg(m["pressure"])
        },
        "solar": {
            "avgUv": avg(m["uv"]),
            "avgRadiation": avg(m["radiation"])
        },
        "rain": {
            "total": round(m["rain"], 2)
        }
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(monthly_data, f, indent=2)

    print(f"Rebuilt monthly (metric, safe): {out_file}")
