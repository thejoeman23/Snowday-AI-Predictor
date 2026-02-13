import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

# ---------------- CONFIG ----------------

LATITUDE = 44.569
LONGITUDE = -80.98

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "snow_day_dates.csv"
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

def safe_sum(values):
    values = [v for v in values if v is not None]
    return sum(values) if values else 0

from datetime import datetime, timedelta

def fetch_weather(start_date: str, end_date: str, lat: float = LATITUDE, lon: float = LONGITUDE, use_forecast: bool = False) -> dict:

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

def get_data_within_timerange(
    start_date: str,
    end_date: str,
    lat: float,
    lon: float,
    use_forecast: bool = False,
) -> pd.DataFrame:

    print("REQUESTING:", start_date, "→", end_date)
    rows = []

    # Convert to datetime
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    if not use_forecast:
        # Clamp end_date to yesterday
        yesterday = datetime.today() - timedelta(days=1)
        if end_dt > yesterday:
            end_dt = yesterday

    # Fetch weather only for the valid range
    data = fetch_weather(
        start_dt.strftime("%Y-%m-%d"),
        end_dt.strftime("%Y-%m-%d"),
        lat=lat,
        lon=lon,
        use_forecast=use_forecast,
    )

    hourly = data["hourly"]
    daily = data["daily"]

    current = start_dt
    end = end_dt

    yesterday_snow = []

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")

        today_hourly = get_hourly_for_date(hourly, date_str)
        today_daily = get_daily_for_date(daily, date_str)

        # skip weekends
        if not is_weekday(current):
            current += timedelta(days=1)
            yesterday_snow = today_hourly["snowfall"]
            continue

        today_temp = today_hourly["temperature_2m"]
        today_precipitation = today_hourly["precipitation"]
        today_snow = today_hourly["snowfall"]
        today_wind = today_hourly["wind_speed_10m"]
        today_wind_gusts = today_hourly["wind_gusts_10m"]
        today_dew  = today_hourly["dew_point_2m"]
        today_weather_code = today_hourly["weather_code"]

        # overnight = first 8 hours
        overnight_wind = today_wind[:8]
        overnight_dew  = today_dew[:8]
        overnight_wind_gusts = today_daily["wind_gusts_10m_max"]

        snowfall_overnight = safe_sum(today_snow[:8])
        snowfall_24h = safe_sum(today_snow)

        precipitation_overnight = safe_sum(today_precipitation[:8])
        precipitation_24h = safe_sum(today_precipitation)

        row = {
            "date": date_str,
            "snow_day": int((SNOW_DAYS["date"].astype(str) == date_str).any()),

            "snowfall_last_24h": (safe_sum(yesterday_snow[7:]) + snowfall_overnight) if yesterday_snow else 0,
            "snowfall_last_12h": (safe_sum(yesterday_snow[20:]) + snowfall_overnight) if yesterday_snow else 0,
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
            "wind_gusts_max_overnight": overnight_wind_gusts,
            "dewpoint_avg_overnight": safe_mean(overnight_dew),
        }

        # first 8 hours
        for h in range(8):
            row[f"temperature{h}"] = today_temp[h] if h < len(today_temp) else 0
            row[f"precipitation{h}"] = today_precipitation[h] if h < len(today_precipitation) else 0
            row[f"snowfall{h}"] = today_snow[h] if h < len(today_snow) else 0
            row[f"wind_speed{h}"] = today_wind[h] if h < len(today_wind) else 0
            row[f"wind_gusts{h}"] = today_wind_gusts[h] if h < len(today_wind_gusts) else 0
            row[f"weather_code{h}"] = any(code in {71,73,75,77,85,86} for code in today_weather_code)
            #row[f"blowing_snow_risk{h}"] = row[f"snowfall{h}"] * row[f"wind_gusts{h}"]

        rows.append(row)
        current += timedelta(days=1)

        yesterday_snow = today_snow

    return pd.DataFrame(rows)

def get_weather_code_label(code) -> str:
    codes = {
        66: "Freezing Rain (Light)",
        67: "Freezing Rain (Heavy)",

        71: "Snowfall (Light)",
        73: "Snowfall (Moderate)",
        75: "Snowfall (Heavy)",

        77: "Snow Grains",

        85: "Snow Showers (Light)",
        86: "Snow Showers (Heavy)",
    }

    return codes.get(code, "Other")


def t() -> pd.DataFrame:
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    print(monday.day)
    return get_data_within_timerange(
        monday.strftime("%Y-%m-%d"),
        friday.strftime("%Y-%m-%d"),
        lat=LATITUDE,
        lon=LONGITUDE,
        use_forecast=True
    )

def get_this_weeks_data(lat: float = 0, lon: float = 0) -> pd.DataFrame:
    if lat == 0 and lon == 0:
        lat, lon = LATITUDE, LONGITUDE

    tz = ZoneInfo("America/Toronto")
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

#data = get_data_within_timerange("2024-11-01", "2025-04-30")
#save_to_file(data, "../data/training_dataset_1.csv")

#data = t()
#save_to_file(data, f"this week.csv")