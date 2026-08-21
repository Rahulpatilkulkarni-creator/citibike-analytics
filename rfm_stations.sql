WITH station_stats AS (
    SELECT
        start_station_id AS station_id,
        MAX(started_at) AS last_ride,
        COUNT(*) AS total_rides,
        SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0) AS total_duration_minutes
    FROM rides
    GROUP BY start_station_id
),

-- Recency = days between this station's last ride and the most recent date in the whole dataset
station_recency AS (
    SELECT
        station_id,
        total_rides,
        total_duration_minutes,
        (SELECT MAX(started_at) FROM rides) - last_ride AS recency_gap
    FROM station_stats
),

-- Quintile scoring: 5 = best (most recent / most frequent / most volume), 1 = worst
scored AS (
    SELECT
        station_id,
        total_rides,
        total_duration_minutes,
        recency_gap,
        -- recency: LOWER gap is better, so we reverse the quintile direction
        6 - NTILE(5) OVER (ORDER BY recency_gap) AS recency_score,
        NTILE(5) OVER (ORDER BY total_rides) AS frequency_score,
        NTILE(5) OVER (ORDER BY total_duration_minutes) AS monetary_score
    FROM station_recency
)

SELECT
    sc.station_id,
    st.station_name,
    sc.total_rides,
    ROUND(sc.total_duration_minutes) AS total_duration_minutes,
    sc.recency_gap,
    sc.recency_score,
    sc.frequency_score,
    sc.monetary_score,
    (sc.recency_score + sc.frequency_score + sc.monetary_score) AS rfm_total,
    CASE
        WHEN (sc.recency_score + sc.frequency_score + sc.monetary_score) >= 13 THEN 'Power Station'
        WHEN (sc.recency_score + sc.frequency_score + sc.monetary_score) >= 9  THEN 'Steady'
        WHEN (sc.recency_score + sc.frequency_score + sc.monetary_score) >= 5  THEN 'At Risk'
        ELSE 'Dormant/Dying'
    END AS station_segment
FROM scored sc
JOIN stations st ON sc.station_id = st.station_id
ORDER BY rfm_total DESC;