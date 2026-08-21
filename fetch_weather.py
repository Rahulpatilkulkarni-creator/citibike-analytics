import requests
import pandas as pd

# NYC coordinates (Manhattan, roughly central to the Citi Bike network)
LAT, LON = 40.7580, -73.9855

url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": LAT,
    "longitude": LON,
    "start_date": "2023-12-31",
    "end_date": "2024-06-30",
    "daily": "temperature_2m_mean,precipitation_sum,windspeed_10m_max",
    "timezone": "America/New_York"
}

print("Fetching weather data from Open-Meteo...")
response = requests.get(url, params=params)
response.raise_for_status()
data = response.json()

weather_df = pd.DataFrame({
    "date": data["daily"]["time"],
    "temp_mean_c": data["daily"]["temperature_2m_mean"],
    "precipitation_mm": data["daily"]["precipitation_sum"],
    "windspeed_max_kmh": data["daily"]["windspeed_10m_max"]
})

print(f"Retrieved {len(weather_df)} days of weather data.")
print(weather_df.head())
print(weather_df.tail())

weather_df.to_csv("nyc_weather.csv", index=False)
print("✅ Saved to nyc_weather.csv")