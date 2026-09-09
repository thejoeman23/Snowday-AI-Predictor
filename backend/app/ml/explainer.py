
def get_explanations(data, model):
    explanations = {}

    for i in data.index:
        row = data.loc[[i]]  # keep 2D

        # shap_values = explainer(row)
        #
        # exp = shap.Explanation(
        #     values=shap_values.values[0, :, 1],
        #     base_values=shap_values.base_values[0, 1],
        #     data=row.iloc[0],
        #     feature_names=row.columns
        # )
        #
        # items = [
        #     (name, shap_val, value)
        #     for name, shap_val, value in zip(
        #         exp.feature_names,
        #         exp.values,
        #         exp.data
        #     )
        #     if not (name.startswith("weather_code") or name.__contains__("last"))
        # ]
        #
        # # Split by direction
        # snow_factors = [
        #     x for x in items
        #     if "snow" in str(x[0]) or "precip" in str(x[0])
        # ]
        #
        # wind_factors = [
        #     x for x in items
        #     if "wind" in str(x[0])
        # ]
        #
        # other_factors = [
        #     x for x in items
        #     if "snow" not in str(x[0]) and "wind" not in str(x[0]) and "precip" not in str(x[0])
        # ]
        #
        # # Sort each group
        # snow_sorted = sorted(snow_factors, key=lambda x: abs(x[1]), reverse=True)
        # wind_sorted = sorted(wind_factors, key=lambda x: abs(x[1]), reverse=True)
        # other_sorted = sorted(other_factors, key=lambda x: abs(x[1]), reverse=True)
        #
        # top = snow_sorted[:1] + wind_sorted[:1] + other_sorted[:1]
        #
        # explanations[i] = [
        #     {
        #         "feature": name,
        #         "impact": round(float(shap_val), 3),
        #         "value": round(float(value), 2),
        #         "direction": "up" if shap_val > 0 else "down",
        #         "humanized_value": humanize_feature_value(name, value, shap_val),
        #     }
        #     for name, shap_val, value in top
        # ]

        explanations[i] = [
            {
                "direction": "up",
                "humanized_value": f"{round(float(row['precipitation_4_9am']))} mm of Precipitation",
            },
            {
                "direction": "up",
                "humanized_value": f"{round(float(row['wind_gusts_4_9am_max']))} km/h Wind Gusts"
            },
            {
                "direction": "up",
                "humanized_value": f"{round(float(row['temp_min']))}°C Daily Min Temp"
            }
        ]

    return explanations

def humanize_feature_value(feature, value, shap_value):
    """
    Convert a raw feature value into a human-friendly label.
    Uses predefined buckets for each feature.
    """

    # Get hour for hourly variables like snowfall_3, etc.
    time = feature[len(feature)-1:]
    time = int(time) if time.isdigit() else None

    base_feature = feature[:len(feature)-1] if time is not None else feature

    for threshold, label in FEATURE_BUCKETS.get(base_feature, []):
        if value <= threshold:
            full_label = label if time is None else f"{label} ({time if time != 0 else 12} am)"
            icon = "⬆️" if shap_value > 0 else "⬇️"
            return f"{full_label}"

FEATURE_BUCKETS = {

    # ❄️ Snowfall (cm)
    "snowfall": [
        (0, "No Snowfall"),
        (2, "Light Snowfall"),
        (7, "Moderate Snowfall"),
        (15, "Heavy Snowfall"),
        (999, "Extreme Snowfall"),
    ],
    "snowfall_4_9am": [
        (0, "No Snowfall from 4-9am"),
        (2, "Light Snowfall from 4-9am"),
        (7, "Moderate Snowfall from 4-9am"),
        (15, "Heavy Snowfall from 4-9am"),
        (999, "Extreme Snowfall from 4-9am"),
    ],

    # ❄️ Blowing Snow Risk (cm)
    "blowing_snow_risk": [
        (0, "No Blowing Snow"),
        (2, "Light Blowing Snow"),
    ],

    # 🌧 Precipitation (mm)
    "precipitation": [
        (0, "No Precipitation"),
        (2, "Light Precipitation"),
        (8, "Moderate Precipitation"),
        (999, "Heavy Precipitation"),
    ],
    "precipitation_4_9am": [
        (0, "No Precipitation from 4-9am"),
        (2, "Light Precipitation from 4-9am"),
        (8, "Moderate Precipitation from 4-9am"),
        (999, "Heavy Precipitation from 4-9am"),
    ],

    # 🌡 Temperature (°C)
    "temperature": [
        (-25, "Extreme Cold Temperatures"),
        (-15, "Very Cold Temperatures"),
        (-8, "Cold Temperatures"),
        (-2, "Near Freezing Temperatures"),
        (999, "Above Freezing Temperatures"),
    ],
    "temperature_4_9am_min": [
        (-25, "Extreme 4-9am Cold"),
        (-15, "Very Cold 4-9am Temperatures"),
        (-8, "Cold 4-9am Temperatures"),
        (-2, "Near Freezing 4-9am Temperatures"),
        (999, "Mild 4-9am Temperatures"),
    ],
    "temperature_4_9am_avg": [
        (-25, "Extreme 4-9am Cold"),
        (-15, "Very Cold 4-9am Temperatures"),
        (-8, "Cold 4-9am Temperatures"),
        (-2, "Near Freezing 4-9am Temperatures"),
        (999, "Mild 4-9am Temperatures"),
    ],
    "temp_min": [
        (-25, "Extreme Daily Cold"),
        (-15, "Very Cold Daily Temperatures"),
        (-8, "Cold Daily Temperatures"),
        (-2, "Near Freezing Daily Temperatures"),
        (999, "Mild Daily Temperatures"),
    ],

    # 💨 Wind speed (km/h)
    "wind_speed": [
        (10, "Calm Wind Speeds"),
        (25, "Breezy Wind Speeds"),
        (40, "Strong Wind Speeds"),
        (60, "Very Strong Wind Speeds"),
        (999, "Extreme Wind Speeds"),
    ],
    "wind_speed_4_9am_avg": [
        (10, "Calm 4-9am Winds"),
        (25, "Breezy 4-9am Winds"),
        (40, "Strong 4-9am Winds"),
        (60, "Very Strong 4-9am Winds"),
        (999, "Extreme 4-9am Winds"),
    ],

    # 🌬 Wind gusts (km/h)
    "wind_gusts": [
        (20, "Light Wind Gusts"),
        (40, "Strong Wind Gusts"),
        (70, "Severe Wind Gusts"),
        (999, "Extreme Wind Gusts"),
    ],
    "wind_gusts_4_9am_max": [
        (20, "Light 4-9am Wind Gusts"),
        (40, "Strong 4-9am Wind Gusts"),
        (70, "Severe 4-9am Wind Gusts"),
        (999, "Extreme 4-9am Wind Gusts"),
    ],
    "daily_wind_gusts_max": [
        (20, "Light Daily Wind Gusts"),
        (40, "Strong Daily Wind Gusts"),
        (70, "Severe Daily Wind Gusts"),
        (999, "Extreme Daily Wind Gusts"),
    ],

    # ❄️ Dew point (°C)
    "dewpoint_4_9am_avg": [
        (-15, "Extremely Dry 4-9am Air"),
        (-5, "Dry 4-9am Air"),
        (0, "Near Freezing Dew Point"),
        (999, "Moist 4-9am Air"),
    ],

    # 🧊 Freezing rain (boolean)
    "freezing_rain": [
        (False, "No Freezing Rain"),
        (True, "Freezing Rain Conditions"),
    ],

    # 🌥 Weather codes
    "snow_weather_code_4_9am": [
        (0, "No 4-9am Snow Conditions"),
        (1, "Snow Conditions from 4-9am"),
    ],

    # ⚠️ Model flags
    "no_snowfall_4_9am_penalty": [
        (0, None),
        (1, "Very Little Snowfall from 4-9am"),
        (2, "No Snowfall from 4-9am"),
    ],
}
