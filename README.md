# Citi Bike Network Analytics

A PostgreSQL + Python deep dive into six months of NYC Citi Bike trips (Jan–Jun 2024, ~18.7M rides). Rather than another "rides per month" dashboard, this project looks at how the station network actually behaves over time — which stations stick around, which ones need constant rebalancing, and how weather changes rider behavior.

**Live dashboard:** [citibike-analytics.streamlit.app](https://citibike-analytics.streamlit.app/)

---

## Why station-level, not rider-level

I originally planned this as a fairly standard subscription-analytics project — cohort retention, RFM segmentation, funnel analysis, the usual stuff you'd do for a SaaS product, just applied to bike-share membership. Partway in, I realized the data doesn't actually support that.

Citi Bike's public trip exports don't include a rider ID. Every `ride_id` belongs to one trip, not one person, so there's no way to tell if two rides came from the same rider. A lot of the "Citi Bike cohort analysis" projects floating around online quietly ignore this and build rider cohorts anyway, which doesn't really hold up if you look closely at the columns available.

So I rebuilt the plan around what the data can actually support: stations instead of riders. A station has a first-active date, ongoing activity, and measurable "churn" (it stops appearing in the data) — the same shape as a customer cohort, just applied to something the dataset can genuinely track. It turned out to be a decent trade — station lifecycle and rebalancing are real problems bike-share operations teams deal with, so the pivot ended up making the project more relevant, not less.

---

## Stack

- **PostgreSQL** for storage — about 18.7M rows, indexed on the columns the analysis actually queries
- **Python** (pandas, SQLAlchemy, psycopg2) for loading and cleaning
- **SciPy** for the statistical tests behind the weather analysis
- **Streamlit + Plotly** for the dashboard
- **Open-Meteo** for historical NYC weather (free, no key needed)

---

## The data

- Source: [Citi Bike System Data](https://s3.amazonaws.com/tripdata/index.html), the public S3 bucket Citi Bike publishes monthly
- Jan–Jun 2024
- 18,807,481 raw rides, 18,755,749 after dropping rows with no station reference
- 2,254 distinct stations once duplicates were merged (more on that below)

---

## The station ID bug (this was the most useful part of the project)

Early on, my supply-demand query was returning results that looked wrong — the "most imbalanced" stations all showed swings of 90–100%, which is basically impossible for a network that runs daily rebalancing trucks. Looking closer, every station in that list showed up twice, once under each of two different IDs pointing at the same physical spot. `Broadway & W 58 St`, for instance, existed as both `6948.1` and `6948.10`.

It turned out 103 of 2,362 station IDs were duplicates like this — about 4.6% of the network — mostly concentrated at busier stations, presumably because those get touched more often by whatever backend system assigns IDs. Rides were getting split across the two IDs for the same station, making it look like bikes were draining out one "station" and piling up at another when really it was one location being counted twice.

I fixed it by mapping every duplicate ID to a single canonical one (keyed on station name), remapped all 18.7M rides to point at the canonical ID, and merged the leftover duplicate station rows. Nothing got deleted from `rides` — the station count just dropped from 2,362 to 2,254, and the supply-demand numbers went from that fake ±90–100% down to a much more believable single-digit range.

I'm writing this up in detail because catching it mattered more than any individual query in this project. If I'd shipped the RFM and supply-demand results before finding this, both would've been wrong.

---

## What I found

### Station cohort retention
Grouped stations by the month they first show up in the data, then tracked how many are still active in later months.

The core network — Manhattan and Brooklyn, cohorts of 1,998 to 2,229 stations — sits at 98–100% retention across all six months. Once a station is established here, it basically never disappears.

Smaller cohorts, mostly in Jersey City and Hoboken (9 to 27 stations), tell a messier story: retention drops to 42–55% in the first month, then climbs back up over the following months. I checked whether this was a data artifact, but the station names are real, specific JC/Hoboken locations, not placeholders — so this reads as genuine volatility in a newer, still-stabilizing part of the network rather than a bug.

### Station RFM segmentation
Scored every station on recency (days since last ride), frequency (total rides), and volume (total ride-minutes), each bucketed into quintiles.

| Segment | Stations |
|---|---|
| Steady | 741 |
| At Risk | 672 |
| Power Station | 543 |
| Dormant/Dying | 380 |

The top "Power Stations" — W 21 St & 6 Ave, University Pl & E 14 St, 8 Ave & W 31 St, West St & Chambers St — are all recognizable, high-traffic spots near Penn Station, Union Square, and the WTC transit hub. That's a good sign the scoring is picking up something real rather than noise.

### Supply-demand imbalance
For each station, compared how many rides start there against how many end there, to find which ones need the most rebalancing.

Broadway & W 56 St is the biggest net "source" (bikes leave and don't come back at −8.8%), and E 41 St & Madison Ave is the biggest net "sink" (+5.4%). The heaviest sources cluster around Midtown West / Hell's Kitchen, which lines up with how that area's commuter and theater-district traffic tends to flow in one direction more than the other.

### Weather and rider behavior
Joined daily ride counts (split by member vs. casual) against NYC weather data.

Both groups ride more when it's warm — member rides correlate with temperature at r=0.804, casual at r=0.843 (p<0.0001 for both). The more interesting split shows up on rainy days: on days with more than 5mm of rain, casual rides dropped 43.0% while member rides dropped 29.8%, and both drops are statistically significant (p<0.001).

So both rider types care about the weather, but casual riders clearly care more — which fits the idea that casual riders are more likely to be riding for leisure, while members are more likely riding out of habit or necessity. It's a real, measurable difference, just not an absolute one — members still slow down noticeably when it rains.

---

## Project structure

```
citibike-analytics/
├── schema.sql              # stations + rides tables, indexes
├── load_data.py             # streams monthly CSVs into Postgres via COPY
├── fix_station_ids.sql      # canonical station-ID fix
├── fetch_weather.py          # pulls NYC weather from Open-Meteo
├── load_weather.py           # loads weather into Postgres
├── cohort_retention.sql      # station cohort retention
├── rfm_stations.sql          # station RFM scoring
├── supply_demand.sql         # supply-demand imbalance
├── weather_correlation.py    # correlation + t-tests on weather sensitivity
├── dashboard.py               # Streamlit dashboard, all four analyses + station search
├── .env                      # DB credentials, not committed
└── .gitignore
```

## Running it yourself

```bash
# create the database and schema
psql -U postgres -c "CREATE DATABASE citibike;"
psql -U postgres -d citibike -f schema.sql

# set up .env with your own DB credentials

# install dependencies
pip install psycopg2-binary sqlalchemy pandas requests python-dotenv scipy streamlit plotly

# download Jan-Jun 2024 trip data into the project folder
# from https://s3.amazonaws.com/tripdata/index.html

# load rides, then fix the known duplicate station IDs
python load_data.py
psql -U postgres -d citibike -f fix_station_ids.sql

# pull and load weather data
python fetch_weather.py
python load_weather.py

# run the dashboard
streamlit run dashboard.py
```
## A note on how the live dashboard is deployed

The live dashboard doesn't query the full 18.7M-row `rides` table directly — it reads from three small pre-aggregated tables (`cohort_summary`, `station_summary`, `daily_summary`), computed once locally against the full dataset and pushed to a free-tier Neon Postgres instance. Combined, those three tables are under 300KB, well within Neon's free-tier storage limit, while still representing the complete 6-month analysis, not a sample. `dashboard.py` (full local version, queries raw data) and `dashboard2.py` (deployed version, queries the summary tables) are both in this repo — `dashboard2.py` is what's live at the link above.

## Limitations, honestly

- No rider ID in the source data, so nothing here is rider-level — that's a deliberate choice, not an oversight (see above).
- Six months isn't a full year, so the seasonality story is really just "winter into summer," not a complete annual cycle.
- Weather is one set of coordinates for the whole city, not per-station — fine for a compact city like NYC, but it won't catch hyper-local weather effects.
