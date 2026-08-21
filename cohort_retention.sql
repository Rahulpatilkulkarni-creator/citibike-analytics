-- Step 1: Find each station's "birth month" — first month it appears in the data
WITH station_cohort AS (
    SELECT
        start_station_id AS station_id,
        DATE_TRUNC('month', MIN(started_at)) AS cohort_month
    FROM rides
    GROUP BY start_station_id
),

-- Step 2: Get every (station, active_month) pair — which months each station had at least one ride
station_activity AS (
    SELECT DISTINCT
        start_station_id AS station_id,
        DATE_TRUNC('month', started_at) AS active_month
    FROM rides
),

-- Step 3: Join activity to cohort, and calculate how many months since "birth"
cohort_activity AS (
    SELECT
        sc.cohort_month,
        sa.active_month,
        sa.station_id,
        -- months elapsed since this station's first-ever ride
        (EXTRACT(YEAR FROM sa.active_month) - EXTRACT(YEAR FROM sc.cohort_month)) * 12 +
        (EXTRACT(MONTH FROM sa.active_month) - EXTRACT(MONTH FROM sc.cohort_month)) AS month_number
    FROM station_activity sa
    JOIN station_cohort sc ON sa.station_id = sc.station_id
),

-- Step 4: Count active stations per cohort per month_number
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT station_id) AS total_stations
    FROM station_cohort
    GROUP BY cohort_month
),

cohort_counts AS (
    SELECT
        cohort_month,
        month_number,
        COUNT(DISTINCT station_id) AS active_stations
    FROM cohort_activity
    GROUP BY cohort_month, month_number
)

-- Step 5: Final retention % table
SELECT
    cc.cohort_month,
    cs.total_stations AS cohort_size,
    cc.month_number,
    cc.active_stations,
    ROUND(100.0 * cc.active_stations / cs.total_stations, 1) AS retention_pct
FROM cohort_counts cc
JOIN cohort_size cs ON cc.cohort_month = cs.cohort_month
ORDER BY cc.cohort_month, cc.month_number;