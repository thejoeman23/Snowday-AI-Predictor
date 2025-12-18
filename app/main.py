from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pathlib import Path

import pickle
from app import weather_fetcher
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)

# Load model
MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"

with open(MODEL_PATH, "rb") as f:
    MODEL = pickle.load(f)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # Get prediction data
    data = weather_fetcher.get_tomorrows_data()
    X = data.drop(columns=["date", "snow_day"], errors="ignore")
    probs = MODEL.predict_proba(X)[:, 1]
    data["snow_day_probability"] = probs

    results = []
    for _, row in data.iterrows():
        weekday = describe_day(row["date"])
        odds = row["snow_day_probability"] * 100 if row.get("snowfall_24h", 0) != 0 else 0.01
        results.append({
            "weekday": weekday,
            "snow_day_probability": float(odds)
        })

    # Render HTML template
    return templates.TemplateResponse("index.html", {"request": request, "data": results})

def describe_day(target_date):
    """
    Takes a date string or datetime and returns a human
    description like:
      - 'today'
      - 'tomorrow'
      - 'yesterday'
      - 'Monday'
      - 'next Tuesday'
      - 'last Friday'
    """
    
    # Normalize input to pandas Timestamp
    date = pd.to_datetime(target_date).normalize()
    today = pd.Timestamp.today().normalize()
    
    # Get difference in days
    diff = (date - today).days
    
    # Direct labels
    if diff == 0:
        return "today"
    if diff == 1:
        return "tomorrow"
    
    # Day names
    day_name = date.day_name()  # e.g. 'Monday'
    
    return day_name