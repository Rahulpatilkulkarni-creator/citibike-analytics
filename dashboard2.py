import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.neon")

# Use Streamlit secrets when deployed in the cloud, fall back to .env.neon locally
if hasattr(st, 'secrets') and 'DB_HOST' in st.secrets:
    db_host = st.secrets['DB_HOST']
    db_port = st.secrets['DB_PORT']
    db_name = st.secrets['DB_NAME']
    db_user = st.secrets['DB_USER']
    db_password = quote_plus(st.secrets['DB_PASSWORD'])
else:
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = quote_plus(os.getenv('DB_PASSWORD'))

DB_URL = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require"engine = create_engine(DB_URL)

@st.cache_data(ttl=3600)
def run_query(query):
    return pd.read_sql(query, engine)

st.set_page_config(page_title="Citi Bike Analytics", layout="wide")
st.title("🚲 Citi Bike Network Analytics — Jan–Jun 2024")
st.caption("Station lifecycle, usage segmentation, rebalancing, and weather sensitivity analysis")
st.caption("📊 This live dashboard runs on pre-aggregated summary tables (full 6-month results, ~280KB total) — see the [GitHub repo](https://github.com/Rahulpatilkulkarni-creator/citibike-analytics) for the full 18.7M-row raw pipeline.")

col1, col2 = st.columns(2)
total_stations = run_query("SELECT COUNT(*) AS n FROM station_summary").iloc[0]['n']
total_departures = run_query("SELECT SUM(total_departures) AS n FROM station_summary").iloc[0]['n']
col1.metric("Total Rides Analyzed", f"{int(total_departures):,}")
col2.metric("Unique Stations", f"{total_stations:,}")

st.divider()

# ============ SECTION 1: Cohort Retention ============
st.header("1. Station Cohort Retention")
st.caption("What % of stations from each monthly cohort are still active in later months")

cohort_df = run_query("SELECT * FROM cohort_summary ORDER BY cohort_month, month_number")
cohort_df['cohort_month'] = pd.to_datetime(cohort_df['cohort_month']).dt.strftime('%b %Y')

fig1 = px.line(cohort_df, x='month_number', y='retention_pct', color='cohort_month',
               markers=True, labels={'month_number': 'Months Since First Active', 'retention_pct': 'Retention %'})
st.plotly_chart(fig1, width='stretch')
st.info("💡 **Why it matters:** The mature Manhattan/Brooklyn core holds 98-100% retention across 6 months — stations rarely go dark once established.")

st.divider()

# ============ SECTION 2: RFM Segmentation ============
st.header("2. Station RFM Segmentation")
st.caption("Stations ranked by Recency, Frequency, and ride-volume — segmented into tiers")

rfm_df = run_query("SELECT rfm_segment AS segment, COUNT(*) AS station_count FROM station_summary GROUP BY rfm_segment ORDER BY station_count DESC")
fig2 = px.bar(rfm_df, x='segment', y='station_count', color='segment',
              category_orders={'segment': ['Power Station', 'Steady', 'At Risk', 'Dormant/Dying']},
              labels={'station_count': 'Number of Stations'})
st.plotly_chart(fig2, width='stretch')
st.info("💡 **Why it matters:** Power Stations validate against real Manhattan transit hubs (Penn Station, Union Square) — confirming the scoring reflects genuine usage, not noise.")

st.divider()

# ============ SECTION 3: Supply-Demand Imbalance ============
st.header("3. Supply-Demand Imbalance")
st.caption("Stations with the biggest gap between rides starting vs. ending there — rebalancing candidates")

supply_df = run_query("SELECT station_name, net_flow, flow_type FROM station_summary ORDER BY ABS(net_flow) DESC LIMIT 15")
fig3 = px.bar(supply_df.sort_values('net_flow'), x='net_flow', y='station_name', color='flow_type',
              orientation='h', labels={'net_flow': 'Net Flow (arrivals - departures)', 'station_name': ''})
st.plotly_chart(fig3, width='stretch')
st.info("💡 **Why it matters:** These stations need daily rebalancing — imbalances are realistic (single-digit %) after fixing a station-ID drift bug that originally inflated these to 90%+.")

st.divider()

# ============ SECTION 4: Weather Sensitivity ============
st.header("4. Weather Sensitivity by Rider Type")
st.caption("Daily ride volume for members vs. casual riders, overlaid with temperature")

weather_df = run_query("SELECT * FROM daily_summary ORDER BY ride_date")
fig4 = px.line(weather_df, x='ride_date', y=['member_rides', 'casual_rides'],
               labels={'value': 'Daily Rides', 'ride_date': 'Date', 'variable': 'Rider Type'})
st.plotly_chart(fig4, width='stretch')

col3, col4 = st.columns(2)
col3.metric("Casual Ride Drop on Rainy Days", "43.0%", help="p < 0.001, statistically significant")
col4.metric("Member Ride Drop on Rainy Days", "29.8%", help="p < 0.001, statistically significant")
st.caption("Both rider types show statistically significant weather sensitivity — casual riders more so, consistent with more discretionary/leisure usage.")

st.divider()
st.header("🔍 Station Lookup")
st.caption("Search any station to see its individual stats")

station_search = st.text_input("Type a station name (partial match works):", "")

if station_search:
    lookup_query = text("""
        SELECT station_name, total_departures, total_arrivals, net_flow, flow_type, rfm_segment, first_seen, last_seen
        FROM station_summary
        WHERE station_name ILIKE :search_term
        ORDER BY total_departures DESC
        LIMIT 10
    """)
    with engine.connect() as conn:
        result_df = pd.read_sql(lookup_query, conn, params={"search_term": f"%{station_search}%"})

    if len(result_df) > 0:
        st.dataframe(result_df, width='stretch')
    else:
        st.warning("No stations found matching that search.")