-- Step 1: For each station_name with multiple IDs, pick one canonical ID (the lowest, alphabetically/numerically first)
CREATE TEMP TABLE station_id_map AS
SELECT
    station_id AS old_id,
    FIRST_VALUE(station_id) OVER (PARTITION BY station_name ORDER BY station_id) AS canonical_id,
    station_name
FROM stations;

-- Step 2: Update rides to point start/end station IDs at the canonical ID
UPDATE rides r
SET start_station_id = m.canonical_id
FROM station_id_map m
WHERE r.start_station_id = m.old_id
  AND m.old_id != m.canonical_id;

UPDATE rides r
SET end_station_id = m.canonical_id
FROM station_id_map m
WHERE r.end_station_id = m.old_id
  AND m.old_id != m.canonical_id;

-- Step 3: Remove the now-orphaned duplicate station rows
DELETE FROM stations
WHERE station_id IN (
    SELECT old_id FROM station_id_map WHERE old_id != canonical_id
);