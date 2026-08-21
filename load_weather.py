import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

load_dotenv()

db_password = quote_plus(os.getenv('DB_PASSWORD'))
DB_URL = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{db_password}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

# Create the weather table
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS weather (
            date DATE PRIMARY KEY,
            temp_mean_c NUMERIC(5,2),
            precipitation_mm NUMERIC(6,2),
            windspeed_max_kmh NUMERIC(5,2)
        );
    """))
    conn.commit()

weather_df = pd.read_csv("nyc_weather.csv")
weather_df.to_sql('weather', engine, if_exists='append', index=False, method='multi', chunksize=200)

print(f"✅ Loaded {len(weather_df)} days of weather data into the weather table.")