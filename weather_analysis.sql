WITH daily_rides AS (
    SELECT
        DATE(started_at) AS ride_date,
        member_casual,
        COUNT(*) AS ride_count
    FROM rides
    WHERE DATE(started_at) BETWEEN '2023-12-31' AND '2024-06-30'
    GROUP BY DATE(started_at), member_casual
),

daily_pivot AS (
    SELECT
        ride_date,
        SUM(CASE WHEN member_casual = 'member' THEN ride_count ELSE 0 END) AS member_rides,
        SUM(CASE WHEN member_casual = 'casual' THEN ride_count ELSE 0 END) AS casual_rides
    FROM daily_rides
    GROUP BY ride_date
)

SELECT
    dp.ride_date,
    w.temp_mean_c,
    w.precipitation_mm,
    dp.member_rides,
    dp.casual_rides,
    ROUND(dp.casual_rides::numeric / NULLIF(dp.member_rides, 0), 3) AS casual_to_member_ratio
FROM daily_pivot dp
JOIN weather w ON dp.ride_date = w.date
ORDER BY dp.ride_date;