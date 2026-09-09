from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from app.core.config import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    LOCAL_TIMEZONE,
    SNOW_DAY_DATES_PATH,
)

SNOW_DAYS = pd.read_csv(SNOW_DAY_DATES_PATH)
SNOW_DAY_SET = set(SNOW_DAYS["date"].astype(str))


def is_weekday(day: date) -> bool:
    return day.weekday() < 5

HOURLY_START = 4
HOURLY_END = 9
HOURLY_RANGE = range(HOURLY_START, HOURLY_END + 1)
SNOW_WEATHER_CODES = {71, 73, 75, 77, 85, 86}
FREEZING_RAIN_CODES = {51, 53, 55, 61, 63, 65, 66, 67}


def format_weather_date(value: str | date | datetime) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        return value.isoformat()
    else:
        parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(ZoneInfo(LOCAL_TIMEZONE))

    return parsed.date().isoformat()


def fetch_weather(
    start_date: str,
    end_date: str,
    lat: float = DEFAULT_LATITUDE,
    lon: float = DEFAULT_LONGITUDE,
    use_forecast: bool = False,
) -> dict:

    if use_forecast:
        url = "https://api.open-meteo.com/v1/forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,

        "start_date": start_date,
        "end_date": end_date,

        "daily": ["temperature_2m_min", "wind_gusts_10m_max"],
        "hourly": ["temperature_2m", "dew_point_2m", "precipitation", "snowfall",
                   "weather_code", "wind_speed_10m", "wind_gusts_10m"],

        "timezone": LOCAL_TIMEZONE,
    }

    r = requests.get(url, params=params)
    return r.json()


def build_hourly_dataframe(hourly: dict) -> pd.DataFrame:
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.date.astype(str)
    return df[df["time"].dt.hour.isin(HOURLY_RANGE)]


def build_daily_dataframe(daily: dict) -> pd.DataFrame:
    df = pd.DataFrame(daily)
    df["date"] = pd.to_datetime(df["time"]).dt.date.astype(str)
    return df.set_index("date")


def build_feature_row(day: str, hourly: pd.DataFrame, daily: pd.Series) -> dict:
    snowfall_4_9am = hourly["snowfall"].sum()
    precipitation_4_9am = hourly["precipitation"].sum()
    temp_min = daily["temperature_2m_min"]

    return {
        "date": day,
        "snow_day": int(day in SNOW_DAY_SET),
        "snowfall_4_9am": snowfall_4_9am,
        "precipitation_4_9am": precipitation_4_9am,
        "temperature_4_9am_min": hourly["temperature_2m"].min(),
        "temperature_4_9am_avg": hourly["temperature_2m"].mean(),
        "wind_speed_4_9am_avg": hourly["wind_speed_10m"].mean(),
        "wind_gusts_4_9am_max": hourly["wind_gusts_10m"].max(),
        "dewpoint_4_9am_avg": hourly["dew_point_2m"].mean(),
        "snow_weather_code_4_9am": int(
            hourly["weather_code"].isin(SNOW_WEATHER_CODES).any()
        ),
        "freezing_rain": int(
            hourly["weather_code"].isin(FREEZING_RAIN_CODES).any()
            and -2 <= temp_min <= 1
        ),
        "temp_min": temp_min,
        "daily_wind_gusts_max": daily["wind_gusts_10m_max"],
        "no_snowfall_4_9am_penalty": (
            2 if snowfall_4_9am == 0
            else 1 if snowfall_4_9am < 1
            else 0
        ),
    }


def weekdays_between(start_day: date, end_day: date):
    current = start_day
    while current <= end_day:
        if is_weekday(current):
            yield current.isoformat()
        current += timedelta(days=1)


def get_data_within_timerange(
    start_date: str,
    end_date: str,
    lat: float,
    lon: float,
    use_forecast: bool = False,
) -> pd.DataFrame:

    print("REQUESTING:", start_date, "→", end_date)
    rows = []

    start_date = format_weather_date(start_date)
    end_date = format_weather_date(end_date)
    start_day = date.fromisoformat(start_date)
    end_day = date.fromisoformat(end_date)

    data = fetch_weather(
        start_date,
        end_date,
        lat=lat,
        lon=lon,
        use_forecast=use_forecast,
    )

    hourly_by_date = build_hourly_dataframe(data["hourly"]).groupby("date")
    daily_by_date = build_daily_dataframe(data["daily"])

    for day in weekdays_between(start_day, end_day):
        rows.append(
            build_feature_row(day, hourly_by_date.get_group(day), daily_by_date.loc[day])
        )

    return pd.DataFrame(rows)


def t() -> pd.DataFrame:
    today = datetime.now(ZoneInfo(LOCAL_TIMEZONE)).date()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    print(monday.day)
    return get_data_within_timerange(
        monday.isoformat(),
        friday.isoformat(),
        lat=DEFAULT_LATITUDE,
        lon=DEFAULT_LONGITUDE,
        use_forecast=True
    )

def get_this_weeks_data(lat: float = 0, lon: float = 0) -> pd.DataFrame:
    if lat == 0 and lon == 0:
        lat, lon = DEFAULT_LATITUDE, DEFAULT_LONGITUDE

    tz = ZoneInfo(LOCAL_TIMEZONE)
    now = datetime.now(tz)
    today = now.date()

    start = today if now.hour < 7 else today + timedelta(days=1)

    dates = []
    current = start

    while len(dates) < 5:
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current += timedelta(days=1)

    df = get_data_within_timerange(
        dates[0],
        dates[-1],
        lat,
        lon,
        use_forecast=True
    )

    df = df[df["date"].isin(dates)]
    return df.reset_index(drop=True)

def save_to_file(data: pd.DataFrame, filename: str):
    """Save DataFrame to CSV."""
    data.to_csv(filename, index=False)
    print(f"Saved {len(data)} rows to {filename}")

data = t()
save_to_file(data, "this week.csv")