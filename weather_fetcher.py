import requests
import pandas as pd
from datetime import datetime, timedelta

from numpy.ma.extras import average

# ---------------- CONFIG ----------------
LATITUDE = 44.56
LONGITUDE = -81.98

SNOW_DAYS = pd.read_csv("snow_day_dates.csv")

# ----------------------------------------


def is_weekday(date: datetime) -> bool:
    return date.weekday() < 5

def fetch_weather(date_str: str, use_forecast: bool = False) -> dict:
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
            "windspeed_10m"
        ],
        "start_date": date_str,
        "end_date": date_str,
        "timezone": "auto"
    }

    r = requests.get(url, params=params)
    return r.json()


def get_data_within_timerange(start_date: str, end_date: str, use_forecast: bool = False) -> pd.DataFrame:
    """Fetch weather data for all weekdays in a date range."""
    rows = []

    current = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    snowfall_24h = 0

    while current <= end:
        if not is_weekday(current):
            current += timedelta(days=1)
            continue

        date_str = current.strftime("%Y-%m-%d")
        data = fetch_weather(date_str, use_forecast=use_forecast)

        if "hourly" not in data:
            raise ValueError(f"No hourly data returned. Keys: {data.keys()}")

        hourly = data["hourly"]

        overnight_wind = [
            v for v in hourly["windspeed_10m"][:8]
            if v is not None
        ]

        row = {
            "date": date_str,
            "snow_day": int((SNOW_DAYS["date"].astype(str) == date_str).any()),
            "snowfall_overnight": sum(hourly["snowfall"][0:7]),
            "snowfall_24h": sum(
                v if v is not None else 0
                for v in hourly["snowfall"][:24]
            ),
            "no_snowfall_penalty": 1 if sum(hourly["snowfall"][0:7]) < .5 else 0,
            "temp_min_overnight": min(hourly["temperature_2m"][0:7]),
            "windspeed_avg_overnight": (
                sum(overnight_wind) / len(overnight_wind)
                if overnight_wind else 0
            ),
        }

        for h in range(8):  # hours 0–7
            row[f"temperature{h}"] = hourly["temperature_2m"][h] or 0
            row[f"snowfall{h}"] = hourly["snowfall"][h] or 0
            row[f"windspeed{h}"] = hourly["windspeed_10m"][h] or 0


        rows.append(row)
        current += timedelta(days=1)
        print(current)

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
    """Fetch weather data for this week so far."""
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return get_data_within_timerange(
        monday.strftime("%Y-%m-%d"),
        friday.strftime("%Y-%m-%d"),
        use_forecast=True
    )


def get_next_weeks_data() -> pd.DataFrame:
    """Fetch weather data for next week (Monday to Friday)."""
    today = datetime.today()
    # Find the Monday of next week
    next_monday = today + timedelta(days=(7 - today.weekday()))
    next_friday = next_monday + timedelta(days=4)

    return get_data_within_timerange(
        next_monday.strftime("%Y-%m-%d"),
        next_friday.strftime("%Y-%m-%d"),
        use_forecast=True
    )

def get_todays_data() -> pd.DataFrame:
    """Fetch weather data for today."""
    today_str = datetime.today().strftime("%Y-%m-%d")
    return get_data_within_timerange(today_str, today_str, use_forecast=True)


def save_to_file(data: pd.DataFrame, filename: str):
    """Save DataFrame to CSV."""
    data.to_csv(filename, index=False)
    print(f"Saved {len(data)} rows to {filename}")

#data = get_data_within_timerange("2024-11-01", "2025-04-30")
#save_to_file(data, "snowday_dataset.csv")