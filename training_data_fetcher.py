import requests
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
START_DATE = "2025-12-07"
END_DATE   = "2025-12-12"

LATITUDE = 44.56
LONGITUDE = -81.98

OUTPUT_FILE = "last_week.csv"

SNOW_DAYS = pd.read_csv("snow_day_dates.csv")
# ----------------------------------------


def is_weekday(date):
    return date.weekday() < 5  # Mon–Fri


def fetch_weather(date_str):
    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": [
            "temperature_2m",
            "snowfall",
            "windspeed_10m",
            "visibility",
            "precipitation_type"
        ],
        "start_date": date_str,
        "end_date": date_str,
        "timezone": "auto"
    }

    r = requests.get(url, params=params)
    #r.raise_for_status()
    return r.json()


rows = []

current = datetime.fromisoformat(START_DATE)
end = datetime.fromisoformat(END_DATE)

while current <= end:
    if not is_weekday(current):
        current += timedelta(days=1)
        continue

    date_str = current.strftime("%Y-%m-%d")
    data = fetch_weather(date_str)

    if "hourly" not in data:
        raise ValueError(f"No hourly data returned. Keys: {data.keys()}")

    hourly = data["hourly"]

    row = {
        "date": date_str,
        "snow_day": int((SNOW_DAYS["date"].astype(str) == date_str).any())
    }

    for h in range(8):  # hours 0–7
        row[f"temperature{h}"]  = hourly["temperature_2m"][h] if hourly["temperature_2m"][h] is not None else 0
        row[f"snowfall{h}"]     = hourly["snowfall"][h] if hourly["snowfall"][h] is not None else 0
        row[f"windspeed{h}"]    = hourly["windspeed_10m"][h] if hourly["windspeed_10m"][h] is not None else 0
        row[f"visibility{h}"]   = hourly["visibility"][h] if hourly["visibility"][h] is not None else 0
        row[f"precip_type{h}"]  = hourly["precipitation_type"][h] if hourly["precipitation_type"][h] is not None else 0

    rows.append(row)
    current += timedelta(days=1)
    print(current);


df = pd.DataFrame(rows)
df.to_csv(OUTPUT_FILE, index=False)

print(f"Saved {len(df)} rows to {OUTPUT_FILE}")
