from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import pickle
import pandas as pd

from app import weather_fetcher

# ───────────────────────────────────────────────────────────────
# App + Paths
# ───────────────────────────────────────────────────────────────

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
MODEL_PATH = BASE_DIR / "model.pkl"

# ───────────────────────────────────────────────────────────────
# Jinja Templates + Static
# ───────────────────────────────────────────────────────────────

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ───────────────────────────────────────────────────────────────
# Load Model
# ───────────────────────────────────────────────────────────────

with open(MODEL_PATH, "rb") as f:
    MODEL = pickle.load(f)

# ───────────────────────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Get prediction data
    data = weather_fetcher.get_this_weeks_data()
    X = data.drop(columns=["date", "snow_day"], errors="ignore")

    probs = MODEL.predict_proba(X)[:, 1]
    data["snow_day_probability"] = probs

    results = []
    for _, row in data.iterrows():
        weekday = describe_day(row["date"])
        odds = row["snow_day_probability"] * 100 if row.get("snowfall_24h", 0) != 0 else 0
        odds = round(odds, None)

        results.append({
            "weekday": weekday,
            "snow_day_probability": float(odds)
        })

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "data": results}
    )


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────

def describe_day(target_date):
    """
    Convert a date into a readable weekday label:
      - today
      - tomorrow
      - Monday
      - Tuesday
      etc.
    """
    date = pd.to_datetime(target_date).normalize()
    today = pd.Timestamp.today().normalize()

    diff = (date - today).days

    if diff == 0:
        return "today"
    if diff == 1:
        return "tomorrow"

    return date.day_name()