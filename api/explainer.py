
def GetExplanations(data, model):
    import shap

    explainer = shap.TreeExplainer(
        model,
        model_output="raw"
    )

    explanations = {}

    for i in data.index:
        row = data.loc[[i]]  # keep 2D

        shap_values = explainer(row)

        exp = shap.Explanation(
            values=shap_values.values[0, :, 1],
            base_values=shap_values.base_values[0, 1],
            data=row.iloc[0],
            feature_names=row.columns
        )

        items = [
            (name, shap_val, value)
            for name, shap_val, value in zip(
                exp.feature_names,
                exp.values,
                exp.data
            )
            if not name.startswith("weather_code")
        ]

        items = [
            (name, shap_val, value)
            for name, shap_val, value in zip(
                exp.feature_names,
                exp.values,
                exp.data
            )
            if not name.startswith("weather_code")
        ]

        # Split by direction
        snow_factors = [
            x for x in items
            if "snow" in str(x[0]) or "precip" in str(x[0])
        ]

        wind_factors = [
            x for x in items
            if "wind" in str(x[0])
        ]

        other_factors = [
            x for x in items
            if "snow" not in str(x[0]) and "wind" not in str(x[0]) and "precip" not in str(x[0])
        ]

        # Sort each group
        snow_sorted = sorted(snow_factors, key=lambda x: x[1], reverse=True)
        wind_sorted = sorted(wind_factors, key=lambda x: x[1], reverse=True)
        other_sorted = sorted(other_factors, key=lambda x: x[1], reverse=True)

        top = snow_sorted[:1] + wind_sorted[:1] + other_sorted[:1]

        explanations[i] = [
            {
                "feature": name,
                "impact": round(float(shap_val), 3),
                "value": round(float(value), 2),
                "direction": "up" if shap_val > 0 else "down",
                "humanized_value": HumanizeFeatureValue(name, value, shap_val),
            }
            for name, shap_val, value in top
        ]

    return explanations

def HumanizeFeatureValue(feature, value, shap_value):
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
    "snowfall_overnight": [
        (0, "No Overnight Snowfall"),
        (2, "Light Overnight Snowfall"),
        (7, "Moderate Overnight Snowfall"),
        (15, "Heavy Overnight Snowfall"),
        (999, "Extreme Overnight Snowfall"),
    ],
    "snowfall_24h": [
        (0, "No Snowfall (Daily Total)"),
        (5, "Light Snowfall (Daily Total)"),
        (15, "Moderate Snowfall (Daily Total)"),
        (30, "Heavy Snowfall (Daily Total)"),
        (999, "Extreme Snowfall (Daily Total)"),
    ],
    "snowfall_last_24h": [
        (0, "No Snowfall (past 24h)"),
        (5, "Light Snowfall (past 24h)"),
        (15, "Moderate Snowfall (past 24h)"),
        (30, "Heavy Snowfall (past 24h)"),
        (999, "Extreme Snowfall (past 24h)"),
    ],
    "snowfall_last_12h": [
        (0, "No Snowfall (past 12h)"),
        (5, "Light Snowfall (past 12h)"),
        (15, "Moderate Snowfall (past 12h)"),
        (30, "Heavy Snowfall (past 12h)"),
        (999, "Extreme Snowfall (past 12h)"),
    ],

    # ❄️ Snow depth (cm)
    "snow_depth": [
        (0, "No Snow Accumulation"),
        (10, "Notable Snow Accumulation"),
        (25, "Deep Snow Accumulation"),
        (999, "Extreme Snow Accumulation"),
    ],

    # 🌧 Precipitation (mm)
    "precipitation": [
        (0, "No Precipitation"),
        (2, "Light Precipitation"),
        (8, "Moderate Precipitation"),
        (999, "Heavy Precipitation"),
    ],
    "precipitation_overnight": [
        (0, "No Overnight Precipitation"),
        (2, "Light Overnight Precipitation"),
        (8, "Moderate Overnight Precipitation"),
        (999, "Heavy Overnight Precipitation"),
    ],
    "precipitation_24h": [
        (0, "No Precipitation (24h)"),
        (5, "Light Precipitation (24h)"),
        (15, "Moderate Precipitation (24h)"),
        (999, "Heavy Precipitation (24h)"),
    ],

    # 🌡 Temperature (°C)
    "temperature": [
        (-25, "Extreme Cold Temperatures"),
        (-15, "Very Cold Temperatures"),
        (-8, "Cold Temperatures"),
        (-2, "Near Freezing Temperatures"),
        (999, "Above Freezing Temperatures"),
    ],
    "temp_min_overnight": [
        (-25, "Extreme Overnight Cold"),
        (-15, "Very Cold Overnight Temperatures"),
        (-8, "Cold Overnight Temperatures"),
        (-2, "Near Freezing Overnight Temperatures"),
        (999, "Mild Overnight Temperatures"),
    ],

    # 💨 Wind speed (km/h)
    "wind_speed": [
        (10, "Calm Wind Speeds"),
        (25, "Breezy Wind Speeds"),
        (40, "Strong Wind Speeds"),
        (60, "Very Strong Wind Speeds"),
        (999, "Extreme Wind Speeds"),
    ],
    "wind_speed_avg_overnight": [
        (10, "Calm Overnight Winds"),
        (25, "Breezy Overnight Winds"),
        (40, "Strong Overnight Winds"),
        (60, "Very Strong Overnight Winds"),
        (999, "Extreme Overnight Winds"),
    ],

    # 🌬 Wind gusts (km/h)
    "wind_gusts": [
        (20, "Light Wind Gusts"),
        (40, "Strong Wind Gusts"),
        (70, "Severe Wind Gusts"),
        (999, "Extreme Wind Gusts"),
    ],
    "wind_gusts_max_overnight": [
        (20, "Light Overnight Wind Gusts"),
        (40, "Strong Overnight Wind Gusts"),
        (70, "Severe Overnight Wind Gusts"),
        (999, "Extreme Overnight Wind Gusts"),
    ],

    # ❄️ Dew point (°C)
    "dewpoint_avg_overnight": [
        (-15, "Extremely Dry Overnight Air"),
        (-5, "Dry Overnight Air"),
        (0, "Near Freezing Dew Point"),
        (999, "Moist Overnight Air"),
    ],

    # 🧊 Freezing rain (boolean)
    "freezing_rain": [
        (False, "No Freezing Rain"),
        (True, "Freezing Rain Conditions"),
    ],

    # 🌥 Weather codes
    "weather_code": [
        (66, "Freezing Rain"),
        (67, "Heavy Freezing Rain"),
        (71, "Snowfall"),
        (73, "Heavy Snowfall"),
        (75, "Extreme Snowfall"),
        (77, "Snow Grains"),
        (85, "Snow Showers"),
        (86, "Heavy Snow Showers"),
    ],

    # ⚠️ Model flags
    "no_snowfall_penalty": [
        (0, None),
        (1, "No Snowfall Overnight"),
        (2, "No Snowfall (24h)"),
    ],
}