import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# ---------------- CONFIG ----------------
TRAINING_DATA = pd.read_csv("snowday_dataset.csv")

BRAIN_CELLS = 500
SEED = 42
TEST_SIZE = 0.5
MODEL = RandomForestClassifier(n_estimators=BRAIN_CELLS, random_state=SEED)
# ----------------------------------------

x = TRAINING_DATA.drop(columns=["date", "snow_day"]) # drop date and snow_day because we dont want to learn from them
y = TRAINING_DATA["snow_day"] # target we want to predict

x_train, x_test, y_train, y_test = train_test_split(
    x, y, test_size=TEST_SIZE, random_state=SEED
)
MODEL.fit(x_train, y_train)

# Predict on test set
y_pred = MODEL.predict(x_test)

# Accuracy
print("Accuracy:", accuracy_score(y_test, y_pred))
print()

# Confusion matrix
cm = confusion_matrix(y_test, y_pred)

tn, fp, fn, tp = cm.ravel()

print(f"Predicted {tn}/{tn + fp} non-snow days")
print(f"Predicted {tp}/{tp + fn} snow days")

# Full classification report (precision, recall, f1)
# print(classification_report(y_test, y_pred))

