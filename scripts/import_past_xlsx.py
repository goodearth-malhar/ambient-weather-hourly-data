import os
import json
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==========================
# CONFIG
# ==========================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "hourly")

XLSX_PATH = os.path.join(PROJECT_ROOT, "AmbientWeatherData.xlsx")
SHEET_NAME = 0  # first sheet

IST = ZoneInfo("Asia/Kolkata")

# ==========================
# LOAD EXCEL
# ==========================
df = pd.read_excel(XLSX_PATH, sheet_name=SHEET_NAME)

# Drop rows without Local Timestamp
df = df[df["Local Timestamp"].notna()]

# Convert timestamp
df["timestamp"] = pd.to_datetime(df["Local Timestamp"], errors="coerce")
df = df[df["timestamp"].notna()]

# Force IST timezone
df["timestamp"] = df["timestamp"].dt.tz_localize(IST, nonexistent="shift_forward")

# ==========================
# ALIGN TO 30-MIN WINDOWS
# ==========================
def align_30min(ts):
    minute = 30 if ts.minute >= 30 else 0
    return ts.replace(minute=minute, second=0, microsecond=0)

df["window"] = df["timestamp"].apply(align_30min)
df["delta"] = (df["timestamp"] - df["window"]).abs()

# Pick closest row per window
df = df.sort_values("delta").groupby("window").first().reset_index()

# ==========================
# HELPER
# ==========================
def num(v):
    try:
        return float(v)
    except:
        return None

# ==========================
# WRITE HOURLY FILES
# ==========================
written = 0

for _, r in df.iterrows():
    ts = r["window"]
    day = ts.strftime("%Y-%m-%d")
    fname = ts.strftime("%H-%M.json")

    out_dir = os.path.join(DATA_DIR, day)
    os.makedirs(out_dir, exist_ok=True)

    out_file = os.path.join(out_dir, fname)
    if os.path.exists(out_file):
        continue

    payload = {
        "timestamp": ts.replace(tzinfo=None).isoformat(),
        "outdoor": {
            "temperature": num(r["Temperature (°F)"]),
            "feelsLike": num(r["Feels Like (°F)"]),
            "dewPoint": num(r["Dew Point (°F)"]),
            "humidity": num(r["Humidity (%)"]),
        },
        "wind": {
            "speed": num(r["Wind Speed (mph)"]),
            "gust": num(r["Wind Gust (mph)"]),
            "maxDailyGust": num(r["Max Wind Gust (mph)"]),
            "directionDeg": num(r["Wind Direction"]),
        },
        "rain": {
            "hourly": num(r["Hourly Rainfall (in)"]),
            "daily": num(r["Daily Rain In"]),
            "weekly": num(r["Weekly Rain In"]),
            "monthly": num(r["Monthly Rain In"]),
            "yearly": num(r["Yearly Rain In"]),
            "total": num(r["Total Rain In"]),
        },
        "pressure": {
            "relative": num(r["Pressure (Rel)"]),
            "absolute": num(r["Pressure (Abs)"]),
        },
        "solar": {
            "uv": num(r["UV"]),
            "radiation": num(r["Solar Radiation"]),
        },
        "indoor": {
            "temperature": num(r["Temperature in F"]),
            "humidity": num(r["HumidityIn"]),
        }
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    written += 1

print(f"Imported {written} historical hourly files")
