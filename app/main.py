from fastapi import FastAPI
import pandas as pd
import weather_fetcher
import pickle

app = FastAPI()

# Load the trained model once when the server starts
with open("app/model.pkl", "rb") as f:
    MODEL = pickle.load(f)


@app.get("/")
def predict():
    # Get tomorrow's weather
    data = weather_fetcher.get_tomorrows_data()
    X = data.drop(columns=["date", "snow_day"], errors="ignore")

    probs = MODEL.predict_proba(X)[:, 1]
    data["snow_day_probability"] = probs

    results = []
    for _, row in data.iterrows():
        weekday = pd.to_datetime(row["date"]).day_name()
        odds = row["snow_day_probability"] * 100 if row.get("snowfall_24h", 0) != 0 else 0.01
        results.append({
            "date": row["date"],
            "weekday": weekday,
            "snow_day_probability": float(odds),
            "prediction": "yes" if odds > 50 else "no"
        })

    return results
