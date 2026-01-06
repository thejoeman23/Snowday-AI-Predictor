import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

from numpy.ma.extras import average

# ---------------- CONFIG ----------------

LATITUDE = 44.56
LONGITUDE = -81.98

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "snow_day_dates.csv"
SNOW_DAYS = pd.read_csv(CSV_PATH)

# ----------------------------------------


def is_weekday(date: datetime) -> bool:
    return date.weekday() < 5

def fetch_weather(start_date: str, end_date: str, use_forecast: bool = False) -> dict:
    if use_forecast:
        url = "https://api.open-meteo.com/v1/forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": [
            "temperature_2m",
            "snowfall",
            "windspeed_10m",
            "dewpoint_2m"
        ],
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto"
    }

    r = requests.get(url, params=params)
    return r.json()

def get_data_within_timerange(start_date: str, end_date: str, use_forecast: bool = False) -> pd.DataFrame:
    """Fetch weather data for all weekdays in a date range, using one API call."""
    print("REQUESTING:", start_date, "→", end_date)
    rows = []

    current = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    # --- FETCH ALL WEATHER AT ONCE ---
    data = fetch_weather(start_date, end_date, use_forecast=use_forecast)

    if "hourly" not in data:
        raise ValueError(f"No hourly data returned. Keys: {data.keys()}")

    hourly = data["hourly"]

    # Convert timestamps to datetime
    times = pd.to_datetime(hourly["time"])

    # Convert hourly values to NumPy for speed
    arr_temp = np.array(hourly["temperature_2m"])
    arr_snow = np.array(hourly["snowfall"])
    arr_wind = np.array(hourly["windspeed_10m"])
    arr_dew = np.array(hourly["dewpoint_2m"])

    while current <= end:

        if not is_weekday(current):
            current += timedelta(days=1)
            continue

        date_str = current.strftime("%Y-%m-%d")

        # --- MASK: hours belonging to this date only ---
        mask = (times.date == current.date())
        idx = np.where(mask)[0]

        if len(idx) == 0:
            print(f"WARNING: No hourly data for {date_str}")
            current += timedelta(days=1)
            continue

        # Today’s sliced weather values
        today_temp = arr_temp[idx]
        today_snow = arr_snow[idx]
        today_wind = arr_wind[idx]
        today_dew = arr_dew[idx]

        # Overnight = midnight to 8am window
        overnight_slice = slice(0, min(8, len(today_temp)))

        snowfall_overnight = np.nansum(today_snow[overnight_slice])
        snowfall_24h = np.nansum(today_snow)

        overnight_temp = today_temp[overnight_slice]
        overnight_wind = today_wind[overnight_slice]
        overnight_dew = today_dew[overnight_slice]

        temp_min_overnight = np.nanmin(overnight_temp)
        windspeed_avg_overnight = np.nanmean(overnight_wind)
        dewpoint_avg_overnight = np.nanmean(overnight_dew)

        # Build row
        row = {
            "date": date_str,
            "snow_day": int((SNOW_DAYS["date"].astype(str) == date_str).any()),

            "snowfall_overnight": snowfall_overnight,
            "snowfall_24h": snowfall_24h,

            "no_snowfall_penalty": (
                2 if snowfall_24h == 0
                else 1 if snowfall_overnight < 1
                else 0
            ),

            "temp_min_overnight": temp_min_overnight,
            "windspeed_avg_overnight": windspeed_avg_overnight,
            "dewpoint_avg_overnight": dewpoint_avg_overnight,
        }

        # First 8 hours feature loop
        for h in range(8):
            row[f"temperature{h}"] = today_temp[h] if h < len(today_temp) else 0
            row[f"snowfall{h}"]    = today_snow[h] if h < len(today_snow) else 0
            row[f"windspeed{h}"]   = today_wind[h] if h < len(today_wind) else 0

        rows.append(row)
        current += timedelta(days=1)

    return pd.DataFrame(rows)

def get_last_weeks_data(use_forecast: bool = False) -> pd.DataFrame:
    """Fetch weather data for last week (Mon–Fri)."""
    today = datetime.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_friday = last_monday + timedelta(days=4)
    return get_data_within_timerange(
        last_monday.strftime("%Y-%m-%d"),
        last_friday.strftime("%Y-%m-%d"),
        use_forecast=use_forecast
    )

def get_this_weeks_data() -> pd.DataFrame:
    """Return 5 weekdays starting today (before 8am) or tomorrow (after 8am)."""

    now = datetime.now()
    today = now.date()

    # Decide the starting date
    start = today if now.hour < 7 else today + timedelta(days=1)

    dates = []
    current = start

    while len(dates) < 5:
        if current.weekday() < 5:  # Mon-Fri
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # --- One fetch instead of five ---
    start_str = dates[0]
    end_str   = dates[-1]

    df = get_data_within_timerange(
        start_str,
        end_str,
        use_forecast=True
    )

    # Keep only needed rows
    df = df[df["date"].isin(dates)]

    return df.reset_index(drop=True)

def get_todays_data() -> pd.DataFrame:
    """Fetch weather data for today."""
    today_str = datetime.today().strftime("%Y-%m-%d")
    return get_data_within_timerange(today_str, today_str, use_forecast=True)

def get_tomorrows_data() -> pd.DataFrame:
    """Fetch weather data for tomorrow."""
    tomorrow_str = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    return get_data_within_timerange(tomorrow_str, tomorrow_str, use_forecast=True)


def save_to_file(data: pd.DataFrame, filename: str):
    """Save DataFrame to CSV."""
    data.to_csv(filename, index=False)
    print(f"Saved {len(data)} rows to {filename}")

#data = get_data_within_timerange("2024-11-01", "2025-04-30")
#save_to_file(data, "training_dataset.csv")

#save_to_file(get_this_weeks_data(), f"this week.csv")