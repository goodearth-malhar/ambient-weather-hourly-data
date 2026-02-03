import os
import json
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY_DIR = os.path.join(PROJECT_ROOT, "data", "hourly")
DAILY_DIR = os.path.join(PROJECT_ROOT, "data", "daily")

os.makedirs(DAILY_DIR, exist_ok=True)

# ==========================
# UNIT CONVERSIONS
# ==========================
def f_to_c(f): return (f - 32) * 5 / 9 if f is not None else None
def mph_to_ms(v): return v * 0.44704 if v is not None else None
def inhg_to_hpa(v): return v * 33.8639 if v is not None else None
def inch_to_mm(v): return v * 25.4 if v is not None else None

def avg(values):
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 2) if vals else None

# ==========================
# DAILY AGGREGATION
# ==========================
for day in sorted(os.listdir(HOURLY_DIR)):
    day_path = os.path.join(HOURLY_DIR, day)
    out_file = os.path.join(DAILY_DIR, f"{day}.json")

    if not os.path.isdir(day_path):
        continue

    buckets = defaultdict(list)
    max_gust = None
    rain_total = 0

    for file in os.listdir(day_path):
        if not file.endswith(".json"):
            continue

        with open(os.path.join(day_path, file)) as f:
            d = json.load(f)

        o = d.get("outdoor", {})
        w = d.get("wind", {})
        p = d.get("pressure", {})
        s = d.get("solar", {})
        r = d.get("rain", {})

        buckets["temp"].append(f_to_c(o.get("temperature")))
        buckets["feels"].append(f_to_c(o.get("feelsLike")))
        buckets["dew"].append(f_to_c(o.get("dewPoint")))
        buckets["hum"].append(o.get("humidity"))

        buckets["wind_speed"].append(mph_to_ms(w.get("speed")))
        buckets["wind_dir"].append(w.get("directionDeg"))

        gust = mph_to_ms(w.get("gust"))
        if gust is not None:
            max_gust = gust if max_gust is None else max(max_gust, gust)

        buckets["pressure"].append(inhg_to_hpa(p.get("relative")))

        buckets["uv"].append(s.get("uv"))
        buckets["radiation"].append(s.get("radiation"))

        rain_total += inch_to_mm(r.get("hourly") or 0)

    daily = {
        "date": day,
        "units": {
            "temperature": "C",
            "wind": "m/s",
            "pressure": "hPa",
            "rain": "mm"
        },
        "outdoor": {
            "avgTemperature": avg(buckets["temp"]),
            "avgFeelsLike": avg(buckets["feels"]),
            "avgDewPoint": avg(buckets["dew"]),
            "avgHumidity": avg(buckets["hum"])
        },
        "wind": {
            "avgSpeed": avg(buckets["wind_speed"]),
            "maxGust": round(max_gust, 2) if max_gust is not None else None,
            "avgDirection": avg(buckets["wind_dir"])
        },
        "pressure": {
            "avgRelative": avg(buckets["pressure"])
        },
        "solar": {
            "avgUv": avg(buckets["uv"]),
            "avgRadiation": avg(buckets["radiation"])
        },
        "rain": {
            "total": round(rain_total, 2)
        }
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(daily, f, indent=2)

    print(f"Rebuilt daily (metric): {out_file}")
