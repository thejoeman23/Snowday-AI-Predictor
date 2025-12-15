import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

# ---------------- CONFIG ----------------

BRAIN_CELLS = 500
SEED = 42
TEST_SIZE = 0.5

MODEL = RandomForestClassifier(
    n_estimators=BRAIN_CELLS,
    random_state=SEED
)

# ----------------------------------------


def Train(data):
    x = data.drop(columns=["date", "snow_day"])
    y = data["snow_day"]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y,
        test_size=TEST_SIZE,
        random_state=SEED
    )

    MODEL.fit(x_train, y_train)

    y_pred = MODEL.predict(x_test)

    print("Accuracy:", accuracy_score(y_test, y_pred))
    print()

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    print(f"Predicted {tn}/{tn + fp} non-snow days")
    print(f"Predicted {tp}/{tp + fn} snow days")
    print()


def Test(data):
    X = data.drop(columns=["date", "snow_day"], errors="ignore")

    probs = MODEL.predict_proba(X)[:, 1]

    results = data.copy()
    results["snow_day_probability"] = probs

    print("SNOW DAY ODDS")

    for _, row in results.iterrows():
        weekday = pd.to_datetime(row["date"]).day_name()
        odds = row["snow_day_probability"] * 100
        print(f"{row['date']} ({weekday}) → {odds:.1f}% chance of snow day")


# ---------------- RUN ----------------
TRAINING_DATA = pd.read_csv("snowday_dataset.csv")

Train(TRAINING_DATA)

# Example usage later:
# TEST_DATA = pd.read_csv("last_week.csv")
# Test(TEST_DATA)
