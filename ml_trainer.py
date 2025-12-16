import pandas as pd
import weather_fetcher as weather
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

# ---------------- CONFIG ----------------

BRAIN_CELLS = 100
SEED = 42
TEST_SIZE = 0.7

# ----------------------------------------

def Train(data):
    global MODEL

    x = data.drop(columns=["date", "snow_day"])
    y = data["snow_day"]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y,
        test_size=TEST_SIZE,
        random_state=SEED
    )

    # 🔍 GRID SEARCH
    param_grid = {
        "n_estimators": [100, 300, 500],
        "max_depth": [None, 6, 10, 15],
        "min_samples_split": [2, 5, 10],
        "class_weight": ["balanced"]
    }

    base_model = RandomForestClassifier(
        random_state=SEED
    )

    grid = GridSearchCV(
        base_model,
        param_grid,
        cv=5,
        scoring="recall",   # snow days matter more
        n_jobs=-1
    )

    grid.fit(x_train, y_train)

    MODEL = grid.best_estimator_

    print("BEST MODEL SETTINGS:")
    print(grid.best_params_)
    print()

    # ---------------- EVALUATION ----------------

    y_pred = MODEL.predict(x_test)

    print("Accuracy:", accuracy_score(y_test, y_pred))
    print()

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    print(f"Predicted {tn}/{tn + fp} non-snow days")
    print(f"Predicted {tp}/{tp + fn} snow days")
    print()


def PrintFeatureImportance():
    importances = MODEL.feature_importances_

    features = TRAINING_DATA.drop(columns=["date", "snow_day"]).columns
    importance_df = pd.DataFrame({
        "feature": features,
        "importance": importances
    }).sort_values(by="importance", ascending=False)

    print("\nTOP FACTORS THE MODEL USES:")
    for _, row in importance_df.head(8).iterrows():
        print(f"- {row['feature']}")


def Test(data):
    X = data.drop(columns=["date", "snow_day"], errors="ignore")

    probs = MODEL.predict_proba(X)[:, 1]

    results = data.copy()
    results["snow_day_probability"] = probs

    print("SNOW DAY ODDS")

    for _, row in results.iterrows():
        weekday = pd.to_datetime(row["date"]).day_name()
        odds = row["snow_day_probability"] * 100
        print(f"{row['date']} ({weekday}) → {odds:.1f}% chance of snow day (so {"yes" if odds > 50 else "no"}")

# ---------------- RUN ----------------
TRAINING_DATA = pd.read_csv("snowday_dataset.csv")
TESTING_DATA = weather.get_data_within_timerange("2025-11-25", "2025-12-15")

Train(TRAINING_DATA)
#PrintFeatureImportance()
Test(TESTING_DATA)
