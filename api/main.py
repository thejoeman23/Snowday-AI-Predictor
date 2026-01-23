from pathlib import Path

from fastapi import FastAPI

from datetime import datetime, timedelta

import pickle
import pandas as pd

import weather_fetcher

from explainer import GetExplanations

from zoneinfo import ZoneInfo

# ───────────────────────────────────────────────────────────────
# App + Paths
# ───────────────────────────────────────────────────────────────

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.pkl"
COUNTER_PATH = BASE_DIR / "counter.csv"


# ───────────────────────────────────────────────────────────────
# Allowing
# ───────────────────────────────────────────────────────────────

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://snowdaypredictor.io", "http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────────────────────────────────────────────────────────
# Load Model
# ───────────────────────────────────────────────────────────────

if not MODEL_PATH.exists():
    raise RuntimeError("model.pkl not found — deployment misconfigured")

with open(MODEL_PATH, "rb") as f:
    MODEL = pickle.load(f)

# ───────────────────────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────────────────────

@app.get("/predict")
async def predictions(lat: float, lon: float):
    # Get prediction data
    data = weather_fetcher.get_this_weeks_data(lat, lon)
    print(lat, lon)

    X = data.drop(columns=["date", "snow_day"], errors="ignore")

    probs = MODEL.predict_proba(X)[:, 1]
    data["snow_day_probability"] = probs

    results = []
    for i, row in data.iterrows():
        weekday = describe_day(row["date"])
        odds = int(round(row["snow_day_probability"] * 100))

        results.append({
            "weekday": weekday,
            "snow_day_probability": float(odds),
        })

    return results

@app.get("/explain")
async def explain(lat: float, lon: float):
    data = weather_fetcher.get_this_weeks_data(lat, lon)

    X = data.drop(columns=["date", "snow_day"], errors="ignore")
    X = X.iloc[:1]  # explain today only

    all_explanations = GetExplanations(X, MODEL)
    explanations = all_explanations[0]  # list of explanation dicts

    results = []

    for explanation in explanations:
        if explanation["humanized_value"] is not None:
            results.append({
                "reason": explanation["humanized_value"]
            })

    return results


COUNTER = {
    "value": 0,
    "last_date": None,
    "hour": None
}

@app.get("/count")
async def update_counter():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    hour = now.hour

    # Reset if new day
    if COUNTER["last_date"] != today_str:
        COUNTER["value"] = 0
        COUNTER["last_date"] = today_str

    # Reset ONCE when crossing before → after school start
    elif COUNTER["hour"] is not None and COUNTER["hour"] < 7 and hour >= 7:
        COUNTER["value"] = 0

    COUNTER["hour"] = hour
    COUNTER["value"] += 1

    return COUNTER["value"]


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────

def describe_day(target_date):
    now = datetime.now(ZoneInfo("America/Toronto"))

    date = pd.to_datetime(target_date).date()
    today = now.date()

    diff = (date - today).days

    if diff == 0:
        return "Today"
    if diff == 1:
        return "Tomorrow"

    return pd.Timestamp(date).day_name()

# ───────────────────────────────────────────────────────────────
# Run App
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)