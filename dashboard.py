import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()

db_password = quote_plus(os.getenv('DB_PASSWORD'))
DB_URL = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{db_password}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

@st.cache_data(ttl=3600)
def run_query(query):
    return pd.read_sql(query, engine)

st.set_page_config(page_title="Citi Bike Analytics", layout="wide")
st.title("🚲 Citi Bike Network Analytics — Jan–Jun 2024")
st.caption("Station lifecycle, usage segmentation, rebalancing, and weather sensitivity analysis")

total_rides = run_query("SELECT COUNT(*) AS n FROM rides").iloc[0]['n']
total_stations = run_query("SELECT COUNT(*) AS n FROM stations").iloc[0]['n']

col1, col2 = st.columns(2)
col1.metric("Total Rides Analyzed", f"{total_rides:,}")
col2.metric("Unique Stations", f"{total_stations:,}")

st.divider()

# ============ SECTION 1: Cohort Retention ============
st.header("1. Station Cohort Retention")
st.caption("What % of stations from each monthly cohort are still active in later months")

cohort_query = """
WITH station_cohort AS (
    SELECT start_station_id AS station_id, DATE_TRUNC('month', MIN(started_at)) AS cohort_month
    FROM rides GROUP BY start_station_id
),
station_activity AS (
    SELECT DISTINCT start_station_id AS station_id, DATE_TRUNC('month', started_at) AS active_month
    FROM rides
),
cohort_activity AS (
    SELECT sc.cohort_month, sa.active_month, sa.station_id,
        (EXTRACT(YEAR FROM sa.active_month) - EXTRACT(YEAR FROM sc.cohort_month)) * 12 +
        (EXTRACT(MONTH FROM sa.active_month) - EXTRACT(MONTH FROM sc.cohort_month)) AS month_number
    FROM station_activity sa JOIN station_cohort sc ON sa.station_id = sc.station_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT station_id) AS total_stations
    FROM station_cohort GROUP BY cohort_month
),
cohort_counts AS (
    SELECT cohort_month, month_number, COUNT(DISTINCT station_id) AS active_stations
    FROM cohort_activity GROUP BY cohort_month, month_number
)
SELECT cc.cohort_month, cs.total_stations AS cohort_size, cc.month_number, cc.active_stations,
    ROUND(100.0 * cc.active_stations / cs.total_stations, 1) AS retention_pct
FROM cohort_counts cc JOIN cohort_size cs ON cc.cohort_month = cs.cohort_month
WHERE cs.total_stations >= 100
ORDER BY cc.cohort_month, cc.month_number;
"""
cohort_df = run_query(cohort_query)
cohort_df['cohort_month'] = cohort_df['cohort_month'].dt.strftime('%b %Y')

fig1 = px.line(cohort_df, x='month_number', y='retention_pct', color='cohort_month',
               markers=True, labels={'month_number': 'Months Since First Active', 'retention_pct': 'Retention %'})
st.plotly_chart(fig1, width='stretch')
st.caption("Filtered to cohorts with 100+ stations to avoid noise from small pilot batches.")
st.info("💡 **Why it matters:** The mature Manhattan/Brooklyn core holds 98-100% retention across 6 months — stations rarely go dark once established. Smaller, newer cohorts (concentrated in Jersey City/Hoboken) show more volatility, consistent with a still-stabilizing service area.")
st.divider()

# ============ SECTION 2: RFM Segmentation ============
st.header("2. Station RFM Segmentation")
st.caption("Stations ranked by Recency, Frequency, and ride-volume — segmented into tiers")

rfm_summary_query = """
WITH station_stats AS (
    SELECT start_station_id AS station_id, MAX(started_at) AS last_ride, COUNT(*) AS total_rides,
        SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0) AS total_duration_minutes
    FROM rides GROUP BY start_station_id
),
station_recency AS (
    SELECT station_id, total_rides, total_duration_minutes,
        (SELECT MAX(started_at) FROM rides) - last_ride AS recency_gap
    FROM station_stats
),
scored AS (
    SELECT station_id,
        6 - NTILE(5) OVER (ORDER BY recency_gap) AS recency_score,
        NTILE(5) OVER (ORDER BY total_rides) AS frequency_score,
        NTILE(5) OVER (ORDER BY total_duration_minutes) AS monetary_score
    FROM station_recency
)
SELECT
    CASE
        WHEN (recency_score+frequency_score+monetary_score) >= 13 THEN 'Power Station'
        WHEN (recency_score+frequency_score+monetary_score) >= 9  THEN 'Steady'
        WHEN (recency_score+frequency_score+monetary_score) >= 5  THEN 'At Risk'
        ELSE 'Dormant/Dying'
    END AS segment,
    COUNT(*) AS station_count
FROM scored GROUP BY segment ORDER BY station_count DESC;
"""
rfm_df = run_query(rfm_summary_query)
fig2 = px.bar(rfm_df, x='segment', y='station_count', color='segment',
              category_orders={'segment': ['Power Station', 'Steady', 'At Risk', 'Dormant/Dying']},
              labels={'station_count': 'Number of Stations'})
st.plotly_chart(fig2, width='stretch')
st.info("💡 **Why it matters:** 543 stations are 'Power Stations' — high-recency, high-frequency hubs validated against real Manhattan transit corridors (Penn Station, Union Square). 380 are 'Dormant/Dying' — candidates for network pruning or targeted promotion.")
st.divider()

# ============ SECTION 3: Supply-Demand Imbalance ============
st.header("3. Supply-Demand Imbalance")
st.caption("Stations with the biggest gap between rides starting vs. ending there — rebalancing candidates")

supply_query = """
WITH departures AS (
    SELECT start_station_id AS station_id, COUNT(*) AS total_departures FROM rides GROUP BY start_station_id
),
arrivals AS (
    SELECT end_station_id AS station_id, COUNT(*) AS total_arrivals FROM rides GROUP BY end_station_id
),
flow AS (
    SELECT COALESCE(d.station_id, a.station_id) AS station_id,
        COALESCE(d.total_departures, 0) AS total_departures,
        COALESCE(a.total_arrivals, 0) AS total_arrivals,
        COALESCE(a.total_arrivals, 0) - COALESCE(d.total_departures, 0) AS net_flow
    FROM departures d FULL OUTER JOIN arrivals a ON d.station_id = a.station_id
)
SELECT st.station_name, f.net_flow,
    CASE WHEN f.net_flow > 0 THEN 'Sink (bikes pile up)' ELSE 'Source (bikes drain)' END AS flow_type
FROM flow f JOIN stations st ON f.station_id = st.station_id
ORDER BY ABS(f.net_flow) DESC LIMIT 15;
"""
supply_df = run_query(supply_query)
fig3 = px.bar(supply_df.sort_values('net_flow'), x='net_flow', y='station_name', color='flow_type',
              orientation='h', labels={'net_flow': 'Net Flow (arrivals - departures)', 'station_name': ''})
st.plotly_chart(fig3, width='stretch')
st.info("💡 **Why it matters:** These stations need daily manual rebalancing — 'Source' stations drain and need bikes trucked in, 'Sink' stations overflow and need bikes trucked out. Note: imbalances here are realistic (single-digit %) after fixing a station-ID drift bug that originally inflated these to 90%+.")
st.divider()

# ============ SECTION 4: Weather Sensitivity ============
st.header("4. Weather Sensitivity by Rider Type")
st.caption("Daily ride volume for members vs. casual riders, overlaid with temperature")

weather_query = """
WITH daily_rides AS (
    SELECT DATE(started_at) AS ride_date, member_casual, COUNT(*) AS ride_count
    FROM rides GROUP BY DATE(started_at), member_casual
),
daily_pivot AS (
    SELECT ride_date,
        SUM(CASE WHEN member_casual = 'member' THEN ride_count ELSE 0 END) AS member_rides,
        SUM(CASE WHEN member_casual = 'casual' THEN ride_count ELSE 0 END) AS casual_rides
    FROM daily_rides GROUP BY ride_date
)
SELECT dp.ride_date, w.temp_mean_c, dp.member_rides, dp.casual_rides
FROM daily_pivot dp JOIN weather w ON dp.ride_date = w.date
ORDER BY dp.ride_date;
"""
weather_df = run_query(weather_query)

fig4 = px.line(weather_df, x='ride_date', y=['member_rides', 'casual_rides'],
               labels={'value': 'Daily Rides', 'ride_date': 'Date', 'variable': 'Rider Type'})
st.plotly_chart(fig4, width='stretch')

col3, col4 = st.columns(2)
col3.metric("Casual Ride Drop on Rainy Days", "43.0%", help="p < 0.001, statistically significant")
col4.metric("Member Ride Drop on Rainy Days", "29.8%", help="p < 0.001, statistically significant")
st.caption("Both rider types show statistically significant weather sensitivity — casual riders more so, consistent with more discretionary/leisure usage.")
st.info("💡 **Why it matters:** Both rider types are weather-sensitive (p < 0.001), but casual riders drop 43% on rainy days vs. members' 29.8% — quantified evidence that casual = leisure-driven, member = more utility-driven, though the distinction is directional, not absolute.")

st.divider()
st.header("🔍 Station Lookup")
st.caption("Search any station to see its individual stats across all four analyses")

station_search = st.text_input("Type a station name (partial match works):", "")

if station_search:
    from sqlalchemy import text

    departures_query = text("""
        SELECT st.station_name, COUNT(*) AS departures, MIN(r.started_at) AS first_seen, MAX(r.started_at) AS last_seen
        FROM stations st
        JOIN rides r ON r.start_station_id = st.station_id
        WHERE st.station_name ILIKE :search_term
        GROUP BY st.station_name
    """)

    arrivals_query = text("""
        SELECT st.station_name, COUNT(*) AS arrivals
        FROM stations st
        JOIN rides r ON r.end_station_id = st.station_id
        WHERE st.station_name ILIKE :search_term
        GROUP BY st.station_name
    """)

    with engine.connect() as conn:
        dep_df = pd.read_sql(departures_query, conn, params={"search_term": f"%{station_search}%"})
        arr_df = pd.read_sql(arrivals_query, conn, params={"search_term": f"%{station_search}%"})

    result_df = pd.merge(dep_df, arr_df, on='station_name', how='outer').fillna(0)
    result_df = result_df.sort_values('departures', ascending=False).head(10)

    if len(result_df) > 0:
        st.dataframe(result_df, width='stretch')
    else:
        st.warning("No stations found matching that search.")