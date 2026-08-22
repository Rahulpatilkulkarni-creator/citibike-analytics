-- Summary 1: cohort retention (all cohorts, all months)
CREATE TABLE cohort_summary AS
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

-- Summary 2: per-station stats (RFM + supply/demand combined — this also powers station search)
CREATE TABLE station_summary AS
WITH departures AS (
    SELECT start_station_id AS station_id, COUNT(*) AS total_departures,
        MIN(started_at) AS first_seen, MAX(started_at) AS last_seen,
        SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0) AS total_duration_minutes
    FROM rides GROUP BY start_station_id
),
arrivals AS (
    SELECT end_station_id AS station_id, COUNT(*) AS total_arrivals
    FROM rides GROUP BY end_station_id
),
flow AS (
    SELECT COALESCE(d.station_id, a.station_id) AS station_id,
        COALESCE(d.total_departures, 0) AS total_departures,
        COALESCE(a.total_arrivals, 0) AS total_arrivals,
        COALESCE(a.total_arrivals, 0) - COALESCE(d.total_departures, 0) AS net_flow,
        d.first_seen, d.last_seen, d.total_duration_minutes
    FROM departures d FULL OUTER JOIN arrivals a ON d.station_id = a.station_id
),
scored AS (
    SELECT *,
        6 - NTILE(5) OVER (ORDER BY (SELECT MAX(started_at) FROM rides) - last_seen) AS recency_score,
        NTILE(5) OVER (ORDER BY total_departures) AS frequency_score,
        NTILE(5) OVER (ORDER BY total_duration_minutes) AS monetary_score
    FROM flow WHERE first_seen IS NOT NULL
)
SELECT st.station_name, sc.station_id, sc.total_departures, sc.total_arrivals, sc.net_flow,
    CASE WHEN sc.net_flow > 0 THEN 'Sink (bikes pile up)' ELSE 'Source (bikes drain)' END AS flow_type,
    sc.first_seen, sc.last_seen,
    (sc.recency_score + sc.frequency_score + sc.monetary_score) AS rfm_total,
    CASE
        WHEN (sc.recency_score+sc.frequency_score+sc.monetary_score) >= 13 THEN 'Power Station'
        WHEN (sc.recency_score+sc.frequency_score+sc.monetary_score) >= 9  THEN 'Steady'
        WHEN (sc.recency_score+sc.frequency_score+sc.monetary_score) >= 5  THEN 'At Risk'
        ELSE 'Dormant/Dying'
    END AS rfm_segment
FROM scored sc JOIN stations st ON sc.station_id = st.station_id;

-- Summary 3: daily rides + weather (full 6 months)
CREATE TABLE daily_summary AS
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