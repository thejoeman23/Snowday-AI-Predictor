import pandas as pd
import numpy as np
import pickle
import weather_fetcher as weather

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

import shap

# ---------------- CONFIG ----------------

BRAIN_CELLS = 100
SEED = 42
TEST_SIZE = 0.8

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
        "class_weight": [None, "balanced"],
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

    with open("model.pkl", "wb") as f:  # <- save to a folder your server can access
        pickle.dump(MODEL, f)
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

def GetExplanations(data, model):
    explainer = shap.TreeExplainer(
        model,
        model_output="raw"
    )

    for i in data.index:
        row = data.loc[[i]]  # <-- keep 2D

        shap_values = explainer(row)

        exp = shap.Explanation(
            values=shap_values.values[0, :, 1],
            base_values=shap_values.base_values[0, 1],
            data=row.iloc[0],
            feature_names=row.columns
        )

        # Zip everything together
        items = list(zip(
            exp.feature_names,
            exp.values,
            exp.data
        ))

        # Sort by absolute SHAP value (descending)
        items_sorted = sorted(
            items,
            key=lambda x: abs(x[1]),
            reverse=True
        )

        top = items_sorted[:3]

        clean_top = [
            {
                "feature": name,
                "impact": round(float(shap_val), 3),
                "value": round(float(value), 2),
                "direction": "up" if shap_val > 0 else "down"
            }
            for name, shap_val, value in top
        ]
        print(clean_top)



        

def Test(data):

    # features used by the model
    X = data.drop(columns=["date", "snow_day"], errors="ignore")

    # load model
    with open("../api/model.pkl", "rb") as f:
        MODEL = pickle.load(f)

    GetExplanations(X, MODEL)

    # predicted probability of snow day
    probs = MODEL.predict_proba(X)[:, 1]

    results = data.copy()
    results["snow_day_probability"] = probs

    print("SNOW DAY ODDS\n")

    # iterate each day
    for i, row in results.iterrows():

        weekday = pd.to_datetime(row["date"]).day_name()

        odds = (
            row["snow_day_probability"] * 100 if row.get("snowfall_24h", 0) != 0 else 0.01
        )

        print(
            f"{row['date']} ({weekday}) → {odds:.1f}% chance of snow day "
            f"(so {'yes' if odds > 50 else 'no'})"
        )

        print()

# ---------------- RUN ----------------

#TRAINING_DATA = pd.read_csv("../data/training_dataset_1.csv")
TESTING_DATA = weather.t()

#Train(TRAINING_DATA)
#PrintFeatureImportance()
Test(TESTING_DATA)
