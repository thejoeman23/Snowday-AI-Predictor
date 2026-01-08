import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

# ---------------- CONFIG ----------------

LATITUDE = 44.56
LONGITUDE = -81.98

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "snow_day_dates.csv"
SNOW_DAYS = pd.read_csv(CSV_PATH)

# ----------------------------------------


def is_weekday(date: datetime) -> bool:
    return date.weekday() < 5

def safe_min(values):
    values = [v for v in values if v is not None]
    return min(values) if values else 0

def safe_mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0

def fetch_weather(start_date: str, end_date: str, use_forecast: bool = False) -> dict:
    if use_forecast:
        url = "https://api.open-meteo.com/v1/forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,

        "start_date": start_date,
        "end_date": end_date,

        "daily": ["temperature_2m_mean", "snowfall_sum", "precipitation_sum", "temperature_2m_min",
                  "wind_gusts_10m_max"],
        "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "snowfall", "snow_depth",
                   "weather_code", "wind_speed_10m", "wind_gusts_10m"],

        "timezone": "America/New_York",
    }

    r = requests.get(url, params=params)
    return r.json()

def get_hourly_for_date(hourly, target_date):

    hourly_times = pd.to_datetime(hourly["time"]).strftime("%Y-%m-%d")

    mask = (hourly_times == target_date)

    if not mask.any():
        return None

    # Creates a dictionary
    return {
        key: [hourly[key][i] for i, ok in enumerate(mask) if ok]
        for key in hourly.keys()
    }

def get_daily_for_date(daily, target_date):

    daily_times = pd.to_datetime(daily["time"]).strftime("%Y-%m-%d")

    mask = (daily_times == target_date)

    if not mask.any():
        return None

    # first matching daily row
    day_index = list(mask).index(True)

    # creating a dictionary
    return {key: daily[key][day_index] for key in daily.keys()}

def get_data_within_timerange(start_date: str, end_date: str, use_forecast: bool = False) -> pd.DataFrame:
    print("REQUESTING:", start_date, "→", end_date)
    rows = []

    current = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    data = fetch_weather(start_date, end_date, use_forecast=use_forecast)

    hourly = data["hourly"]
    daily = data["daily"]

    # pandas datetimes for matching

    while current <= end:

        # skip weekends
        if not is_weekday(current):
            current += timedelta(days=1)
            continue

        date_str = current.strftime("%Y-%m-%d")

        today_hourly = get_hourly_for_date(hourly, date_str)
        today_daily = get_daily_for_date(daily, date_str)

        today_temp = today_hourly["temperature_2m"]
        today_precipitation = today_hourly["precipitation"]
        today_snow = today_hourly["snowfall"]
        today_snow_depth = today_hourly["snow_depth"]
        today_wind = today_hourly["wind_speed_10m"]
        today_wind_gusts = today_hourly["wind_gusts_10m"]
        today_humidity = today_hourly["relative_humidity_2m"]
        today_dew  = today_hourly["dew_point_2m"]
        today_weather_code = today_hourly["weather_code"]

        # overnight = first 8 hours
        overnight_wind = today_wind[:8]
        overnight_dew  = today_dew[:8]
        overnight_humidity = today_humidity[:8]
        overnight_wind_gusts = today_wind_gusts[:8]

        overnight_weather_code = today_weather_code[:8]

        def safe_mean(values):
            values = [v for v in values if v is not None]
            return sum(values) / len(values) if values else 0

        snowfall_overnight = sum(today_snow[:8])
        snowfall_24h = today_daily["snowfall_sum"]

        precipitation_overnight = sum(today_precipitation[:8])
        precipitation_24h = today_daily["precipitation_sum"]

        row = {
            "date": date_str,
            "snow_day": int((SNOW_DAYS["date"].astype(str) == date_str).any()),

            "snowfall_overnight": snowfall_overnight,
            "snowfall_24h": snowfall_24h,

            "precipitation_overnight": precipitation_overnight,
            "precipitation_24h": precipitation_24h,

            "no_snowfall_penalty": (
                2 if snowfall_24h == 0
                else 1 if snowfall_overnight < 1
                else 0
            ),

            "freezing_rain": (
                    any(code in {51, 53, 55, 61, 63, 65, 66, 67} for code in today_weather_code[:17])
                    and -2 <= today_daily["temperature_2m_min"] <= 1
            ),

            "temp_min_overnight": today_daily["temperature_2m_min"],
            "wind_speed_avg_overnight": safe_mean(overnight_wind),
            "wind_gusts_max_overnight": max(overnight_wind_gusts),
            "dewpoint_avg_overnight": safe_mean(overnight_dew),
            "humidity_avg_overnight": safe_mean(overnight_humidity),
        }

        # first 8 hours
        for h in range(8):
            row[f"temperature{h}"] = today_temp[h] if h < len(today_temp) else 0
            row[f"precipitation{h}"] = today_precipitation[h] if h < len(today_precipitation) else 0
            row[f"snowfall{h}"] = today_snow[h] if h < len(today_snow) else 0
            row[f"snow_depth{h}"] = today_snow_depth[h] if h < len(today_snow_depth) else 0
            row[f"wind_speed{h}"] = today_wind[h] if h < len(today_wind) else 0
            row[f"wind_gusts{h}"] = today_wind_gusts[h] if h < len(today_wind_gusts) else 0
            row[f"weather_code{h}"] = today_weather_code[h] if h < len(today_weather_code) else 0

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

def t() -> pd.DataFrame:
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    print(monday.day)
    return get_data_within_timerange(
        monday.strftime("%Y-%m-%d"),
        friday.strftime("%Y-%m-%d"),
        use_forecast=True
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
#save_to_file(data, "../data/training_dataset_1.csv")

#data = t()
#save_to_file(data, f"this week.csv")