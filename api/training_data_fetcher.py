import weather_fetcher as weather
import pandas as pd

print("Insert year(s) (e.g. 2021, 2022, etc): ")
years = input().split(", ")
years = [y.strip() for y in years if y.strip()]

print("\nInsert latitude and longitude (e.g. 44.56, -80.98): ")
latlon = input().strip()

if latlon == "":
    latitude, longitude = 44.569, -80.98
else:
    latitude, longitude = latlon.split(", ")
    latitude, longitude = float(latitude), float(longitude)

print("\nPull data from 15/11/xx -> 31/03/xx+1? (Y/n):")
choice = input().lower()

all_data = []

if choice in ["y", ""]:
    print("\nPulling data...\n")

    for year in years:
        start = f"{year}-11-15"
        end = f"{int(year) + 1}-03-31"

        print(f"Fetching {start} → {end}")

        year_data = weather.get_data_within_timerange(
            start,
            end,
            latitude,
            longitude
        )

        all_data.append(year_data)

    final_df = pd.concat(all_data, ignore_index=True)

    print("\nData Pulled. What is the # of this training dataset?")
    number = int(input().strip())

    filename = f"data/training_dataset_{number}.csv"
    final_df.to_csv(filename, index=False)

    print(f"\nDone. Saved {len(final_df)} rows to {filename}")

else:
    print("Cancelled.")
