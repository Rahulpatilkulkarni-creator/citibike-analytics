import os
import glob
import io
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from urllib.parse import quote_plus

load_dotenv()

db_password = quote_plus(os.getenv('DB_PASSWORD'))
DB_URL = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{db_password}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

csv_files = sorted(
    glob.glob("202401-citibike-tripdata*.csv") +
    glob.glob("202402-citibike-tripdata*.csv") +
    glob.glob("202403-citibike-tripdata*.csv") +
    glob.glob("202404-citibike-tripdata*.csv") +
    glob.glob("202405-citibike-tripdata*.csv") +
    glob.glob("202406-citibike-tripdata*.csv")
)
print(f"Found {len(csv_files)} files.")

seen_station_ids = set()
total_rides_loaded = 0
total_dropped = 0

for f in csv_files:
    print(f"\nProcessing {f}...")
    df = pd.read_csv(f, dtype={
        'start_station_id': str,
        'end_station_id': str,
        'ride_id': str
    })

    # ---- Stations: only insert IDs we haven't seen in a previous file ----
    start_st = df[['start_station_id', 'start_station_name', 'start_lat', 'start_lng']].rename(
        columns={'start_station_id': 'station_id', 'start_station_name': 'station_name', 'start_lat': 'latitude', 'start_lng': 'longitude'})
    end_st = df[['end_station_id', 'end_station_name', 'end_lat', 'end_lng']].rename(
        columns={'end_station_id': 'station_id', 'end_station_name': 'station_name', 'end_lat': 'latitude', 'end_lng': 'longitude'})

    stations = pd.concat([start_st, end_st], ignore_index=True)
    stations = stations.dropna(subset=['station_id'])
    stations = stations.drop_duplicates(subset=['station_id'], keep='first')
    stations = stations[~stations['station_id'].isin(seen_station_ids)]

    if len(stations) > 0:
        stations.to_sql('stations', engine, if_exists='append', index=False, method='multi', chunksize=1000)
        seen_station_ids.update(stations['station_id'].tolist())
        print(f"  Inserted {len(stations)} new stations (running total: {len(seen_station_ids)})")

    # ---- Rides: clean, then stream straight into COPY ----
    rides = df[['ride_id', 'rideable_type', 'started_at', 'ended_at',
                'start_station_id', 'end_station_id', 'member_casual']].copy()

    before = len(rides)
    rides = rides.dropna(subset=['start_station_id', 'end_station_id'])
    dropped = before - len(rides)
    total_dropped += dropped

    rides = rides.drop_duplicates(subset=['ride_id'], keep='first')

    buffer = io.StringIO()
    rides.to_csv(buffer, index=False, header=False)
    buffer.seek(0)

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        cursor.copy_expert(
            "COPY rides (ride_id, rideable_type, started_at, ended_at, start_station_id, end_station_id, member_casual) FROM STDIN WITH CSV",
            buffer
        )
        raw_conn.commit()
        total_rides_loaded += len(rides)
        print(f"  Loaded {len(rides)} rides (dropped {dropped}). Running total: {total_rides_loaded}")
    finally:
        raw_conn.close()

    # Free memory before next file
    del df, rides, stations, buffer

print(f"\n✅ Done. Total rides loaded: {total_rides_loaded}. Total dropped: {total_dropped}.")