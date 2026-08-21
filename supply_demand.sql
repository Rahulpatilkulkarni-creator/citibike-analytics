WITH departures AS (
    SELECT start_station_id AS station_id, COUNT(*) AS total_departures
    FROM rides
    GROUP BY start_station_id
),

arrivals AS (
    SELECT end_station_id AS station_id, COUNT(*) AS total_arrivals
    FROM rides
    GROUP BY end_station_id
),

flow AS (
    SELECT
        COALESCE(d.station_id, a.station_id) AS station_id,
        COALESCE(d.total_departures, 0) AS total_departures,
        COALESCE(a.total_arrivals, 0) AS total_arrivals,
        COALESCE(a.total_arrivals, 0) - COALESCE(d.total_departures, 0) AS net_flow
    FROM departures d
    FULL OUTER JOIN arrivals a ON d.station_id = a.station_id
)

SELECT
    f.station_id,
    st.station_name,
    f.total_departures,
    f.total_arrivals,
    f.net_flow,
    ROUND(100.0 * f.net_flow / NULLIF(f.total_departures + f.total_arrivals, 0), 1) AS imbalance_pct,
    CASE
        WHEN f.net_flow > 0 THEN 'Sink (bikes pile up)'
        WHEN f.net_flow < 0 THEN 'Source (bikes drain)'
        ELSE 'Balanced'
    END AS flow_type
FROM flow f
JOIN stations st ON f.station_id = st.station_id
ORDER BY ABS(f.net_flow) DESC
LIMIT 20;